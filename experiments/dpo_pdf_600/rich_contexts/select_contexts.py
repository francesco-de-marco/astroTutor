"""Local reproducible selection. Heuristic scores are not scientific validation."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'dataset_v5/contexts_train.json'
DEFINITION=r'\b(?:cioè|ossia|si chiama|si chiamano|significa|chiamat[oaie]|definit[oaie]|called|defined|refers to|known as|means)\b'
CAUSE=r'\b(?:perché|poiché|quindi|provoca|produce|causa|dipende|conseguenza|because|therefore|causes?|due to|as a result|leads to|results? in)\b'
ASTRONOMY=r'\b(?:stell[ae]|galassi[ae]|pianet[ai]|Sole|Luna|eclissi|buco nero|buchi neri|stars?|galax(?:y|ies)|planets?|Sun|Moon|eclipse|black holes?|nebula|supernova|pulsar|comet[ae]?)\b'


def analyze(text):
    words=re.findall(r'\b\w+\b',text)
    if not 1000<=len(text)<=3600:return None
    if not text.strip()[0].isupper() or text.rstrip()[-1] not in '.!?':return None
    if '$' in text or '\\' in text or '\ufffd' in text:return None
    if not words or sum(len(w)==1 for w in words)/len(words)>.10:return None
    if re.search(r'https?://|www\.|copyright|bibliograph|references|author of|lives with|Figure \d|Figura \d',text,re.I):return None
    if len(re.findall(r'\b(?:19|20)\d\d\b',text))>2:return None
    defs=list(re.finditer(DEFINITION,text,re.I));causes=list(re.finditer(CAUSE,text,re.I));astro=list(re.finditer(ASTRONOMY,text,re.I))
    if not defs or not causes or len(astro)<2:return None
    def snippets(matches):
        return [text[max(0,m.start()-65):min(len(text),m.end()+100)] for m in matches[:3]]
    return dict(score=3*min(len(defs),3)+3*min(len(causes),3)+min(len(astro),5),
                definition_indicators=snippets(defs),causal_indicators=snippets(causes))


def main():
    rows=json.loads(SOURCE.read_text(encoding='utf-8'));seen=set()
    for pattern in ('dataset_v*/attempts_train.jsonl','automatico/attempts.jsonl','facts_first/results.jsonl'):
        for path in ROOT.parent.glob(pattern):
            seen.update(json.loads(line)['id'] for line in path.read_text(encoding='utf-8').splitlines() if line.strip())
    seen.update(r['id'] for r in json.loads((ROOT.parent/'revisione_locale/contesti_5.json').read_text(encoding='utf-8')))
    candidates=[]
    for row in rows:
        if row['id'] in seen:continue
        quality=analyze(row['context'])
        if quality:candidates.append(dict(source=row,heuristics=quality))
    candidates.sort(key=lambda r:(-r['heuristics']['score'],r['source']['id']))
    # Round-robin document topics; cap each book, retain source-level metadata.
    groups=defaultdict(list)
    for row in candidates:groups[row['source']['topic']].append(row)
    chosen=[];books=Counter();used=set()
    while len(chosen)<12:
        progress=False
        for topic in sorted(groups):
            row=next((r for r in groups[topic] if r['source']['id'] not in used and books[r['source']['source_group']]<4),None)
            if row:
                chosen.append(row);used.add(row['source']['id']);books[row['source']['source_group']]+=1;progress=True
                if len(chosen)==12:break
        if not progress:break
    output=dict(input_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        candidates=len(candidates),selected=len(chosen),rows=chosen,
        status='heuristically_selected_not_validated',new_api_calls=0)
    (ROOT/'selection.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# Contesti con definizioni e passaggi causali','Selezione locale da TRAIN. Gli indicatori lessicali non garantiscono completezza, correttezza o adeguatezza al livello. Nessuna generazione API avviata.']
    for i,row in enumerate(chosen,1):
        r=row['source'];md.extend([f"## {i}. {r['source_title']} — topic {r['topic']}",
          f"ID {r['id']}; livello documento {r['source_level']}; chunk {r['chunk_file']}, riga {r['chunk_line']}.",r['context']])
    (ROOT/'CONTESTI.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(candidates=len(candidates),selected=len(chosen),topics=dict(Counter(x['source']['topic'] for x in chosen)),books=dict(books)),ensure_ascii=False))


if __name__=='__main__':main()
