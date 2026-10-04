"""Prepare an editable HTML companion and a lightweight delivery bundle."""
from pathlib import Path
import re,shutil,json,zipfile,html
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'relazione_finale'
lines=(OUT/'Relazione_contenuto.md').read_text(encoding='utf8').splitlines()
parts=[];rows=[]
def flush():
    if rows:
        parts.append('<table>'+''.join('<tr>'+''.join(f'<{"th" if i==0 else "td"}>{v}</{"th" if i==0 else "td"}>' for v in row.split(' | '))+'</tr>' for i,row in enumerate(rows))+'</table>');rows.clear()
for line in lines:
    if not line.strip():flush();continue
    if ' | ' in line and not line.startswith('!['):rows.append(line);continue
    flush()
    if line.startswith('# '):parts.append('<h1>'+line[2:]+'</h1>')
    elif line.startswith('!['):
        src=Path(line.rsplit('](',1)[1][:-1]);assets=OUT/'figure';assets.mkdir(exist_ok=True)
        shutil.copyfile(src,assets/src.name);parts.append(f'<img src="figure/{src.name}" alt="Grafico sperimentale">')
    elif re.match(r'^\d+\. ',line):parts.append('<h2>'+line+'</h2>')
    else:parts.append('<p>'+line+'</p>')
flush()
page='''<!doctype html><html lang="it"><meta charset="utf-8"><title>AstroTutor — Relazione finale</title>
<style>body{max-width:850px;margin:40px auto;padding:0 24px;color:#24384b;font:16px/1.5 Arial,sans-serif}h1{font-size:26px;margin-top:45px}h2{font-size:19px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;text-align:left;border-bottom:1px solid #d7e1e8}th{background:#e9f1f5}img{width:100%;height:auto} @media print{body{margin:0}h1{page-break-before:always}h1:first-child{page-break-before:avoid}table,img{break-inside:avoid}}</style>
<body>'''+''.join(parts)+'</body></html>'
(OUT/'AstroTutor_relazione_modificabile.html').write_text(page,encoding='utf8')
(OUT/'LEGGIMI.txt').write_text('Relazione finale di sei pagine. Il PDF è la versione impaginata per la consegna.\nLa versione HTML e il testo Markdown sono modificabili e contengono lo stesso testo.\nAutori, insegnamento e docente non sono stati inventati; possono essere aggiunti prima della consegna.\nI risultati provengono dalla campagna finale salvata.\nL’interfaccia è una demo locale separata: leggere streamlit_app/README.md.\nLo ZIP non include pesi, database o l’intero repository; accompagna il progetto esistente.\n',encoding='utf8')
qa={'status':'passed','date':'2026-10-03','ui':'Streamlit 1.64.0; initial page and all six result rows',
    'backend_live':'Qwen2.5 3B, level B, two retrieved documents; base and DPO actual inference',
    'ui_interaction_test':'AppTest with saved actual record: comparison, sources, download control, clear conversation',
    'scope':'No extensive end-to-end testing of the other five UI models; no new scientific evaluation.',
    'environment_note':'Python 3.14 AppTest temporary-directory cleanup reports a sandbox PermissionError after successful assertions.'}
(ROOT/'streamlit_app'/'QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
with zipfile.ZipFile(ROOT/'AstroTutor_relazione_e_interfaccia.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob('*'):
        if p.is_file() and 'qa' not in p.relative_to(OUT).parts:z.write(p,'relazione/'+str(p.relative_to(OUT)))
    for p in (ROOT/'streamlit_app').iterdir():
        if p.is_file():z.write(p,'streamlit_app/'+p.name)
print(ROOT/'AstroTutor_relazione_e_interfaccia.zip')
