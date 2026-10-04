"""Confronto diagnostico NF4 base/LoRA sugli 8 prompt del gruppo validation.
Nessun giudizio automatico. Usa stesso modello, tokenizer, prompt e decoding.
"""
import argparse
from contextlib import nullcontext
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import sys
import uuid


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def hashed(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    allow_nan=False).encode('utf-8')).hexdigest()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(text, encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def save(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False))


def inputs(source, training):
    manifest = read(source / 'manifest.json')
    groups = set(training['data']['source_groups']['validation'])
    rows = []
    for q in manifest['spec']['questions']:
        if q['source_id'] not in groups:
            continue
        for level in ['A', 'B', 'C', 'D']:
            cid = q['id'] + '_' + level
            candidate = read(source / 'candidates' / (cid + '.json'))
            if candidate['manifest_hash'] != hashed(manifest):
                raise ValueError('Candidato non coerente con il manifest: ' + cid)
            rows.append({'id': cid, 'question': q['question'], 'level': level,
                         'group': q['source_id'], 'messages': candidate['messages']})
    if not rows:
        raise ValueError('Nessun prompt validation.')
    for split in ['train', 'validation']:
        exported = [json.loads(line) for line in (source / 'export' / (split + '.jsonl')).read_text(
            encoding='utf-8-sig').splitlines() if line.strip()]
        if hashed(exported) != training['data']['hashes'][split]:
            raise ValueError('Dataset cambiato rispetto al training.')
    return rows


