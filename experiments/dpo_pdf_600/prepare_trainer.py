"""Derive a standalone trainer from the already used project trainer."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = Path(r'C:\Users\matti\Documents\astroTutor\scripts\train_dpo_pilot.py').read_text(encoding='utf-8')
start = source.index('def load_data(')
end = source.index('\ndef environment():', start)
loader = '''def load_data(directory):
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

'''
source = source[:start] + loader + source[end:]
changes = {
 "Eseguire dalla root del progetto: check -> smoke -> train.": "Dataset sintetico PDF: check -> smoke -> train. Nessun test finale incluso.",
 "parser.add_argument('--data-dir', default='results/dpo_pilot_curated_v1/export')": "parser.add_argument('--data-dir', default=str(Path(__file__).resolve().parent / 'dataset_consegna'))\n    parser.add_argument('--model', default=BASE)",
 "args = parser.parse_args()": "args = parser.parse_args()\n    model_id = args.model",
 "out = Path(args.output_dir or ('models/pilot_dpo_' + args.mode + '_v1'))": "out = Path(args.output_dir or (Path(__file__).resolve().parent / 'runs' / (model_id.replace('/', '__') + '_' + args.mode + '_v1')))",
 "model_info(BASE, revision=": "model_info(model_id, revision=",
 "AutoTokenizer.from_pretrained(BASE,": "AutoTokenizer.from_pretrained(model_id,",
 "AutoModelForCausalLM.from_pretrained(BASE,": "AutoModelForCausalLM.from_pretrained(model_id,",
 "{'model': BASE,": "{'model': model_id,",
 "eval_dataset=Dataset.from_list(prepared['validation']), processing_class=tokenizer,": "processing_class=tokenizer,",
 "initial = trainer.evaluate(metric_key_prefix='before')": "initial = {'available': False, 'reason': 'No held-out validation supplied'}",
 "final = trainer.evaluate(metric_key_prefix='after')": "final = {'available': False, 'reason': 'No held-out validation supplied'}",
 "'note': 'Solo pilota tecnico. 8 domande, 4 gruppi fonte; giudizi assistiti da IA. '\n         'La validation non e un test finale e le coppie non sono indipendenti.'": "'note': '600 confronti sintetici, 75 domande, 300 prompt. Nessuna validation o test. '\n         'Obiettivo correttezza e pertinenza; nessuna revisione umana indipendente.'",
 "print('Caricamento Qwen 3B da Hugging Face; il primo download occupa diversi GB.', flush=True)": "print('Caricamento modello:', model_id, flush=True)",
 "print('CHECK OK: import, CUDA e forward/backward NF4. Nessun modello scaricato.')": "print('CHECK OK: dataset, import, CUDA e forward/backward NF4. Nessun modello scaricato.')",
 "smoke = args.mode == 'smoke'": "smoke = args.mode == 'smoke'\n    if smoke:\n        # Eight diverse question/level prompts, both negative types: only a technical check.\n        prepared['train'] = [prepared['train'][q*8+l*2+n] for q,l in [(0,0),(3,1),(6,2),(9,3),(12,0),(15,1),(18,2),(21,3)] for n in (0,1)]\n    data_report['rows_used_this_run'] = len(prepared['train'])",
}
for old, new in changes.items():
    assert old in source, old
    source = source.replace(old,new)
compile(source,'train_dpo_600.py','exec')
(ROOT/'train_dpo_600.py').write_text(source,encoding='utf-8')
print('Creato:', ROOT/'train_dpo_600.py')
