"""Due continuazioni indipendenti del checkpoint SFT: dpo e sft_control.
Stessi 12 aggiornamenti, batch/accumulo, LR e seed; compute/token diversi fra obiettivi.
"""
import argparse
import hashlib
import math
import os
from pathlib import Path
import sys
os.environ['HF_HUB_OFFLINE'] = '1'  # Usa esclusivamente modello e adapter gia presenti.
import train_dpo_pilot as common
from train_sft_pilot import tokenize_chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check', 'dpo', 'sft_control'])
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    source = Path('models/pilot_sft_train_v1')
    old = common.read(source / 'run_manifest.json')
    if common.read(source / 'result.json')['status'] != 'completed':
        raise ValueError('SFT iniziale non completato.')
    rows, report = common.load_data('results/dpo_pilot_curated_v1/export')
    if report != old['data']:
        raise ValueError('Dataset cambiato dopo SFT.')
    env = common.environment()
    import torch
    from datasets import Dataset
    from peft import PeftModel, prepare_model_for_kbit_training, get_peft_model_state_dict
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainerCallback, set_seed
    from trl import DPOConfig, DPOTrainer, SFTConfig, SFTTrainer
    from trl.data_utils import maybe_apply_chat_template
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling
    set_seed(42)
    tokenizer = AutoTokenizer.from_pretrained(str(source / 'adapter'), local_files_only=True)
    dpo_data = {s: [maybe_apply_chat_template(r, tokenizer) for r in v] for s, v in rows.items()}
    sft_data = {s: [tokenize_chosen(r, tokenizer) for r in v] for s, v in rows.items()}
    lengths = []
    for values in dpo_data.values():
        for row in values:
            tokens = DPOTrainer.tokenize_row(row, tokenizer, add_special_tokens=False)
            lengths.extend(len(tokens['prompt_input_ids']) + len(tokens[k])
                           for k in ['chosen_input_ids', 'rejected_input_ids'])
    if max(lengths) > 1536:
        raise ValueError('Sequenze oltre il limite del pilota; nessun troncamento.')
    adapter_hash = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (source / 'adapter').glob('*.safetensors')}
    if not adapter_hash:
        raise ValueError('Pesi SFT assenti.')
    out = Path(args.output_dir or ('models/pilot_after_sft_' + args.mode + '_v1'))
    if args.mode != 'check' and out.exists() and any(out.iterdir()):
        raise ValueError('Output gia presente: scegli una nuova --output-dir.')
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
    base = AutoModelForCausalLM.from_pretrained(old['model'], revision=old['revision'],
        local_files_only=True, quantization_config=quant, torch_dtype=torch.bfloat16,
        device_map={'': 0}, attn_implementation='sdpa')
    base.config.use_cache = False
    base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True,
                                           gradient_checkpointing_kwargs={'use_reentrant': False})
    model = PeftModel.from_pretrained(base, str(source / 'adapter'), adapter_name='default', is_trainable=True)
    use_reference = args.mode in ('check', 'dpo')
    if use_reference:
        model.load_adapter(str(source / 'adapter'), adapter_name='reference', is_trainable=False)
    model.set_adapter('default')

    def state(name):
        return {k: v.detach().cpu().clone() for k, v in
                get_peft_model_state_dict(model, adapter_name=name).items()}

    start = state('default')
    ref_start = state('reference') if use_reference else None
    if use_reference and (start.keys() != ref_start.keys() or
                          any(not torch.equal(start[k], ref_start[k]) for k in start)):
        raise ValueError('Policy e riferimento non partono dagli stessi pesi SFT.')
    trainable = [n for n, p in model.named_parameters() if p.requires_grad]
    if not trainable or any('.default.' not in n or 'lora_' not in n for n in trainable):
        raise ValueError('Parametri addestrabili inattesi; il riferimento deve essere congelato.')
    if args.mode == 'check':
        model.eval()
        batch = tokenizer('Controllo inizializzazione', return_tensors='pt').to('cuda')
        with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16):
            first = model(**batch).logits.float()
            model.set_adapter('reference')
            second = model(**batch).logits.float()
        model.set_adapter('default')
        delta = float((first - second).abs().max())
        if delta > 1e-5:
            raise ValueError(f'Logits iniziali diversi fra policy e riferimento: {delta}')
        print(f'CONTINUATION CHECK OK: pesi SFT identici, riferimento congelato, differenza logits {delta}.')
        return
    settings = dict(output_dir=str(out), max_steps=12, learning_rate=5e-6,
        per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=4,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
        bf16=True, fp16=False, optim='adamw_torch', lr_scheduler_type='constant', warmup_steps=0,
        max_grad_norm=1.0, weight_decay=0.0, logging_steps=1, logging_nan_inf_filter=False,
        eval_strategy='no', save_strategy='no', report_to='none', dataloader_num_workers=0,
        seed=42, data_seed=42, push_to_hub=False, use_liger_kernel=False)

    class FiniteLogs(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if any(isinstance(v, (int, float)) and not math.isfinite(v) for v in (logs or {}).values()):
                raise ValueError('Metrica non finita.')

    class BF16ReferenceDPO(DPOTrainer):
        def compute_ref_log_probs(self, batch):
            # Usa BF16 esplicito per il riferimento, come per la policy.
            with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16), self.null_ref_context():
                result = self.concatenated_forward(self.model, batch, is_ref_model=True)
            return result['chosen_logps'], result['rejected_logps']

    if args.mode == 'dpo':
        settings.update(beta=0.1, loss_type='sigmoid', max_prompt_length=None,
            max_completion_length=None, max_length=max(lengths) + 8, dataset_num_proc=1,
            precompute_ref_log_probs=True, precompute_ref_batch_size=1, use_logits_to_keep=True,
            model_adapter_name='default', ref_adapter_name='reference', disable_dropout=True)
        trainer = BF16ReferenceDPO(model=model, ref_model=None, args=DPOConfig(**settings),
            train_dataset=Dataset.from_list(dpo_data['train']), eval_dataset=Dataset.from_list(dpo_data['validation']),
            processing_class=tokenizer, callbacks=[FiniteLogs()])
    else:
        settings.update(max_length=None, packing=False, completion_only_loss=True,
            dataset_kwargs={'skip_prepare_dataset': True}, prediction_loss_only=True)
        trainer = SFTTrainer(model=model, args=SFTConfig(**settings),
            train_dataset=Dataset.from_list(sft_data['train']), eval_dataset=Dataset.from_list(sft_data['validation']),
            processing_class=tokenizer, callbacks=[FiniteLogs()],
            data_collator=DataCollatorForLanguageModeling(pad_token_id=tokenizer.pad_token_id,
                                                          completion_only_loss=True))
    common.save(out / 'run_manifest.json', {'model': old['model'], 'revision': old['revision'],
        'data': report, 'environment': env, 'lora': old['lora'], 'settings': settings,
        'objective': args.mode, 'parent_adapter_hashes': adapter_hash,
        'reference': 'frozen SFT adapter' if use_reference else None,
        'note': 'Stesso checkpoint, seed, LR, batch e 12 aggiornamenti; costo e token elaborati diversi. '
                'Optimizer riavviato in entrambi i rami. Nessuna scelta del checkpoint sulla validation.'})
    before = trainer.evaluate(metric_key_prefix='before')
    common.save(out / 'validation_before.json', before)
    if use_reference and abs(before['before_loss'] - math.log(2)) > 0.01:
        raise ValueError('Loss DPO iniziale distante da log(2). Controllare validation_before.json prima del training.')
    result = trainer.train()
    after = trainer.evaluate(metric_key_prefix='after')
    final = state('default')
    delta = max(float((final[k].float() - start[k].float()).abs().max()) for k in start)
    if delta <= 0 or not math.isfinite(delta):
        raise ValueError('Nessun aggiornamento valido.')
    if use_reference:
        ref_final = state('reference')
        if any(not torch.equal(ref_start[k], ref_final[k]) for k in ref_start):
            raise ValueError('Il riferimento SFT e cambiato: risultato non valido.')
    model.set_adapter('default')
    model.save_pretrained(str(out / 'adapter'), selected_adapters=['default'])
    tokenizer.save_pretrained(str(out / 'adapter'))
    common.save(out / 'training_history.json', trainer.state.log_history)
    common.save(out / 'result.json', {'status': 'completed', 'objective': args.mode,
        'steps': trainer.state.global_step, 'before': before, 'after': after,
        'train_metrics': result.metrics, 'max_adapter_parameter_change': delta,
        'reference_unchanged': True if use_reference else None,
        'note': 'Loss SFT e DPO non confrontabili direttamente; confrontare le generazioni.'})
    print(f'{args.mode.upper()} CONTINUATION OK: {trainer.state.global_step} step. Risultati: {out / "result.json"}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ImportError) as exc:
        print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(1)
