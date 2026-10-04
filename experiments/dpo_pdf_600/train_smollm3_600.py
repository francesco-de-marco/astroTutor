"""Training diagnostico DPO, Qwen2.5-3B-Instruct + NF4 + LoRA.

Dataset sintetico PDF: check -> smoke -> train. Nessun test finale incluso.
Non usa Ollama, non modifica i vecchi modelli e non pubblica dati o pesi.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import uuid

# Read by huggingface_hub at import time. Applies only to this Python process.
os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '180')
os.environ.setdefault('HF_HUB_ETAG_TIMEOUT', '60')

BASE = 'HuggingFaceTB/SmolLM3-3B'
PINS = {'trl': '0.24.0', 'peft': '0.17.1', 'bitsandbytes': '0.48.1',
        'transformers': '4.57.6'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def hashed(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode('utf-8')).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def load_data(directory):
    directory = Path(directory)
    manifest = read(directory / 'manifest.json')
    for name in ['train_dpo.jsonl', 'provenance.jsonl', 'contexts.json']:
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if actual != manifest['sha256'][name]:
            raise ValueError('Checksum non corrispondente: ' + name)
    rows = [json.loads(x) for x in (directory/'train_dpo.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    provenance = [json.loads(x) for x in (directory/'provenance.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    if len(rows) != 600 or len(provenance) != 600:
        raise ValueError('Attese 600 coppie e 600 record di provenienza.')
    for i, (row, meta) in enumerate(zip(rows, provenance), 1):
        pair_hash = hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
        if pair_hash != meta['pair_sha256'] or meta['row_1based'] != i or meta['split'] != 'train':
            raise ValueError('Abbinamento provenienza non valido alla riga ' + str(i))
        if set(row) != {'prompt','chosen','rejected'} or row['chosen'] == row['rejected']:
            raise ValueError('Coppia non valida.')
        if [m['role'] for m in row['prompt']] != ['system','user']:
            raise ValueError('Prompt non valido.')
        for key in ['chosen','rejected']:
            if len(row[key]) != 1 or row[key][0]['role'] != 'assistant' or not row[key][0]['content'].strip():
                raise ValueError('Risposta non valida.')
    families = {m['question_id'] for m in provenance}
    prompts = Counter(hashed(r['prompt']) for r in rows)
    if len(families) != 75 or len(prompts) != 300 or set(prompts.values()) != {2}:
        raise ValueError('Raggruppamenti inattesi.')
    return {'train':rows}, {'counts':{'train':600}, 'unique_questions':75,
        'hashes':{'train':hashed(rows)}, 'provenance_hash':hashed(provenance),
        'human_validated':False, 'validation_available':False}


def preload_manifest(out, model_id, mode):
    """Retry only a run stopped before trainer creation; never overwrite training."""
    out = Path(out)
    if not out.exists() or not any(out.iterdir()):
        return None
    if {p.name for p in out.iterdir()} != {'run_manifest.json'}:
        raise ValueError('Output contiene risultati o checkpoint: ripresa automatica non consentita.')
    previous = read(out / 'run_manifest.json')
    if previous.get('model') != model_id or previous.get('mode') != mode:
        raise ValueError('Il manifest esistente appartiene a un altro modello o modo.')
    return previous


def environment():
    versions = {}
    for name in ['torch', 'transformers', 'datasets', 'accelerate', 'trl', 'peft', 'bitsandbytes']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            raise ValueError(f'Manca {name}. Installa requirements-dpo-pilot.txt.')
    for name, expected in PINS.items():
        if versions[name] != expected:
            raise ValueError(f'{name}: atteso {expected}, trovato {versions[name]}.')
    import torch
    import bitsandbytes as bnb
    from peft import LoraConfig
    from trl import DPOConfig, DPOTrainer
    if not torch.cuda.is_available():
        raise ValueError('CUDA non disponibile in questo interprete.')
    if not torch.cuda.is_bf16_supported():
        raise ValueError('Questa configurazione richiede BF16; GPU diversa da quella prevista.')
    free, total = torch.cuda.mem_get_info()
    if free < 5 * 2**30:
        raise ValueError('Meno di 5 GiB GPU liberi. Scarica i modelli Ollama e chiudi altri lavori GPU.')
    layer = bnb.nn.Linear4bit(64, 64, bias=False, compute_dtype=torch.bfloat16,
                             quant_type='nf4').to('cuda')
    x = torch.randn(2, 64, device='cuda', dtype=torch.bfloat16, requires_grad=True)
    layer(x).float().square().mean().backward()
    if x.grad is None or not torch.isfinite(x.grad).all():
        raise ValueError('Test forward/backward NF4 fallito.')
    del layer, x
    torch.cuda.empty_cache()
    return {'versions': versions, 'python': platform.python_version(),
            'gpu': torch.cuda.get_device_name(0), 'vram_gib': total / 2**30,
            'free_gib_at_start': free / 2**30, 'cuda_build': torch.version.cuda}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check', 'smoke', 'train'])
    parser.add_argument('--data-dir', default=str(Path(__file__).resolve().parent / 'dataset_consegna'))
    parser.add_argument('--model', default=BASE)
    parser.add_argument('--output-dir')
    parser.add_argument('--revision', help='Commit HF del modello; altrimenti risolto e registrato.')
    args = parser.parse_args()
    model_id = args.model
    if model_id != BASE:
        raise ValueError('Questo trainer e dedicato a SmolLM3-3B senza extended thinking.')
    rows, data_report = load_data(args.data_dir)
    print('Dataset:', data_report['counts'], flush=True)
    env = environment()
    print('Ambiente:', json.dumps(env, ensure_ascii=False), flush=True)
    if args.mode == 'check':
        print('CHECK OK: dataset, import, CUDA e forward/backward NF4. Nessun modello scaricato.')
        return

    out = Path(args.output_dir or (Path(__file__).resolve().parent / 'runs' / (model_id.replace('/', '__') + '_' + args.mode + '_v1')))
    previous_manifest = preload_manifest(out, model_id, args.mode)
    import torch
    from datasets import Dataset
    from huggingface_hub import model_info
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainerCallback, set_seed
    from trl import DPOConfig, DPOTrainer
    from trl.data_utils import maybe_apply_chat_template

    set_seed(42)
    if previous_manifest:
        revision = previous_manifest['revision']
        if args.revision and args.revision != revision:
            raise ValueError('La ripresa richiede la stessa revisione del primo tentativo.')
        print('Ripresa caricamento della stessa revisione; riutilizzo cache Hugging Face.', flush=True)
    else:
        revision = model_info(model_id, revision=args.revision or 'main').sha
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    prepared = {}
    lengths = []
    for split, values in rows.items():
        prepared[split] = []
        for row in values:
            rendered = maybe_apply_chat_template(row, tokenizer, enable_thinking=False)
            tokenized = DPOTrainer.tokenize_row(rendered, tokenizer, add_special_tokens=False)
            lengths.extend(len(tokenized['prompt_input_ids']) + len(tokenized[k])
                           for k in ['chosen_input_ids', 'rejected_input_ids'])
            # Testo gia formattato: TRL non deve applicare un secondo chat template.
            prepared[split].append(rendered)
    longest = max(lengths)
    if longest > 1536:
        raise ValueError(f'Sequenza di {longest} token: supera il limite prudente del pilota. Nessun troncamento eseguito.')
    print(f'Sequenza massima: {longest} token. Nessun troncamento.', flush=True)
    smoke = args.mode == 'smoke'
    if smoke:
        # Eight diverse question/level prompts, both negative types: only a technical check.
        prepared['train'] = [prepared['train'][q*8+l*2+n] for q,l in [(0,0),(3,1),(6,2),(9,3),(12,0),(15,1),(18,2),(21,3)] for n in (0,1)]
    data_report['rows_used_this_run'] = len(prepared['train'])
    settings = dict(output_dir=str(out), beta=0.1, loss_type='sigmoid',
        learning_rate=5e-6, num_train_epochs=2, max_steps=3 if smoke else -1,
        per_device_train_batch_size=1, per_device_eval_batch_size=1,
        gradient_accumulation_steps=1 if smoke else 4,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
        bf16=True, fp16=False, optim='adamw_torch', lr_scheduler_type='constant',
        warmup_steps=0, max_grad_norm=1.0, weight_decay=0.0,
        max_length=longest + 8, max_prompt_length=None, max_completion_length=None,
        precompute_ref_log_probs=True, precompute_ref_batch_size=1,
        use_logits_to_keep=True, use_liger_kernel=False, disable_dropout=True,
        logging_steps=1, logging_nan_inf_filter=False, report_to='none',
        save_strategy='no' if smoke else 'epoch', save_total_limit=2,
        eval_strategy='no', dataloader_num_workers=0, dataset_num_proc=1,
        seed=42, data_seed=42, push_to_hub=False)
    lora = dict(r=8, lora_alpha=16, lora_dropout=0.0, bias='none', task_type='CAUSAL_LM',
                target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj'])
    manifest = {'model': model_id, 'revision': revision, 'data': data_report,
         'environment': env, 'dpo': settings, 'lora': lora, 'quantization': 'NF4 double quant BF16',
         'chat_template_kwargs': {'enable_thinking': False},
         'token_lengths': {'min': min(lengths), 'max': longest},
         'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'mode': args.mode, 'note': '600 confronti sintetici, 75 domande, 300 prompt. Nessuna validation o test. '
         'Obiettivo correttezza e pertinenza; nessuna revisione umana indipendente.'}
    if previous_manifest:
        for key in ['model', 'revision', 'data', 'dpo', 'lora', 'quantization', 'chat_template_kwargs', 'mode']:
            if previous_manifest.get(key) != manifest[key]:
                raise ValueError('Configurazione cambiata rispetto al tentativo interrotto: ' + key)
        save(out.parent / 'preload_retry_history' / (out.name + '_' + uuid.uuid4().hex + '.json'), previous_manifest)
    save(out / 'run_manifest.json', manifest)
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                               bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
    print('Caricamento modello:', model_id, flush=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision,
        quantization_config=quant, torch_dtype=torch.bfloat16, device_map={'': 0},
        attn_implementation='sdpa')
    model.config.use_cache = False

    class FiniteLogs(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            for key, value in (logs or {}).items():
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    raise ValueError('Metrica non finita: ' + key)

    trainer = DPOTrainer(model=model, ref_model=None, args=DPOConfig(**settings),
        train_dataset=Dataset.from_list(prepared['train']),
        processing_class=tokenizer,
        peft_config=LoraConfig(**lora), callbacks=[FiniteLogs()])
    trainer.model.print_trainable_parameters()
    before = {n: v.detach().cpu().clone() for n, v in trainer.model.named_parameters() if v.requires_grad}
    if not before or any('lora_' not in n for n in before):
        raise ValueError('Parametri addestrabili inattesi: previsto solo LoRA.')
    torch.cuda.reset_peak_memory_stats()
    # Con adapter inizializzati a zero, policy e riferimento coincidono: loss iniziale ~log(2).
    initial = {'available': False, 'reason': 'No held-out validation supplied'}
    save(out / 'validation_before.json', initial)
    result = trainer.train()
    deltas = [float((v.detach().float().cpu() - before[n].float()).abs().max())
              for n, v in trainer.model.named_parameters() if n in before]
    changed = max(deltas)
    if not math.isfinite(changed) or changed <= 0:
        raise ValueError('Nessun aggiornamento LoRA finito rilevato.')
    final = {'available': False, 'reason': 'No held-out validation supplied'}
    adapter = out / 'adapter'
    trainer.save_model(str(adapter))
    tokenizer.save_pretrained(str(adapter))
    trainer.save_state()
    save(out / 'validation_after.json', final)
    save(out / 'training_history.json', trainer.state.log_history)
    save(out / 'result.json', {'status': 'completed', 'mode': args.mode,
        'steps': trainer.state.global_step, 'train_metrics': result.metrics,
        'max_adapter_parameter_change': changed,
        'peak_vram_allocated_gib': torch.cuda.max_memory_allocated() / 2**30,
        'peak_vram_reserved_gib': torch.cuda.max_memory_reserved() / 2**30,
        'adapter': str(adapter), 'before': initial, 'after': final,
        'interpretation': 'Loss e reward margin misurano la preferenza relativa al riferimento. '
                          'Non sono voti di correttezza o di efficacia didattica.'})
    print(f'\n{args.mode.upper()} OK: {trainer.state.global_step} step, adapter aggiornato e salvato.')
    print(f'Picco VRAM allocata: {torch.cuda.max_memory_allocated() / 2**30:.2f} GiB')
    print('Risultati:', out / 'result.json')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ImportError) as exc:
        print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(1)
