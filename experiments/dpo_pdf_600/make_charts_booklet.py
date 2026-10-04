import json,textwrap,zipfile
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape,A4
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from PIL import Image
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'grafici_relazione'
FIGS=json.loads((OUT/'figure_catalog.json').read_text(encoding='utf-8'))
W,H=landscape(A4)
pdf=OUT/'AstroTutor_grafici_relazione.pdf'
c=canvas.Canvas(str(pdf),pagesize=(W,H))
c.setTitle('AstroTutor - Grafici per la relazione')
c.setAuthor('AstroTutor - analisi assistita da IA')
style=ParagraphStyle('caption',fontName='Helvetica',fontSize=10,leading=14,textColor=HexColor('#26364a'))
def para(text,x,y,width,style=style):
    p=Paragraph(text,style);_,height=p.wrap(width,1000);p.drawOn(c,x,y-height);return y-height
def footer(page):
    c.setStrokeColor(HexColor('#d2dce4'));c.line(36,34,W-36,34)
    c.setFillColor(HexColor('#53677a'));c.setFont('Helvetica',8)
    c.drawString(36,21,'AstroTutor | Sei modelli, confronto base / DPO | Valutazione automatica esplorativa')
    c.drawRightString(W-36,21,f'{page} / {len(FIGS)+1}')
c.setFillColor(HexColor('#159b89'));c.rect(36,H-70,65,5,fill=1,stroke=0)
c.setFillColor(HexColor('#203348'));c.setFont('Helvetica-Bold',27);c.drawString(36,H-112,'AstroTutor')
c.setFont('Helvetica',19);c.drawString(36,H-143,'Grafici del training e del confronto finale')
y=H-179
y=para('<b>6 modelli · 600 coppie di training · 960 risposte di test · 18 figure</b>',36,y,W-72)-22
y=para('La correttezza stimata dal giudice migliora in cinque modelli su sei. Il miglioramento non si traduce in un adattamento didattico uniforme: le risposte diventano più brevi e, in alcuni casi, meno complete.',36,y,W-72)-20
y=para('<b>Come usare il fascicolo</b><br/>Figure 01-06: andamento del training. Figure 07-15: risultati e incertezza. Figura 16: risorse. Figure 17-18: transizioni e differenze per argomento. Per il corpo della relazione si consigliano 01, 07, 09, 10, 13 e 15; le altre possono andare in appendice.',36,y,W-72)-20
y=para('<b>Limiti essenziali</b><br/>I giudizi provengono da GPT-OSS 120B tramite Groq e non sono stati validati da revisori umani. Il test contiene 20 domande ripetute a quattro livelli, su 10 brani: le 960 risposte non sono osservazioni indipendenti. Il training usa un solo seed; non ci sono curve di validation. Non è stato eseguito un braccio SFT in questo confronto. Non si misura l\'apprendimento degli studenti.',36,y,W-72)-20
para('<b>Fonti e riproducibilità</b><br/>Grafici ricavati dai log salvati dei sei run e dai giudizi finali. Il pacchetto include PNG, SVG, didascalie, script di generazione e checksum delle fonti. Nessuna risposta o configurazione di training è stata modificata per questa analisi.',36,y,W-72)
footer(1);c.showPage()
for i,f in enumerate(FIGS,2):
    c.setFillColor(HexColor('#53677a'));c.setFont('Helvetica-Bold',10)
    c.drawString(36,H-28,f"FIGURA {i-1:02d} | "+('TRAINING' if f['kind']=='train' else 'RISULTATI DEL TEST'))
    p=OUT/(f['id']+'.png')
    with Image.open(p) as image:iw,ih=image.size
    scale=min((W-56)/iw,405/ih);dw,dh=iw*scale,ih*scale
    c.drawImage(str(p),(W-dw)/2,H-43-dh,width=dw,height=dh)
    para(f['caption'],36,117,W-72)
    footer(i);c.showPage()
c.save()
assert len(PdfReader(str(pdf)).pages)==19
with zipfile.ZipFile(ROOT/'AstroTutor_grafici_relazione.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        if p.is_file():z.write(p,'grafici_relazione/'+p.name)
    for name in ['make_relation_charts.py','make_charts_booklet.py']:
        z.write(ROOT/name,'script/'+name)
print(pdf)
