"""Due controlli sul modello base BF16, senza adapter e senza quantizzazione NF4.
Usa gli stessi prompt e decoding del confronto gia eseguito. Nessun training.
"""
import gc
import json
from pathlib import Path
import sys


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    root = Path('results/pilot_dpo_comparison_v1')
    manifest = read(root / 'manifest.json')
    training = Path('models/pilot_dpo_train_v1')
    out = Path('results/pilot_base_bf16_probe_v1')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output gia presente: conserva il primo controllo e condividine i risultati.')
    if not torch.cuda.is_available():
        raise ValueError('CUDA non disponibile.')
    print(f'GPU libera: {torch.cuda.mem_get_info()[0] / 2**30:.2f} GiB', flush=True)
    print('Caricamento base BF16: richiede piu memoria della versione NF4.', flush=True)
    model = AutoModelForCausalLM.from_pretrained(manifest['model'], revision=manifest['revision'],
        torch_dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa')
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(str(training / 'adapter'))
    eos = model.generation_config.eos_token_id
    if eos is None:
        eos = tokenizer.eos_token_id
    eos_set = set(eos if isinstance(eos, list) else [eos])
    selected = [r for r in manifest['inputs'] if r['id'] in ('pilot07_A', 'pilot08_D')]
    if len(selected) != 2:
        raise ValueError('Mancano i due prompt previsti.')
    results = []
    for row in selected:
        prompt = tokenizer.apply_chat_template(row['messages'], tokenize=False, add_generation_prompt=True)
        encoded = tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
        print('Generazione BF16:', row['id'], flush=True)
        with torch.inference_mode():
            ids = model.generate(**encoded, **manifest['decoding'], use_cache=True,
                                 pad_token_id=tokenizer.pad_token_id, eos_token_id=eos)
        tokens = ids[0, encoded['input_ids'].shape[1]:].tolist()
        answer = tokenizer.decode(tokens, skip_special_tokens=True).strip()
        old = read(root / 'records' / (row['id'] + '_base.json'))
        results.append({'id': row['id'], 'messages': row['messages'],
                        'base_nf4_previous': old['answer'], 'base_bf16': answer,
                        'token_ids': tokens,
                        'possibly_truncated': len(tokens) >= manifest['decoding']['max_new_tokens']
                        and (not tokens or tokens[-1] not in eos_set)})
        print('\n===== ' + row['id'] + ' BF16 =====\n' + answer, flush=True)
    out.mkdir(parents=True, exist_ok=True)
    payload = {'model': manifest['model'], 'revision': manifest['revision'],
               'decoding': manifest['decoding'], 'results': results,
               'note': 'Controllo descrittivo su due prompt. BF16 senza adapter confrontato con '
                       'precedente base NF4 (adapter disattivato). Non basta per attribuire causalmente '
                       'le differenze alla sola quantizzazione.'}
    (out / 'result.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\nSalvato:', out / 'result.json')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        if 'out of memory' in str(exc).lower():
            print('Memoria GPU insufficiente per il controllo BF16. Nessun training eseguito. '
                  'Condividi questo errore; non cambiare la configurazione del training.', file=sys.stderr)
        else:
            print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(1)
