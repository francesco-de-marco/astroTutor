"""Confronto diagnostico delle penalita; eseguire dalla root di astroTutor.

python scripts/run_dev.py freeze
python scripts/run_dev.py generate
Nessun training e nessun giudice automatico. Una sola esecuzione per cartella.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from urllib.request import urlopen
import uuid

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
SETTINGS = {
    'original': {'frequency_penalty': 0.6, 'presence_penalty': 0.5},
    'zero': {'frequency_penalty': 0.0, 'presence_penalty': 0.0},
}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def hashed(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def save(path, value):
    path = Path(path)
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(text, encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def code_hash(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def packages(names):
    return {name: importlib.metadata.version(name) for name in names}


def check_manifest(path, value):
    if path.exists():
        if read(path) != value:
            raise ValueError('Input, codice o configurazione cambiati: usa --run-dir con un nuovo nome.')
    else:
        if path.parent.exists() and any(path.parent.iterdir()):
            raise ValueError(f'Cartella non vuota senza manifest: {path.parent}')
        save(path, value)


def questions(path):
    rows = read(path)
    if not isinstance(rows, list) or not rows:
        raise ValueError('Lista di domande vuota o non valida.')
    identifiers, inputs = set(), set()
    for row in rows:
        if row.get('level') not in ('A', 'B', 'C', 'D'):
            raise ValueError('Livello non valido.')
        if not isinstance(row.get('question'), str) or not row['question'].strip():
            raise ValueError('Domanda vuota.')
        identifier = row.get('item_id')
        if not isinstance(identifier, str) or not identifier:
            raise ValueError('item_id mancante.')
        key = (' '.join(row['question'].casefold().split()), row['level'])
        if identifier in identifiers or key in inputs:
            raise ValueError('Domanda/livello o item_id duplicato.')
        if not row.get('group_id'):
            raise ValueError('group_id mancante.')
        identifiers.add(identifier)
        inputs.add(key)
    return rows


def context_path(directory, item):
    return directory / 'items' / (hashed(item) + '.json')


def freeze(args):
    rows = questions(args.questions)
    directory = Path(args.run_dir) / 'contexts'
    manifest = {
        'schema': 1, 'items': rows, 'query_expansion': False,
        'initial_k': 15, 'final_k': 3,
        'retrieval_source_hash': code_hash('src/retrieval.py'),
        'packages': packages(['chromadb', 'sentence-transformers', 'transformers', 'torch']),
        'note': 'Corpus e indice devono restare invariati durante questa fase.',
    }
    check_manifest(directory / 'manifest.json', manifest)
    missing = [row for row in rows if not context_path(directory, row).exists()]
    if not missing:
        load_contexts(args.run_dir)
        print(f'Contesti gia completi: {len(rows)}. Puoi passare a generate.')
        return
    if not (ROOT / 'data/vector_db/chroma.sqlite3').exists():
        raise FileNotFoundError('Database Chroma non trovato.')
    from src.retrieval import AdvancedRetriever
    retriever = AdvancedRetriever()
    for row in missing:
        docs = retriever.search([row['question']], user_level=row['level'], initial_k=15, final_k=3)
        if not docs:
            raise RuntimeError(f'Nessun contesto per {row["item_id"]}: controlla prima di proseguire.')
        record = {'item': row, 'docs': docs, 'queries': [row['question']]}
        save(context_path(directory, row), record)
        print(f'Contesto salvato: {row["item_id"]} ({len(docs)} chunk)', flush=True)
    load_contexts(args.run_dir)
    print(f'Contesti completi: {len(rows)}. Attendi la chiusura del processo, poi esegui generate.')


def load_contexts(run_dir):
    directory = Path(run_dir) / 'contexts'
    manifest = read(directory / 'manifest.json')
    records = []
    for item in manifest['items']:
        path = context_path(directory, item)
        if not path.exists():
            raise ValueError('Contesti incompleti: rilancia freeze.')
        record = read(path)
        if record['item'] != item or not isinstance(record['docs'], list) or not record['docs']:
            raise ValueError(f'Contesto non valido: {path}')
        for doc in record['docs']:
            if not isinstance(doc.get('text'), str) or not isinstance(doc.get('title'), str):
                raise ValueError(f'Testo o titolo del chunk non valido: {path}')
        records.append(record)
    return records


def model_identity(args):
    with urlopen(args.ollama_url.rstrip('/') + '/api/tags', timeout=20) as response:
        entries = json.load(response)['models']
    for entry in entries:
        if entry.get('name') == args.model or entry.get('model') == args.model:
            return {'name': args.model, 'digest': entry['digest'], 'details': entry.get('details')}
    raise ValueError(f'Modello assente: esegui ollama pull {args.model}')


def generate(args):
    records = load_contexts(args.run_dir)
    identity = model_identity(args)
    directory = Path(args.run_dir) / 'generation'
    manifest = {
        'schema': 1, 'model': identity, 'ollama_url': args.ollama_url,
        'contexts_hash': hashed(records), 'settings': SETTINGS,
        'temperature': 0.0, 'seed': 42, 'guardrails_enabled': False,
        'code': {name: code_hash(name) for name in ['src/generation.py', 'src/alignment.py']},
        'packages': packages(['openai']),
        'script_hash': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    check_manifest(directory / 'manifest.json', manifest)
    from src.generation import RAGGenerator
    rag = RAGGenerator(model_name=args.model, guardrails_enabled=False,
                       temperature=0.0, seed=42, base_url=args.ollama_url.rstrip('/') + '/v1')
    completed, total = 0, len(records) * len(SETTINGS)
    for position, context in enumerate(records):
        # Alterna l'ordine dei due bracci per limitare effetti legati all'ordine.
        order = list(SETTINGS) if position % 2 == 0 else list(reversed(SETTINGS))
        for name in order:
            key = hashed([manifest, context['item'], name])
            path = directory / name / (key + '.json')
            if path.exists():
                if read(path).get('run_key') != key:
                    raise ValueError('Record salvato non coerente.')
                completed += 1
                print(f'Gia salvata {completed}/{total}', flush=True)
                continue
            rag.generation_config.update(SETTINGS[name])
            row = context['item']
            record = rag.generate_record(row['question'], row['level'], docs=context['docs'])
            record.update(run_key=key, item_id=row['item_id'], group_id=row['group_id'],
                          experiment_setting=name, model_identity=identity, split='development')
            save(path, record)
            completed += 1
            print(f'Salvata {completed}/{total}: {row["item_id"]} / {name}', flush=True)
    if model_identity(args) != identity:
        raise RuntimeError('Il modello e cambiato durante la run: i risultati non sono confrontabili.')
    print(f'Generazione completata: {completed}/{total}. Risposte in {directory}')
    print('Nessun giudizio automatico calcolato: la qualita deve ancora essere valutata.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=['freeze', 'generate'])
    p.add_argument('--questions', default='data/splits/questions_dev_v1.json')
    p.add_argument('--run-dir', default='results/dev_penalties_v1')
    p.add_argument('--model', default='qwen2.5:3b')
    p.add_argument('--ollama-url', default='http://localhost:11434')
    args = p.parse_args()
    if not (ROOT / 'src/generation.py').exists():
        p.error('Esegui il comando dalla root del progetto astroTutor.')
    if args.phase == 'freeze':
        freeze(args)
    else:
        generate(args)


if __name__ == '__main__':
    main()
