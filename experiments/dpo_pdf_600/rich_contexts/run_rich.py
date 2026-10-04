"""Bounded diagnostic using locally selected core and optional evidence."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'facts_first'))
import pipeline_facts as f
core=f.core


def hashes():
    paths=[Path(__file__),ROOT/'selected_pack.json',Path(f.__file__),Path(f.transport.__file__),Path(core.__file__)]
    return {str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def answer_prompt(row,level):
    return ('Rispondi alla domanda in italiano per il profilo. Mantieni tutti i fatti del NUCLEO. '
      'Gli altri fatti sono FACOLTATIVI: scegli solo quelli utili al profilo. Non devi inserire tutti i dettagli. '
      'Puoi cambiare struttura, definire termini o spiegare passaggi solo usando le informazioni elencate. '
      'Non aggiungere cause, formule, analogie o conoscenze esterne. Non omettere condizioni o limiti del nucleo. '
      'Non scrivere una risposta deliberatamente difettosa. Non citare ID, istruzioni o livello scolastico. '
      'Massimo 180 parole. JSON: {"sentences":[{"text":"frase della risposta","fact_ids":[1]}]}. '
      'Ogni frase indica gli ID che la sostengono.\nPROFILO: '+core.LEVELS[level]
      +'\nDOMANDA: '+row['question']+'\nNUCLEO (ID obbligatori): '+json.dumps(row['core_fact_ids'])
      +'\nFATTI ORIGINALI DISPONIBILI:\n'+json.dumps(row['facts'],ensure_ascii=False))


def answer_check(raw,row):
    sentences=raw.get('sentences')
    if not isinstance(sentences,list):raise ValueError('invalid_sentences')
    used=set()
    for s in sentences:
        if not isinstance(s,dict) or not isinstance(s.get('fact_ids'),list):raise ValueError('invalid_fact_ids')
        for i in s['fact_ids']:
            if type(i) is not int:raise ValueError('invalid_fact_ids')
            used.add(i)
    valid={x['id'] for x in row['facts']}
    if not used<=valid:raise ValueError('unknown_fact')
    if not set(row['core_fact_ids'])<=used:raise ValueError('missing_core_fact')
    return f.resolve_answer(raw,{'facts':[x for x in row['facts'] if x['id'] in used]})


def audit_prompt(row,answers):
    prompt=f.audit_prompt(row,{'question':row['question'],'facts':row['facts']},answers)
    prompt=prompt.replace('entrambe esprimano tutti i fatti selezionati','entrambe esprimano tutti i fatti del NUCLEO')
    prompt=prompt.replace('qui vogliamo isolare la spiegazione mantenendo il contenuto',
      'qui il nucleo e obbligatorio, gli approfondimenti sono facoltativi e possono differire')
    prompt=prompt.replace('all_facts_preserved','core_preserved')
    return prompt+'\nNUCLEO OBBLIGATORIO: '+json.dumps(row['core_fact_ids'])+(
        '\nOmettere fatti facoltativi non e un errore. Inserirne di piu non rende automaticamente migliore '
        'una risposta. Valuta definizioni utili, prerequisiti e profondita; una sola diversa divisione '
        'in frasi non basta per una preferenza sostanziale. Rifiuta meccanismi non sostenuti dalla fonte.')


def decide(judge,answers,order):
    adapted=copy.deepcopy(judge)
    for report in adapted.get('answers',[]):
        if isinstance(report,dict):report['all_facts_preserved']=report.get('core_preserved')
    return f.decision(adapted,answers,order)


def run(client=None):
    plan=core.read(ROOT/'plan.json')
    if plan['hashes']!=hashes():raise ValueError('Piano o codice cambiato.')
    rows=core.read(ROOT/'selected_pack.json')
    if client is None:
        if not os.environ.get('ORACLE_API_KEY','').strip():raise ValueError('Chiave assente.')
        f.transport.ROOT=ROOT;f.transport.MAX_REQUESTS=30
        client=f.Client();core.http=client.http
    done={x['id'] for x in core.lines(ROOT/'results.jsonl')}
    for row in rows:
        if row['id'] in done:continue
        state={};seed=int(row['id'][:8],16)%2147483647
        try:
            answers=[];state['answers']=answers
            for offset,level in enumerate([row['level'],row['alternate_level']]):
                raw=client.chat(SimpleNamespace(model=f.AUTHOR),answer_prompt(row,level),seed+offset)
                answers.append(answer_check(raw,row))
            if core.normalized(answers[0]['text'])==core.normalized(answers[1]['text']):raise ValueError('identical_answers')
            order=[0,1];random.Random(seed).shuffle(order);state['order']=order
            displayed=[answers[i] for i in order]
            judge=client.chat(SimpleNamespace(model=f.JUDGE),audit_prompt(row,displayed),seed+2)
            state['judge']=judge;state['chosen_index']=decide(judge,displayed,order);status='auto_accepted'
        except ValueError as exc:status=str(exc)
        core.append(ROOT/'results.jsonl',dict(id=row['id'],level=row['level'],status=status,state=state))
        print(row['id'],status,flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','run','summary']);args=parser.parse_args()
    f.ROOT=ROOT
    if args.mode=='prepare':
        if (ROOT/'plan.json').exists():raise ValueError('Piano gia presente.')
        core.write(ROOT/'plan.json',dict(hashes=hashes(),max_requests=30,planned=5,author=f.AUTHOR,judge=f.JUDGE))
        print('Piano preparato, nessuna API.');return
    if args.mode=='summary':return f.summary()
    lock=ROOT/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:run()
    except Exception as exc:
        print('STOP:',str(exc),flush=True);raise SystemExit(2)
    finally:
        try:f.summary()
        finally:lock.unlink(missing_ok=True)


if __name__=='__main__':main()
