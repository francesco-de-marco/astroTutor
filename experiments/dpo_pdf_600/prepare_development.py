"""Freeze eight new development questions and prepare a resumable comparison."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dataset_builder',ROOT/'dataset_consegna'/'build.py')
import sys
sys.path.insert(0,str(ROOT/'dataset_consegna'))
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

SPECS=[
 ('ada419f70f344d53f554aca2',None,None,[
  ('Due gemelli percorrono strade diverse nello spaziotempo e poi si ritrovano: devono aver vissuto necessariamente lo stesso tempo?',
   'No. Tra gli stessi eventi, percorsi diversi possono accumulare tempi propri diversi. Non serve attribuire un malfunzionamento agli orologi.'),
  ('Viaggiare vicino a un buco nero permette di vivere cento anni sul proprio orologio senza invecchiare di cento anni?',
   'No. Il tempo vissuto e l’invecchiamento coincidono con il tempo proprio indicato dall’orologio personale. Differenze rispetto ad altri osservatori non annullano questo fatto.')]),
 ('946fe370173f22b33ac196fe','If two stones initially','The second answer',[
  ('Due pietre inizialmente ferme sono a distanze diverse dal centro della Terra: perché non cadono con la stessa accelerazione?',
   'Quella più vicina al centro subisce un’accelerazione maggiore. Si tratta di una differenza dell’attrazione gravitazionale da punto a punto, non di una diversa massa delle pietre.'),
  ('Perché estendere troppo una regione in caduta libera può impedire di trattarla come un sistema inerziale?',
   'Le accelerazioni di marea variano tra punti della regione. Se sono rilevabili alla precisione dell’esperimento, l’approssimazione di sistema inerziale locale non è sufficiente.')]),
 ('bbf282b6e7297f9fc9721af5',None,None,[
  ('In relatività generale, che cosa si intende per un sistema di riferimento inerziale locale?',
   'Un sistema che segue la caduta libera in una regione sufficientemente piccola dello spaziotempo. Locale non significa estendibile senza limiti a tutto lo spazio e il tempo.'),
  ('Un sistema inerziale costruito in una piccola regione può essere esteso automaticamente a tutto lo spaziotempo?',
   'No. Il brano rinuncia a un’unica estensione globale dei riferimenti inerziali: sistemi locali lontani non sono automaticamente lo stesso riferimento.')]),
 ('a8b069b00535cfb8a6ddfd23','Una delle equazioni',None,[
  ('Quale relazione tra massa ed energia esprime l’equazione E = mc² citata nel brano?',
   'Esprime l’equivalenza fra massa ed energia: l’energia corrispondente è la massa moltiplicata per il quadrato della velocità della luce. Non è una somma.'),
  ('Nell’equazione E = mc², la lettera c indica la velocità di una stella?',
   'No. Indica la velocità della luce, descritta come una costante, non la velocità della stella o la massa.')]),
]

def sha(data):return hashlib.sha256(data).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 rows=json.loads((ROOT/'dataset_v5'/'contexts_development.json').read_text(encoding='utf-8'))
 lookup={r['id']:r for r in rows}
 train_meta=[json.loads(s) for s in (ROOT/'dataset_consegna'/'provenance.jsonl').read_text(encoding='utf-8').splitlines()]
 train_groups={r['source_group'] for r in train_meta}
 prompts=[];sources=[];qid=0
 for source_id,start_marker,end_marker,questions in SPECS:
  r=lookup[source_id]
  assert r['source_group'] not in train_groups
  text=r['context']; start=text.index(start_marker) if start_marker else 0
  end=text.index(end_marker,start) if end_marker else len(text)
  while end>start and text[end-1].isspace():end-=1
  context=text[start:end]
  sources.append({'source_id':source_id,'source_file':r['source_file'],'source_group':r['source_group'],
   'chunk_file':r['chunk_file'],'chunk_line':r['chunk_line'],'start':start,'end':end,
   'source_context':text,'selected_context':context})
  for question,reference in questions:
   qid+=1
   for level,profile in builder.LEVELS.items():
    prompts.append({'id':f'dev{qid:02}_{level}','question_id':f'dev{qid:02}',
     'question':question,'level':level,'group':r['source_group'],'source_id':source_id,
     'reference_points':reference,
     'messages':[{'role':'system','content':builder.SYSTEM},{'role':'user','content':
       f'Profilo: {profile}\n\nContesto:\n{context}\n\nDomanda: {question}'}]})
 payload={'split':'development','human_validated':False,'unique_questions':8,
  'note':'Primo controllo di sviluppo, 8 domande da 4 brani e 3 documenti riservati. Non è il test finale. Temi prevalentemente relativistici; non rappresenta tutto il dominio.',
  'sources':sources,'prompts':prompts}
 out=ROOT/'development_600_v1.json'
 if out.exists():
  assert json.loads(out.read_text(encoding='utf-8'))==payload,'Set già esistente differente: non sovrascrivere.'
 else:dump(out,payload)
 source=Path(r'C:\Users\matti\Documents\astroTutor\scripts\compare_dpo_pilot.py').read_text(encoding='utf-8')
 start=source.index('def inputs(');end=source.index('\ndef render(',start)
 loader='''def inputs(source, training):
    dataset = read(source)
    if dataset['split'] != 'development':
        raise ValueError('Atteso sviluppo, non test finale.')
    train_dir = Path(training['dataset_path'])
    train = [json.loads(x) for x in (train_dir/'train_dpo.jsonl').read_text(encoding='utf-8').splitlines()]
    if hashed(train) != training['data']['hashes']['train']:
        raise ValueError('Dataset training modificato.')
    metadata = [json.loads(x) for x in (train_dir/'provenance.jsonl').read_text(encoding='utf-8').splitlines()]
    groups = {m['source_group'] for m in metadata}
    train_prompts = {hashed(r['prompt']) for r in train}
    rows = dataset['prompts']
    for row in rows:
        if row['group'] in groups or hashed(row['messages']) in train_prompts:
            raise ValueError('Contaminazione train/development.')
    if len(rows)!=32 or len({r['question_id'] for r in rows})!=8:
        raise ValueError('Conteggi sviluppo inattesi.')
    return rows

'''
 source=source[:start]+loader+source[end:]
 replacements={
  'Confronto diagnostico NF4 base/LoRA sugli 8 prompt del gruppo validation.':'Confronto di sviluppo NF4 base/LoRA: 32 prompt, 8 nuove domande.',
  "'Otto prompt: due domande per quattro livelli, un solo gruppo di fonte. '":"'Trentadue prompt: otto domande per quattro livelli da tre documenti di sviluppo. '",
  "'Non sono otto osservazioni indipendenti e non costituiscono un test finale.'":"'Le varianti di livello non sono osservazioni indipendenti. Non è il test finale.'",
  "default='models/pilot_dpo_train_v1'":"default=str(Path(__file__).resolve().parent/'runs'/'Qwen__Qwen2.5-3B-Instruct_train_v1')",
  "default='results/dpo_pilot_curated_v1'":"default=str(Path(__file__).resolve().parent/'development_600_v1.json')",
  "default='results/pilot_dpo_comparison_v1'":"default=str(Path(__file__).resolve().parent/'evaluation'/'qwen3b_development_v1')",
  "training = read(train_root / 'run_manifest.json')":"training = read(train_root / 'run_manifest.json')\n    training['dataset_path'] = str(Path(__file__).resolve().parent/'dataset_consegna')",
  "'adapter_hashes':":"'source_file_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),\n        'adapter_hashes':",
 }
 for old,new in replacements.items():
  assert old in source,old
  source=source.replace(old,new)
 compile(source,'compare_dpo_600.py','exec')
 (ROOT/'compare_dpo_600.py').write_text(source,encoding='utf-8')
 dump(ROOT/'development_600_v1_manifest.json',{'sha256':sha(out.read_bytes()),'questions':8,'prompts':32,'generations':64,
  'source_groups':sorted({p['group'] for p in prompts}),'frozen_before_generation':True,'test_final_used':False})
 print('Creati set sviluppo e compare_dpo_600.py; 32 prompt, 64 generazioni.')

if __name__=='__main__':main()
