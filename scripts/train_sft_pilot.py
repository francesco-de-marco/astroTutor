"""SFT esplorativo sulle chosen del pilota: 22 train / 6 validation.
Parte dal base originale. Non prosegue l'adapter DPO. Nessuna nuova dipendenza.
"""
import argparse
import math
from pathlib import Path
import sys
import train_dpo_pilot as common


def tokenize_chosen(row, tokenizer):
    prompt = tokenizer.apply_chat_template(row['prompt'], tokenize=True, add_generation_prompt=True)
    full = tokenizer.apply_chat_template(row['prompt'] + row['chosen'], tokenize=True,
                                         add_generation_prompt=False)
    if full[:len(prompt)] != prompt or len(full) <= len(prompt):
        raise ValueError('Confine prompt/risposta ambiguo nel chat template.')
    if len(full) > 1536:
        raise ValueError('Sequenza troppo lunga: nessun troncamento automatico.')
    return {'input_ids': full, 'completion_mask': [0] * len(prompt) + [1] * (len(full) - len(prompt))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check', 'train'])
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--learning-rate', type=float, default=5e-5)
    parser.add_argument('--output-dir', default='models/pilot_sft_train_v1')
    parser.add_argument('--data-dir', default='results/dpo_pilot_curated_v1/export')
    args = parser.parse_args()
    if args.epochs < 1 or args.learning_rate <= 0:
        raise ValueError('Epoche e learning rate devono essere positivi.')
    rows, report = common.load_data(args.data_dir)
    previous = common.read(Path('models/pilot_dpo_train_v1/run_manifest.json'))
    if report != previous['data']:
        raise ValueError('Dataset diverso da quello del pilota DPO.')
    env = common.environment()
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainerCallback, set_seed
    from trl import SFTConfig, SFTTrainer
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling
    set_seed(42)
    tokenizer = AutoTokenizer.from_pretrained('models/pilot_dpo_train_v1/adapter', local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    datasets = {s: [tokenize_chosen(row, tokenizer) for row in values] for s, values in rows.items()}
    collator = DataCollatorForLanguageModeling(pad_token_id=tokenizer.pad_token_id,
                                              completion_only_loss=True)
    for values in datasets.values():
        for row in values:
            batch = collator([row])
            mask = torch.tensor(row['completion_mask'], dtype=torch.bool)
            labels = batch['labels'][0]
            if not (labels[~mask] == -100).all() or not torch.equal(labels[mask], batch['input_ids'][0][mask]):
                raise ValueError('Mascheramento della loss non corretto.')
    longest = max(len(r['input_ids']) for values in datasets.values() for r in values)
    print(f'Dati: {report["counts"]}; max {longest} token; loss solo sulla risposta.', flush=True)
    if args.mode == 'check':
        print('SFT CHECK OK: template, maschere, split e ambiente verificati.')
        return
    out = Path(args.output_dir)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output gia presente: per un nuovo esperimento scegli una nuova --output-dir.')
    settings = dict(output_dir=str(out), num_train_epochs=args.epochs, learning_rate=args.learning_rate,
        per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=4,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
        bf16=True, fp16=False, optim='adamw_torch', lr_scheduler_type='constant', warmup_steps=0,
        max_grad_norm=1.0, weight_decay=0.0, max_length=None, packing=False,
        completion_only_loss=True, dataset_kwargs={'skip_prepare_dataset': True},
        dataloader_num_workers=0, prediction_loss_only=True, eval_strategy='no',
        logging_steps=1, logging_nan_inf_filter=False, save_strategy='epoch', save_total_limit=2,
        report_to='none', seed=42, data_seed=42, push_to_hub=False, use_liger_kernel=False)
    common.save(out / 'run_manifest.json', {'model': previous['model'], 'revision': previous['revision'],
        'data': report, 'environment': env, 'lora': previous['lora'], 'sft': settings,
        'quantization': previous['quantization'], 'objective': 'SFT chosen response tokens only',
        'note': 'Esplorativo: budget e learning rate diversi dal DPO. Non confronto causale fra obiettivi. '
                'Nessuna selezione del checkpoint sulla validation; si usa l ultima epoca.'})
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(previous['model'], revision=previous['revision'],
        quantization_config=quant, torch_dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa',
        local_files_only=True)
    model.config.use_cache = False

    class FiniteLogs(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            for name, value in (logs or {}).items():
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    raise ValueError('Metrica non finita: ' + name)

    trainer = SFTTrainer(model=model, args=SFTConfig(**settings),
        train_dataset=Dataset.from_list(datasets['train']), eval_dataset=Dataset.from_list(datasets['validation']),
        processing_class=tokenizer, data_collator=collator,
        peft_config=LoraConfig(**previous['lora']), callbacks=[FiniteLogs()])
    before_params = {n: v.detach().cpu().clone() for n, v in trainer.model.named_parameters() if v.requires_grad}
    if not before_params or any('lora_' not in n for n in before_params):
        raise ValueError('Attesi solo parametri LoRA addestrabili.')
    torch.cuda.reset_peak_memory_stats()
    before = trainer.evaluate(metric_key_prefix='before')
    common.save(out / 'validation_before.json', before)
    trained = trainer.train()
    change = max(float((v.detach().float().cpu() - before_params[n].float()).abs().max())
                 for n, v in trainer.model.named_parameters() if n in before_params)
    if not math.isfinite(change) or change == 0:
        raise ValueError('Aggiornamento adapter non valido.')
    after = trainer.evaluate(metric_key_prefix='after')
    trainer.save_model(str(out / 'adapter'))
    tokenizer.save_pretrained(str(out / 'adapter'))
    trainer.save_state()
    common.save(out / 'training_history.json', trainer.state.log_history)
    common.save(out / 'result.json', {'status': 'completed', 'objective': 'SFT',
        'steps': trainer.state.global_step, 'before': before, 'after': after,
        'train_metrics': trained.metrics, 'max_adapter_parameter_change': change,
        'peak_vram_allocated_gib': torch.cuda.max_memory_allocated() / 2**30,
        'note': 'Loss SFT non confrontabile numericamente con loss DPO. Valutare risposte generate.'})
    print(f'SFT TRAIN OK: {trainer.state.global_step} step. Risultati: {out / "result.json"}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ImportError) as exc:
        print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(1)
