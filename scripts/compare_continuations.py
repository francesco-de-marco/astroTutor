"""Tre risposte per prompt: SFT iniziale, SFT+DPO, SFT proseguito.
Stesso runtime NF4 e decoding; nessuna etichetta di qualita automatica.
"""
import hashlib
from pathlib import Path
import random
import sys
import os
os.environ['HF_HUB_OFFLINE'] = '1'
import importlib.metadata
import compare_dpo_pilot as common


def weights(path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.glob('*.safetensors')}


def main():
    roots = {'initial_sft': Path('models/pilot_sft_train_v1'),
             'after_dpo': Path('models/pilot_after_sft_dpo_v1'),
             'after_sft': Path('models/pilot_after_sft_sft_control_v1')}
    train = {name: common.read(root / 'run_manifest.json') for name, root in roots.items()}
    parent = weights(roots['initial_sft'] / 'adapter')
    for name, root in roots.items():
        if common.read(root / 'result.json')['status'] != 'completed':
            raise ValueError('Training incompleto: ' + name)
        if any(train[name][k] != train['initial_sft'][k] for k in ['model', 'revision', 'data']):
            raise ValueError('Modello o dataset diversi fra rami.')
        if name != 'initial_sft' and train[name]['parent_adapter_hashes'] != parent:
            raise ValueError('I rami non derivano dallo stesso SFT.')
    rows = common.inputs(Path('results/dpo_pilot_curated_v1'), train['initial_sft'])
    out = Path('results/pilot_continuations_comparison_v1')
    decoding = {'do_sample': False, 'max_new_tokens': 384, 'repetition_penalty': 1.0, 'num_beams': 1}
    manifest = {'inputs': rows, 'training': train, 'decoding': decoding,
                'adapter_hashes': {n: weights(r / 'adapter') for n, r in roots.items()},
                'versions': {n: importlib.metadata.version(n) for n in ['torch', 'transformers', 'peft', 'bitsandbytes']}}
    if (out / 'manifest.json').exists():
        if common.read(out / 'manifest.json') != manifest:
            raise ValueError('Configurazione cambiata rispetto al confronto esistente.')
    else:
        if out.exists() and any(out.iterdir()):
            raise ValueError('Output senza manifest.')
        common.save(out / 'manifest.json', manifest)
    pending = [(row, name) for row in rows for name in roots
               if not (out / 'records' / (row['id'] + '_' + name + '.json')).exists()]
    if pending:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        tokenizer = AutoTokenizer.from_pretrained(str(roots['initial_sft'] / 'adapter'), local_files_only=True)
        for name in ['after_dpo', 'after_sft']:
            other = AutoTokenizer.from_pretrained(str(roots[name] / 'adapter'), local_files_only=True)
            if other.get_vocab() != tokenizer.get_vocab() or other.chat_template != tokenizer.chat_template:
                raise ValueError('Tokenizer differenti fra rami.')
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
        base = AutoModelForCausalLM.from_pretrained(train['initial_sft']['model'],
            revision=train['initial_sft']['revision'], local_files_only=True,
            quantization_config=quant, torch_dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa')
        model = PeftModel.from_pretrained(base, str(roots['initial_sft'] / 'adapter'),
                                         adapter_name='initial_sft', is_trainable=False)
        for name in ['after_dpo', 'after_sft']:
            model.load_adapter(str(roots[name] / 'adapter'), adapter_name=name, is_trainable=False)
        model.eval()
        eos = model.generation_config.eos_token_id or tokenizer.eos_token_id
        eos_set = set(eos if isinstance(eos, list) else [eos])
        for row, name in pending:
            print(f"Generazione {row['id']} {name}", flush=True)
            model.set_adapter(name)
            prompt = tokenizer.apply_chat_template(row['messages'], tokenize=False, add_generation_prompt=True)
            encoded = tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
            with torch.inference_mode():
                output = model.generate(**encoded, **decoding, use_cache=True,
                                        pad_token_id=tokenizer.pad_token_id, eos_token_id=eos)
            tokens = output[0, encoded['input_ids'].shape[1]:].tolist()
            common.save(out / 'records' / (row['id'] + '_' + name + '.json'), {
                'manifest_hash': common.hashed(manifest), 'answer': tokenizer.decode(tokens, skip_special_tokens=True).strip(),
                'completion_ids': tokens, 'truncated': len(tokens) >= 384 and tokens[-1] not in eos_set})
    text = ['# Confronto continuazioni SFT',
            'Tre configurazioni in ordine casuale. Due domande, quattro livelli: diagnostica, non test indipendente. '
            'Valutare separatamente correttezza, supporto nel contesto e adeguatezza al livello. Parita ammesse. '
            'Non aprire la chiave prima dei giudizi.']
    key = {}
    for row in rows:
        order = list(roots)
        random.Random(common.hashed(['continuations-v1', row['id']])).shuffle(order)
        key[row['id']] = {str(i + 1): name for i, name in enumerate(order)}
        text.append(f"## {row['id']}\n\n{row['messages'][-1]['content']}")
        for i, name in enumerate(order, 1):
            record = common.read(out / 'records' / (row['id'] + '_' + name + '.json'))
            if record['manifest_hash'] != common.hashed(manifest):
                raise ValueError('Risultato non coerente con manifest.')
            text.append(f'### Risposta {i}\n\n' + record['answer'] +
                        ('\n\nATTENZIONE: limite token raggiunto.' if record['truncated'] else ''))
        text.append('Giudizio: da compilare.\n\nMotivazione: da compilare.')
    common.write(out / 'comparison.md', '\n\n'.join(text))
    common.save(out / 'comparison_key.json', key)
    print('Salvato:', out / 'comparison.md')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ImportError) as exc:
        print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(1)
