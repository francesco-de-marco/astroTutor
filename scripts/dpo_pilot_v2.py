"""Pilota preferenze AstroTutor v2. Solo libreria standard; Ollama locale per generate.

Eseguire dalla root del progetto. generate -> review -> export.
Non avvia training. Non modifica indice, codice del tutor o risultati precedenti.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys
from urllib.request import Request, urlopen
import uuid

LEVELS = {
    'A': 'Scuola primaria, 6-10 anni: nessun prerequisito astronomico. Usa parole comuni e spiega i concetti necessari senza infantilizzare.',
    'B': 'Scuola secondaria di primo grado: conoscenze scientifiche elementari. Spiega il meccanismo e definisci i termini nuovi.',
    'C': 'Scuola secondaria di secondo grado: basi di fisica. Esplicita i passaggi causali e usa termini tecnici pertinenti spiegandoli quando necessario.',
    'D': 'Università: basi di fisica e astronomia. Usa terminologia precisa, relazioni causali e limiti delle affermazioni; evita premesse elementari superflue.',
}
OPPOSITE = {'A': 'D', 'B': 'C', 'C': 'B', 'D': 'A'}
SYSTEM = (
    'Sei AstroTutor. Rispondi in italiano alla domanda astronomica adattando la spiegazione '
    'alle conoscenze dello studente. Usa il contesto come base fattuale; non inventare dati, '
    'formule o fenomeni. Se il contesto non basta, dichiara il limite. '
    'Puoi riformulare e spiegare le relazioni presenti. Usa analogie solo se presenti nel '
    'contesto, segnalando che sono analogie. Rispondi direttamente: non aggiungere quiz, '
    'piani di studio o domande allo studente. La precisione scientifica vale a tutti i livelli. '
    'Scegli la lunghezza necessaria: il livello non impone una quota di parole. '
    'Non menzionare il codice del livello nella risposta. '
    'Produci soltanto la risposta finale, senza simulare turni user/assistant o commenti '
    'sulle istruzioni. Evita introduzioni generiche, ripetizioni e riepiloghi duplicati. '
    'Non aggiungere cause fisiche o nomi di effetti che il contesto non fornisce. '
    'Distingui condizioni necessarie e sufficienti: non trasformare un possibile '
    'disallineamento o una correlazione in una causa sufficiente. '
    'Per i livelli avanzati privilegia precisione e limiti, senza inventare dettagli '
    'per rendere la risposta apparentemente piu tecnica.'
)
OPTIONS = {'temperature': 0.1, 'seed': 42, 'num_ctx': 4096, 'num_predict': 850,
           'repeat_penalty': 1.0, 'frequency_penalty': 0.0, 'presence_penalty': 0.0}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode('utf-8')).hexdigest()


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(text, encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def save(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False))


def stamp():
    return datetime.now(timezone.utc).isoformat()


def api(endpoint, payload=None):
    request = Request('http://127.0.0.1:11434' + endpoint,
                      data=None if payload is None else json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=600) as response:
        return json.load(response)


def identity(model):
    for row in api('/api/tags')['models']:
        if model in (row.get('name'), row.get('model')):
            return {'name': model, 'digest': row['digest'], 'details': row.get('details')}
    raise ValueError(f'Modello locale assente: {model}. Controlla ollama list.')


def build_prompt(question, level, context):
    """Riutilizzare esattamente questo builder per la futura baseline del pilota."""
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': f'Profilo {level}: {LEVELS[level]}\n\n'
             f'Contesto:\n{context}\n\nDomanda: {question}'}]


def validate_spec(spec):
    ids = set()
    if not spec.get('questions'):
        raise ValueError('Domande mancanti.')
    for q in spec['questions']:
        if q['id'] in ids or not q['id'].isalnum() or not q['question'].strip():
            raise ValueError('ID non valido/duplicato o domanda vuota.')
        ids.add(q['id'])
        source = spec['sources'][q['source_id']]
        if source['split'] not in ('train', 'validation') or not source['context'].strip():
            raise ValueError('Fonte o split non valido.')


def generate(args):
    spec = read(args.spec)
    validate_spec(spec)
    root = Path(args.run_dir)
    model = identity(args.model)
    manifest = {'schema': 1, 'spec': spec, 'model': model, 'options': OPTIONS,
                'ollama_version': api('/api/version'), 'system': SYSTEM, 'levels': LEVELS,
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path = root / 'manifest.json'
    if path.exists():
        if read(path) != manifest:
            raise ValueError('Configurazione cambiata: usa una nuova --run-dir.')
    else:
        if root.exists() and any(root.iterdir()):
            raise ValueError('Cartella non vuota senza manifest.')
        save(path, manifest)
    total = len(spec['questions']) * 4
    new = 0
    for q in spec['questions']:
        for level in LEVELS:
            cid = q['id'] + '_' + level
            path = root / 'candidates' / (cid + '.json')
            if path.exists():
                row = read(path)
                if row['manifest_hash'] != digest(manifest) or row['id'] != cid:
                    raise ValueError('Cache incompatibile: ' + cid)
                continue
            if args.limit is not None and new >= args.limit:
                print('Limite raggiunto. Rilancia senza --limit per completare.')
                return
            messages = build_prompt(q['question'], level, spec['sources'][q['source_id']]['context'])
            print(f'Generazione {cid}...', flush=True)
            attempt_paths = []
            accepted = None
            for attempt in range(3):
                options = dict(OPTIONS, seed=42 + attempt)
                raw = api('/api/chat', {'model': args.model, 'messages': messages,
                                       'options': options, 'stream': False, 'keep_alive': '5m'})
                answer = raw.get('message', {}).get('content', '').strip()
                issues = format_issues(raw, options)
                attempt_path = root / 'attempts' / cid / (stamp().replace(':', '-') + '.json')
                save(attempt_path, {'options': options, 'issues': issues, 'response': raw})
                attempt_paths.append(str(attempt_path.relative_to(root)))
                if identity(args.model) != model:
                    raise ValueError('Modello cambiato durante la generazione.')
                if not issues:
                    accepted = (answer, raw, options)
                    break
                print(f'  Tentativo {attempt + 1} escluso: {issues}', flush=True)
            if accepted is None:
                raise ValueError(f'{cid}: tre tentativi non validi. Originali in attempts; '
                                 'nessun candidato accettato. Controllare prima di riprovare.')
            answer, raw, options = accepted
            save(path, {'id': cid, 'manifest_hash': digest(manifest), 'messages': messages,
                        'answer': answer, 'created_at': stamp(), 'ollama_response': raw,
                        'actual_options': options, 'attempt_files': attempt_paths,
                        'quality_status': 'format_checked_not_fact_checked'})
            new += 1
    print(f'Candidati disponibili: {total}/{total}. Ora esegui review.')


def pairs(root):
    manifest = read(root / 'manifest.json')
    spec = manifest['spec']
    validate_spec(spec)
    records = {}
    for q in spec['questions']:
        for level in LEVELS:
            cid = q['id'] + '_' + level
            path = root / 'candidates' / (cid + '.json')
            if not path.exists():
                raise ValueError('Completa generate: manca ' + cid)
            row = read(path)
            expected = build_prompt(q['question'], level, spec['sources'][q['source_id']]['context'])
            if (row['manifest_hash'] != digest(manifest) or row['id'] != cid
                    or row['messages'] != expected or not row['answer'].strip()):
                raise ValueError('Candidato incoerente: ' + cid)
            records[cid] = row
    output = []
    for q in spec['questions']:
        source = spec['sources'][q['source_id']]
        for level in LEVELS:
            pid = q['id'] + '_' + level
            ids = [pid, q['id'] + '_' + OPPOSITE[level]]
            random.Random(digest(['pair-order-v1', pid])).shuffle(ids)
            row = {'id': pid, 'source_id': q['source_id'], 'question_id': q['id'],
                   'split': source['split'], 'question': q['question'], 'level': level,
                   'context': source['context'], 'source_url': source['url'],
                   'prompt': records[pid]['messages'], 'candidate_ids': ids,
                   'answers': [records[c]['answer'] for c in ids]}
            row['pair_hash'] = digest(row)
            output.append(row)
    random.Random(42).shuffle(output)
    return output


def ask(prompt, allowed):
    while True:
        value = input(prompt).strip().lower()
        if value in allowed:
            return value
        print('Valori ammessi: ' + ', '.join(allowed))


def review(args):
    root = Path(args.run_dir)
    rows = pairs(root)
    for row in rows:
        path = root / 'reviews' / (row['id'] + '.json')
        if path.exists():
            if read(path)['pair_hash'] != row['pair_hash']:
                raise ValueError('Revisione non corrisponde ai candidati.')
            continue
        print('\n' + '=' * 70)
        print(f"{row['id']} | {LEVELS[row['level']]}\nDomanda: {row['question']}")
        print(f"\nFonte da verificare: {row['source_url']}\nContesto: {row['context']}")
        for i, answer in enumerate(row['answers'], 1):
            print(f'\nRISPOSTA {i}\n{answer}')
        print('\nPreferisci per prerequisiti, termini spiegati e profondita. La lunghezza da sola non basta.')
        decision = ask('Scelta [1/2 = preferita, t = equivalenti, r = scarta, q = esci]: ',
                       ['1', '2', 't', 'r', 'q'])
        if decision == 'q':
            break
        checked = False
        if decision in ('1', '2'):
            checked = ask('Hai controllato fonte/contesto, entrambe le risposte sono corrette e supportate, '
                          'e la preferenza dipende dal livello? [s/n]: ', ['s', 'n']) == 's'
            if not checked:
                print('Coppia scartata: non adatta a isolare la calibrazione del livello.')
                decision = 'r'
        reason = ''
        while not reason:
            reason = input('Motivo breve e concreto: ').strip()
        save(path, {'pair_hash': row['pair_hash'], 'decision': decision,
                    'quality_checks_passed': checked, 'reason': reason,
                    'reviewer': args.reviewer, 'review_kind': args.review_kind,
                    'reviewed_at': stamp()})
    summary(root, rows)


def summary(root, rows):
    counts = Counter()
    for row in rows:
        path = root / 'reviews' / (row['id'] + '.json')
        counts[read(path)['decision'] if path.exists() else 'pending'] += 1
    print('Revisione:', dict(counts), '| 1/2 accettate, t pari, r scartate.')


def export(args):
    root = Path(args.run_dir)
    rows = pairs(root)
    output = {'train': [], 'validation': []}
    provenance = []
    for row in rows:
        path = root / 'reviews' / (row['id'] + '.json')
        if not path.exists():
            raise ValueError('Revisione incompleta. Completa review prima di export.')
        rev = read(path)
        if rev['pair_hash'] != row['pair_hash']:
            raise ValueError('Revisione obsoleta: ' + row['id'])
        if rev['decision'] in ('t', 'r'):
            continue
        if (rev['decision'] not in ('1', '2') or rev['quality_checks_passed'] is not True
                or not rev['reason'].strip() or not rev['reviewer'].strip()
                or rev['review_kind'] not in ('human', 'ai_assisted')):
            raise ValueError('Revisione non valida: ' + row['id'])
        chosen = int(rev['decision']) - 1
        if row['answers'][0] == row['answers'][1]:
            raise ValueError('Risposte identiche marcate come preferenza: ' + row['id'])
        output[row['split']].append({'prompt': row['prompt'],
            'chosen': [{'role': 'assistant', 'content': row['answers'][chosen]}],
            'rejected': [{'role': 'assistant', 'content': row['answers'][1 - chosen]}]})
        provenance.append({'id': row['id'], 'split': row['split'], 'source_id': row['source_id'],
                           'candidate_ids': row['candidate_ids'], 'review': rev,
                           'chosen_words': len(row['answers'][chosen].split()),
                           'rejected_words': len(row['answers'][1 - chosen].split())})
    if not all(output.values()):
        raise ValueError('Servono coppie accettate in entrambi gli split; nessun export prodotto.')
    for split, values in output.items():
        write_text(root / 'export' / (split + '.jsonl'),
                   ''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in values))
    save(root / 'export' / 'provenance.json', provenance)
    save(root / 'export' / 'summary.json', {
        'counts': {k: len(v) for k, v in output.items()},
        'source_groups': {k: sorted({r['source_id'] for r in provenance if r['split'] == k}) for k in output},
        'review_kinds': dict(Counter(r['review']['review_kind'] for r in provenance)),
        'warning': 'Pilota: 8 domande, 4 gruppi di fonte; risposte riusate tra livelli. '
                   'Non 32 osservazioni indipendenti. Validation diagnostica, nessun test finale.',
        'manifest_hash': digest(read(root / 'manifest.json'))})
    print('Export:', {k: len(v) for k, v in output.items()})
    print('Formato conversazionale prompt/chosen/rejected. Nessun training eseguito.')



def format_issues(raw, options):
    """Indicatori di formato, non un giudizio di correttezza scientifica."""
    answer = raw.get('message', {}).get('content', '').strip()
    issues = []
    if not answer:
        issues.append('risposta_vuota')
    if not raw.get('done') or raw.get('done_reason') != 'stop':
        issues.append('completamento_non_regolare')
    if raw.get('eval_count', 0) >= options['num_predict']:
        issues.append('limite_token_raggiunto')
    if re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\ufffd]', answer):
        issues.append('caratteri_estranei_o_danneggiati')
    if re.search(r'(?im)^\s*(?:user|assistant|system|utente|assistente)\s*:?\s*$', answer):
        issues.append('turno_dialogo_simulato')
    if re.search(r'<\|(?:im_start|im_end|endoftext)\|>|\[/?INST\]', answer):
        issues.append('token_template_esposto')
    return issues


def audit(args):
    root = Path(args.run_dir)
    manifest = read(root / 'manifest.json')
    flags = {}
    for path in sorted((root / 'candidates').glob('*.json')):
        row = read(path)
        issues = format_issues(row['ollama_response'], row.get('actual_options', manifest['options']))
        if issues:
            flags[row['id']] = issues
    print(json.dumps(flags, ensure_ascii=False, indent=2))
    print('Questi sono indicatori di formato; nessuna verifica automatica dei fatti.')


def preview(args):
    root = Path(args.run_dir)
    paths = sorted((root / 'candidates').glob('*.json'))
    if not paths:
        raise ValueError('Nessun candidato disponibile; esegui generate.')
    for path in paths:
        row = read(path)
        print('\n===== ' + row['id'] + ' =====\n' + row['answer'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['generate', 'review', 'export', 'status', 'audit', 'preview'])
    parser.add_argument('--spec', default='data/splits/pilot_spec_v1.json')
    parser.add_argument('--run-dir', default='results/dpo_pilot_v2')
    parser.add_argument('--model', default='qwen2.5:7b')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--reviewer')
    parser.add_argument('--review-kind', choices=['human', 'ai_assisted'])
    args = parser.parse_args()
    if args.command == 'review' and (not args.reviewer or not args.reviewer.strip() or not args.review_kind):
        parser.error('review richiede --reviewer e --review-kind human oppure ai_assisted')
    if args.limit is not None and args.limit < 1:
        parser.error('--limit deve essere positivo')
    if args.command == 'status':
        summary(Path(args.run_dir), pairs(Path(args.run_dir)))
    else:
        globals()[args.command](args)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nInterrotto. I risultati gia salvati restano disponibili.', file=sys.stderr)
        sys.exit(130)