def render(root, rows, manifest):
    blocks = ['# Confronto diagnostico base / SFT',
              'Otto prompt: due domande per quattro livelli, un solo gruppo di fonte. '
              'Non sono otto osservazioni indipendenti e non costituiscono un test finale.',
              'Lato delle risposte randomizzato. Non aprire comparison_key.json prima dei giudizi. '
              'Il fatto che una risposta provenga dal SFT non la rende automaticamente migliore.',
              'Per ogni confronto: verifica correttezza e supporto nel contesto; poi valuta '
              'adeguatezza al livello e chiarezza. Sono possibili parita e regressioni.']
    key = {}
    for row in rows:
        order = ['base', 'sft']
        random.Random(hashed(['blind-v1', row['id']])).shuffle(order)
        key[row['id']] = {str(i + 1): side for i, side in enumerate(order)}
        blocks.append(f"\n## {row['id']} — livello {row['level']}\n\n{row['question']}")
        blocks.append('\n### Prompt completo\n\n' + row['messages'][-1]['content'])
        for i, side in enumerate(order, 1):
            result = read(root / 'records' / (row['id'] + '_' + side + '.json'))
            if result['manifest_hash'] != hashed(manifest):
                raise ValueError('Record non coerente.')
            flags = result['flags']
            blocks.append(f'\n### Risposta {i}\n\n' + result['answer'] +
                          ('\n\n**Segnalazioni:** ' + ', '.join(flags) if flags else ''))
        blocks.append('\nGiudizio: da compilare.\n\nMotivo: da compilare.\n')
    write(root / 'comparison.md', '\n\n'.join(blocks))
    save(root / 'comparison_key.json', key)
    print('Confronto salvato:', root / 'comparison.md')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-dir', default='models/pilot_sft_train_v1')
    parser.add_argument('--source-run', default='results/dpo_pilot_curated_v1')
    parser.add_argument('--output-dir', default='results/pilot_sft_comparison_v1')
    parser.add_argument('--max-new-tokens', type=int, default=384)
    parser.add_argument('--check-data', action='store_true')
    args = parser.parse_args()
    train_root, source, out = map(Path, [args.training_dir, args.source_run, args.output_dir])
    training = read(train_root / 'run_manifest.json')
    if read(train_root / 'result.json')['status'] != 'completed':
        raise ValueError('Training non completato.')
    rows = inputs(source, training)
    print(f'Prompt: {len(rows)}; generazioni previste: {2 * len(rows)}.', flush=True)
    if args.check_data:
        print('CHECK DATA OK. Nessun modello caricato.')
        return
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise ValueError('Richiesta GPU CUDA con BF16.')
    if args.max_new_tokens < 1:
        raise ValueError('max-new-tokens deve essere positivo.')
    if torch.cuda.mem_get_info()[0] < 5 * 2**30:
        raise ValueError('Libera memoria GPU, ad esempio scaricando i modelli Ollama.')
    adapter = train_root / 'adapter'
    adapter_files = sorted(adapter.glob('*.safetensors'))
    if not adapter_files:
        raise ValueError('Pesi adapter assenti.')
    tokenizer = AutoTokenizer.from_pretrained(str(adapter))
    manifest = {'schema': 1, 'training_hash': hashed(training), 'inputs': rows,
        'model': training['model'], 'revision': training['revision'],
        'adapter_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in adapter_files},
        'adapter_config': read(adapter / 'adapter_config.json'),
        'tokenizer_files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(adapter.glob('*')) if p.is_file() and p.suffix in ['.json', '.txt']},
        'decoding': {'do_sample': False, 'max_new_tokens': args.max_new_tokens,
                     'repetition_penalty': 1.0, 'num_beams': 1},
        'versions': {n: importlib.metadata.version(n) for n in ['torch', 'transformers', 'peft', 'bitsandbytes']},
        'note': 'NF4 in entrambi i casi. Base = adapter disattivato. SFT = adapter attivo. '
                'Nessun guardrail, retrieval, riscrittura o giudizio automatico.'}
    if (out / 'manifest.json').exists():
        if read(out / 'manifest.json') != manifest:
            raise ValueError('Configurazione cambiata: usa una nuova --output-dir.')
    else:
        if out.exists() and any(out.iterdir()):
            raise ValueError('Output non vuoto senza manifest.')
        save(out / 'manifest.json', manifest)
    pending = [(row, side) for index, row in enumerate(rows)
               for side in (['base', 'sft'] if index % 2 == 0 else ['sft', 'base'])
               if not (out / 'records' / (row['id'] + '_' + side + '.json')).exists()]
    if pending:
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
        base = AutoModelForCausalLM.from_pretrained(training['model'], revision=training['revision'],
            quantization_config=quant, torch_dtype=torch.bfloat16, device_map={'': 0},
            attn_implementation='sdpa')
        model = PeftModel.from_pretrained(base, str(adapter), is_trainable=False)
        model.eval()
        eos = model.generation_config.eos_token_id
        if eos is None:
            eos = tokenizer.eos_token_id
        eos_ids = set(eos if isinstance(eos, list) else [eos])
        for row, side in pending:
            print(f"Generazione {row['id']} ({side})...", flush=True)
            prompt = tokenizer.apply_chat_template(row['messages'], tokenize=False, add_generation_prompt=True)
            encoded = tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to('cuda')
            with torch.inference_mode(), (model.disable_adapter() if side == 'base' else nullcontext()):
                ids = model.generate(**encoded, **manifest['decoding'], use_cache=True,
                                     pad_token_id=tokenizer.pad_token_id, eos_token_id=eos)
            completion = ids[0, encoded['input_ids'].shape[1]:].tolist()
            answer = tokenizer.decode(completion, skip_special_tokens=True).strip()
            flags = []
            if not answer:
                flags.append('risposta_vuota')
            if len(completion) >= args.max_new_tokens and (not completion or completion[-1] not in eos_ids):
                flags.append('limite_token_senza_EOS')
            save(out / 'records' / (row['id'] + '_' + side + '.json'), {
                'manifest_hash': hashed(manifest), 'id': row['id'], 'setting': side,
                'answer': answer, 'completion_ids': completion, 'flags': flags})
    render(out, rows, manifest)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ImportError) as exc:
        print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(1)

