"""Offline reproducible export. No API calls. Run: python build.py"""
import hashlib
import json
import re
from pathlib import Path
from collections import Counter
from content import UNITS

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / 'dataset_v5'
LEVELS = {
 'A': 'Scuola primaria, 6-10 anni: usa parole comuni, spiega i concetti necessari senza infantilizzare.',
 'B': 'Scuola secondaria di primo grado: conoscenze scientifiche elementari; spiega il meccanismo e i termini nuovi.',
 'C': 'Scuola secondaria di secondo grado: basi di fisica; esplicita i passaggi causali e usa termini tecnici pertinenti.',
 'D': 'Università: basi di fisica e astronomia; usa terminologia precisa, relazioni causali e limiti delle affermazioni.'
}
SYSTEM = ('Sei AstroTutor. Rispondi in italiano alla domanda dello studente, adattando la spiegazione al profilo indicato. '
          'Usa il contesto fornito e non inventare informazioni. Se non basta, dichiara il limite. '
          'Rispondi direttamente, senza aggiungere quiz o piani di studio non richiesti.')

def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def save_json(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def save_lines(name, values):
    (ROOT / name).write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in values), encoding='utf-8')

def answer(item, level):
    if level == 'A': return item['simple']
    if level == 'B': return item['simple']+' '+item['explanation']
    if level == 'C': return item['precise']+' '+item['explanation']
    return item['precise']

def extract(row, anchors):
    text = row['context']
    bounds = [0]+[m.end() for m in re.finditer(r'(?<=[.!?])\s+(?=[A-ZÀ-Ö“])', text)]+[len(text)]
    spans = set()
    for anchor in anchors:
        pos = text.index(anchor)
        start = max(b for b in bounds if b <= pos)
        end = min(b for b in bounds if b >= pos+len(anchor))
        while start < end and text[start].isspace(): start += 1
        while end > start and text[end-1].isspace(): end -= 1
        spans.add((start,end))
    evidence = [{'start':s,'end':e,'text':text[s:e]} for s,e in sorted(spans)]
    return '\n\n'.join(x['text'] for x in evidence), evidence

def main():
    snapshot = ROOT / 'source_snapshot.json'
    if snapshot.exists():
        frozen = json.loads(snapshot.read_text(encoding='utf-8'))
        sources = frozen['sources']
        reserved = set(frozen['reserved_source_groups'])
    else:
        rows = json.loads((INPUT/'contexts_train.json').read_text(encoding='utf-8'))
        by_id = {r['id']:r for r in rows}
        sources = [by_id[u['source_id']] for u in UNITS]
        reserved = set()
        for split in ('development','test'):
            reserved.update(r['source_group'] for r in json.loads((INPUT/f'contexts_{split}.json').read_text(encoding='utf-8')))
        save_json('source_snapshot.json', {'sources':sources,'reserved_source_groups':sorted(reserved)})
    by_id = {r['id']:r for r in sources}
    assert not ({r['source_group'] for r in sources} & reserved), 'Source leakage'
    dpo, sft, metadata, questions, contexts = [], [], [], [], []
    for ui, unit in enumerate(UNITS):
        row = by_id[unit['source_id']]
        context, evidence = extract(row,unit['anchors'])
        assert all(row['context'][e['start']:e['end']] == e['text'] for e in evidence)
        contexts.append({'source_id':row['id'], 'topic':unit['topic'], 'source_file':row['source_file'],
                         'source_group':row['source_group'], 'chunk_file':row['chunk_file'],
                         'chunk_line':row['chunk_line'], 'context':context, 'evidence':evidence})
        for qi, item in enumerate(unit['items']):
            family = f'q{ui*3+qi+1:03}'
            questions.append({'question_id':family,'topic':unit['topic'],'source_id':row['id'],**item})
            for level, profile in LEVELS.items():
                prompt = [{'role':'system','content':SYSTEM}, {'role':'user','content':
                    f'Profilo: {profile}\n\nContesto:\n{context}\n\nDomanda: {item["question"]}'}]
                chosen = answer(item,level)
                sft.append({'messages':prompt+[{'role':'assistant','content':chosen}]})
                other_unit = UNITS[(ui+7)%len(UNITS)]
                other_item = other_unit['items'][qi]
                for category, rejected in [('factual_contradiction',item['wrong']),
                                            ('off_question',answer(other_item,level))]:
                    assert chosen != rejected
                    pair_id = f'{family}_{level}_{category}'
                    dpo.append({'prompt':prompt,'chosen':[{'role':'assistant','content':chosen}],
                                'rejected':[{'role':'assistant','content':rejected}]})
                    metadata.append({'row_1based':len(dpo),'pair_id':pair_id,'question_id':family,
                         'level':level,'category':category,'topic':unit['topic'],
                         'source_id':row['id'],'source_group':row['source_group'],
                         'source_file':row['source_file'],'context_sha256':digest(context),
                         'split':'train','author':'AI assistant','human_validated':False,
                         'negative_source_id':other_unit['source_id'] if category=='off_question' else row['id'],
                         'negative_answers_question':other_item['question'] if category=='off_question' else None,
                         'preference_reason': ('La risposta rifiutata contiene una contraddizione fattuale intenzionale.'
                           if category=='factual_contradiction' else 'La risposta rifiutata risponde a una domanda di un altro argomento.'),
                         'pair_sha256':digest(json.dumps(dpo[-1],ensure_ascii=False,sort_keys=True))})
    assert len(dpo)==600 and len(sft)==300 and len(questions)==75
    assert len({m['pair_sha256'] for m in metadata})==600
    assert len({q['question'] for q in questions})==75
    save_lines('train_dpo.jsonl',dpo)
    save_lines('train_sft.jsonl',sft)
    save_lines('provenance.jsonl',metadata)
    save_json('questions.json',questions)
    save_json('contexts.json',contexts)
    report={'structural_checks_passed':True,'pairs':len(dpo),'unique_questions':75,
            'unique_question_level_prompts':300,'concept_blocks':25,
            'by_level':dict(Counter(m['level'] for m in metadata)),
            'by_category':dict(Counter(m['category'] for m in metadata)),
            'source_groups_used':sorted({r['source_group'] for r in sources}),
            'reserved_source_overlap':False,'evidence_exact_substrings':True,
            'human_validated':False,'independent_semantic_validation':False,
            'average_response_words':{kind:round(sum(len(r[kind][0]['content'].split()) for r in dpo)/600,2)
                                      for kind in ('chosen','rejected')}}
    save_json('validation_report.json',report)
    review=['# Domande e risposte di riferimento','',
            '75 domande. Le risposte seguenti sono quelle accessibili; il JSON contiene anche le varianti e gli errori intenzionali.','']
    for q in questions:
        review += [f'## {q["question_id"]} — {q["topic"]}', '',q['question'],'',q['simple'], '',
                   f'Fonte: `{q["source_id"]}` (vedere contexts.json).','']
    (ROOT/'LEGGIMI_DOMANDE.md').write_text('\n'.join(review),encoding='utf-8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
            if p.is_file() and p.name!='manifest.json'}
    save_json('manifest.json',{'version':'assistant_pdf_600_v1','created':'2026-09-26',
         'generation':'Offline, assistant-authored; no API calls',
         'purpose':'Controlled synthetic DPO training: factual correctness and relevance',
         'test_set_included':False,'counts':{'dpo':600,'sft':300,'questions':75},'sha256':hashes})
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
