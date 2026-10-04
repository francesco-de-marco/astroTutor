"""Concise, source-checked Italian report; no new model/API execution."""
from pathlib import Path
import json, hashlib
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from PIL import Image
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'relazione_sintetica';OUT.mkdir(exist_ok=True)
PDF=OUT/'AstroTutor_relazione_sintetica.pdf'
S=json.loads((ROOT/'evaluation/final_groq_v1/summary.json').read_text(encoding='utf-8'))
M={m['model']:m for m in S['models']}
ORDER=['Qwen/Qwen2.5-1.5B-Instruct','Qwen/Qwen2.5-3B-Instruct','HuggingFaceTB/SmolLM3-3B','google/gemma-3-1b-it','meta-llama/Llama-3.2-3B-Instruct','mistralai/Mistral-7B-Instruct-v0.3']
NAMES=['Qwen 2.5 1.5B','Qwen 2.5 3B','SmolLM3 3B','Gemma 3 1B','Llama 3.2 3B','Mistral 7B v0.3']
W,H=A4;LEFT=43;WIDTH=W-86
c=canvas.Canvas(str(PDF),pagesize=A4)
c.setTitle('AstroTutor - Dal RAG originale al confronto DPO su sei modelli')
c.setAuthor('Progetto AstroTutor - relazione assistita da IA')
body=ParagraphStyle('body',fontName='Helvetica',fontSize=10.2,leading=14.2,textColor=HexColor('#24384b'))
small=ParagraphStyle('small',parent=body,fontSize=8.5,leading=11.6)
cell=ParagraphStyle('cell',parent=body,fontSize=9,leading=12)
heading=ParagraphStyle('heading',parent=body,fontName='Helvetica-Bold',fontSize=12,leading=16)
MD=[];y=0;page=0
def start(title,subtitle=None):
    global y,page
    page+=1;y=H-62
    c.setFillColor(HexColor('#159b89'));c.rect(LEFT,H-36,35,3,stroke=0,fill=1)
    c.setFont('Helvetica',8);c.setFillColor(HexColor('#657888'));c.drawRightString(W-LEFT,H-35,'ASTROTUTOR | RELAZIONE SINTETICA | 02.10.2026')
    put(title,ParagraphStyle('title',parent=heading,fontSize=19,leading=23),gap=10)
    if subtitle: put(subtitle,small,gap=12)
    MD.extend(['\n# '+title,''])
def put(text,style=body,gap=9):
    global y
    p=Paragraph(text,style);_,h=p.wrap(WIDTH,1000)
    assert y-h>48,(page,y,h,text[:50])
    p.drawOn(c,LEFT,y-h);y-=h+gap
    MD.extend([text,''])
def section(text):put(text,heading,7)
def table(rows,widths):
    global y
    data=[[Paragraph(str(v),cell) for v in r] for r in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e9f1f5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,-1),.35,HexColor('#d7e1e8'))]))
    _,h=t.wrap(WIDTH,1000);assert y-h>48,(page,y,h);t.drawOn(c,LEFT,y-h);y-=h+12
    MD.extend([' | '.join(map(str,r)) for r in rows]);MD.append('')
def figure(file,caption,maxheight=290):
    global y
    p=ROOT/'grafici_relazione'/file
    with Image.open(p) as im:iw,ih=im.size
    scale=min(WIDTH/iw,maxheight/ih);dw,dh=iw*scale,ih*scale
    assert y-dh>65,(page,y,dh)
    c.drawImage(str(p),LEFT+(WIDTH-dw)/2,y-dh,width=dw,height=dh);y-=dh+5
    put(caption,small,10)
    MD.extend([f'![{caption}]({p.as_posix()})',''])
def end():
    c.setStrokeColor(HexColor('#d7e1e8'));c.line(LEFT,39,W-LEFT,39)
    c.setFont('Helvetica',8);c.setFillColor(HexColor('#657888'))
    c.drawString(LEFT,26,'Dati di progetto e giudizi IA: risultati esplorativi, non validazione didattica.')
    c.drawRightString(W-LEFT,26,f'{page}/5');c.showPage()

start('AstroTutor: obiettivo e versione originale',
      'Dalla consultazione dei documenti al confronto sperimentale dell’allineamento DPO.')
put('AstroTutor nasce come tutor di astronomia capace di rispondere usando documenti di riferimento e un livello scelto dall’utente: <b>A primaria, B medie, C superiori, D università</b>. L’obiettivo è fornire spiegazioni corrette e comprensibili rispetto alle conoscenze dello studente. Nel prototipo il livello è selezionato esplicitamente: non viene stimato mediante un test iniziale.')
section('1. La pipeline già presente nel repository')
put('Il sistema usa il <b>RAG</b> (Retrieval-Augmented Generation): prima cerca nei documenti i passaggi pertinenti, poi li inserisce nel prompt del modello. Il flusso è: <b>PDF e fonti divulgative → estrazione → chunk → indice vettoriale → ricerca e riordino → risposta adattata</b>.')
table([
 ['Modulo o classe','Funzione e tecnologie'],
 ['parsing.py; ingest_api_data.py','Docling per i PDF; acquisizione di contenuti divulgativi, anche da Vikidia ed EduINAF.'],
 ['chuncking.py; indexing.py','Pulizia e suddivisione del testo; embedding BAAI/bge-m3 e indice persistente ChromaDB.'],
 ['AdvancedRetriever<br/>(retrieval.py)','Combina query italiana e tradotta; filtra per livello con fallback ai livelli vicini; riordina con BAAI/bge-reranker-v2-m3.'],
 ['RAGGenerator<br/>(generation.py)','Costruisce il prompt con domanda, contesto e livello; genera tramite Ollama, con Qwen 2.5 3B come modello predefinito.'],
 ['ResponseGuardrails;<br/>TripletFactory (alignment.py)','Controlli di registro e leggibilità con possibile rigenerazione; costruzione di esempi di preferenza tramite un modello “oracolo”.'],
 ['evaluation.py;<br/>retrieval_eval.py','Valutazione storica con Gulpease, faithfulness RAGAS e rifiuti fuori dominio; analisi IR con BM25, Recall@k, MRR e nDCG.']
],[145,WIDTH-145])
section('2. Il primo uso del DPO')
put('Il <b>Direct Preference Optimization</b> insegna al modello a preferire una risposta <i>chosen</i> a una <i>rejected</i>, date la stessa domanda e il medesimo contesto. Nel progetto originale erano già presenti training QLoRA/TRL e due versioni allineate di Qwen 3B: 378 e 623 triplette, poi esportate in GGUF e usate con Ollama. L’oracolo per i dati era configurato su Groq; questo non rendeva interamente locale la preparazione del dataset.')
put('Il report del 26 luglio documenta risultati non replicati tra valutazione locale e Colab e problemi nella metrica dei rifiuti. La criticità iniziale era quindi anche <b>come misurare l’effetto del DPO</b>, non soltanto quanto addestrare il modello.',small)
end()

start('Cosa è cambiato e dove si trova il codice')
put('La nuova fase ha mantenuto l’architettura RAG, aggiungendo tracciabilità, prove controllate e un confronto su più modelli. Non è stata riscritta da zero l’applicazione.')
section('3. Modifiche effettive nel branch esperimento-calibrazione')
table([
 ['Intervento','Perché è importante'],
 ['config.py e alignment.py','La chiave dell’oracolo è richiesta quando serve a generare dati, non al semplice import dei moduli locali. Il modello è configurabile tramite ambiente.'],
 ['RAGGenerator.generate_record()','Salva prompt, contesti, configurazione, risposta originale e finale, tempi e dettagli dei guardrail. È possibile fornire gli stessi documenti a confronti diversi.'],
 ['Guardrail tracciati e disattivabili','Distingue la risposta del modello dalle eventuali correzioni successive. Il controllo di registro non viene confuso con una verifica scientifica.'],
 ['retrieval.py','Embedding e re-ranker selezionano CUDA quando disponibile, altrimenti CPU. Non viene introdotto un nuovo algoritmo di retrieval.'],
 ['scripts/run_dev.py; judge_dev.py','Aggiungono confronti controllati e giudizi riprendibili, con registrazione dei dati e materiale per revisione. Dipendenze e file ignorati sono stati aggiornati.']
],[155,WIDTH-155])
section('4. Prove preliminari e nuova campagna sperimentale')
put('Prima della campagna finale sono state svolte prove sulle penalità di generazione, controlli del modello base e piccoli pilot DPO e <b>SFT</b>. Lo SFT addestra su esempi di risposta desiderata; il DPO su preferenze tra due risposte. Sono presenti anche pilot di continuazione SFT+DPO e SFT aggiuntivo. Queste prove hanno funzione diagnostica e <b>non sono i risultati sui sei modelli</b> riportati nelle pagine successive.')
put('I tentativi di produrre automaticamente nuove coppie tramite modelli e filtri hanno avuto una resa bassa. Il dataset finale da 600 coppie è stato quindi costruito sinteticamente dall’assistente, a partire dai concetti dei documenti, e conservato con provenienza e controlli. Non è il semplice ampliamento del vecchio dataset da 623 triplette.')
section('5. Una distinzione necessaria per la consegna')
put('Il confronto Git verificato è <b>main 6859ea6 → esperimento-calibrazione 9e21b5b</b>: 10 file tracciati differiscono. Diversi script dei pilot sono presenti localmente ma risultano ancora non tracciati. La campagna finale e i grafici sono invece nella cartella esterna <b>outputs/dpo_pdf_600</b> dell’area Codex: non vanno descritti come già committati nel branch.')
put('File cruciali della campagna: <b>dataset_consegna/build.py</b> costruisce i dati; <b>train_dpo_600.py</b> e le varianti di famiglia eseguono il training; <b>compare_test_*600.py</b> generano base/DPO; <b>evaluate_final_local.py</b>, nonostante il nome, gestisce anche il giudice Groq; <b>make_relation_charts.py</b> produce i grafici dai file salvati.',small)
end()

start('Il nuovo esperimento e l’andamento del training')
section('6. Dati e condizioni del confronto')
put('Il training comprende <b>75 domande × 4 livelli × 2 risposte rifiutate = 600 coppie</b>. I 300 prompt hanno una risposta preferita e due tipi di negativo: errori fattuali o contenuti fuori tema. Questo insegna soprattutto correttezza e pertinenza; non isola la capacità di adattare la spiegazione al livello scolastico.')
put('Sono stati addestrati <b>Qwen 2.5 1.5B e 3B, SmolLM3 3B, Gemma 3 1B, Llama 3.2 3B e Mistral 7B v0.3</b>. Lo stack usa PyTorch/CUDA, Transformers, Datasets, Accelerate, TRL, PEFT e bitsandbytes. Sulla RTX 4070 Laptop da 8 GB, QLoRA carica i pesi in NF4 e addestra piccoli adapter LoRA, riducendo il fabbisogno di memoria.')
put('<b>Configurazione comune:</b> 2 epoche, 300 step, learning rate 5×10<super>-6</super>, beta 0,1, LoRA rank 8/alpha 16, batch effettivo 4, seed 42. Sono stati rispettati i template dei modelli; per Gemma e Mistral l’istruzione di sistema è unita al primo messaggio utente. Non è una ricerca degli iperparametri ottimali per ciascuna famiglia.',small)
figure('01_training_loss.png','<b>Figura 1.</b> Loss DPO nei sei training. La linea tenue mostra il log per step; quella piena una media mobile di 20 step. La linea verticale indica la fine della prima epoca.',maxheight=277)
put('La loss diminuisce nei sei run: il modello sta imparando le preferenze del dataset. Il calo più rapido o il valore finale più basso <b>non provano che un modello sia un tutor migliore</b>. Non sono disponibili curve di validation; per valutare l’effetto sulle risposte si usa il test separato.')
section('7. Test congelato e giudice')
put('Il test usa 20 domande nuove, 10 brani e 4 livelli: <b>80 prompt per modello</b>, generati sia con il modello base sia con l’adapter DPO. I documenti del test sono separati da quelli del training. Entrambe le condizioni usano gli stessi contesti riformulati in italiano, decoding greedy, NF4 e massimo 384 nuovi token, senza guardrail. Il test isola la generazione con contesto fornito: non rivaluta il retrieval RAG.')
put('Le 960 risposte sono state valutate da <b>GPT-OSS 120B su Groq</b>, senza indicare al giudice il modello o la condizione. Otto duplicati identici per lo stesso prompt condividono il giudizio: 952 valutazioni uniche. Il primo giudice locale Qwen 7B è stato scartato dopo controlli qualitativi. I risultati finali restano giudizi IA, non una revisione umana.',small)
end()

start('Risultati: la correttezza migliora, ma non sempre')
put('La rubrica distingue risposte <b>C</b> (corrette), <b>P</b> (parziali o con imprecisioni rilevanti) e <b>I</b> (errate nel nucleo o con errori gravi). Completezza, adeguatezza al livello e chiarezza sono valutate separatamente da 0 a 2.')
figure('07_correctness.png','<b>Figura 2.</b> Percentuale di risposte classificate C dal giudice IA, su 80 per condizione. Le quattro versioni di una domanda non sono osservazioni indipendenti.',maxheight=249)
rows=[['Modello','C base → DPO','Variazione','Adeguatezza base → DPO']]
for model,name in zip(ORDER,NAMES):
    m=M[model];b=m['base'];d=m['dpo'];delta=m['correctness_uncertainty']['delta_percentage_points']
    rows.append([name,f"{b['correctness'].get('C',0)} → {d['correctness'].get('C',0)} /80",f'{delta:+.2f} p.p.',f"{b['adequacy']:.2f} → {d['adequacy']:.2f}"])
table(rows,[135,102,80,WIDTH-317])
put('La correttezza stimata cresce in <b>cinque modelli su sei</b>; SmolLM3 registra una diminuzione. Llama mostra il maggiore aumento assoluto (+13 risposte C); Mistral passa da 73 a 79 su 80. Sommando descrittivamente le condizioni dei sei modelli, le risposte C passano da 333 a 364 su 480. Questa somma non è un campione di 480 domande indipendenti.')
put('La sola percentuale di C non descrive tutte le regressioni. Per esempio, in Qwen 1.5B aumentano sia le risposte corrette (40→42) sia quelle errate I (18→20), a scapito delle parziali. In Qwen 3B gli errori I scendono da 8 a 0, mentre diminuisce la completezza media. Il risultato dipende quindi dalla dimensione di qualità osservata.')
put('<b>Incertezza:</b> gli intervalli bootstrap del fascicolo completo raggruppano per 10 brani. Non coprono l’errore del giudice o la variabilità tra seed; non è stata applicata una correzione per confronti multipli. Le differenze sono da presentare come risultati esplorativi, non come prova generale dell’efficacia del DPO.',small)
end()

start('Adattamento didattico e conclusione')
figure('09_quality_dimensions.png','<b>Figura 3.</b> Medie dei voti IA (0-2). Correttezza, completezza e adeguatezza sono dimensioni distinte: il DPO non migliora uniformemente tutte le qualità di un tutor.',maxheight=202)
figure('13_response_length.png','<b>Figura 4.</b> Lunghezza delle risposte: mediana, quartili e distribuzione. La riduzione è comune ai sei modelli; maggiore brevità non equivale automaticamente a maggiore utilità didattica.',maxheight=211)
put('Il caso Mistral rende evidente il compromesso: la correttezza cresce, ma la completezza media passa da <b>1,95 a 1,80</b>, l’adeguatezza da <b>1,95 a 1,84</b> e le parole medie da circa <b>86 a 44</b>. Anche negli altri modelli il DPO tende ad accorciare le risposte. I casi al limite di token sono stati conservati, non esclusi dal confronto.')
put('<b>Conclusione.</b> Il progetto passa da un prototipo RAG con primi tentativi di allineamento a un confronto più tracciabile e ripetibile su sei modelli. I risultati non permettono di affermare che “il DPO è inutile”: mostrano benefici sulla correttezza, ma non un adattamento didattico uniforme. Per l’obiettivo originale del tutor, resta da verificare se questi benefici siano percepiti anche dagli studenti.')
put('<b>Limiti e passo finale:</b> dati sintetici scritti dall’assistente, un solo giudice IA, un seed, test piccolo e nessuno studio sull’apprendimento. Il campione cieco di 24 coppie è pronto ma non ancora revisionato da una persona. I pilot SFT esistono, ma non costituiscono un confronto SFT sistematico sui sei modelli.',small)
put('<b>Fonti interne verificate:</b> repository locale e diff main/esperimento-calibrazione; report storico del 26/07/2026; manifest del dataset e del test; log dei sei training; final_groq_v1/summary.json e scored_responses.json. I grafici sono riprodotti dai dati salvati, senza nuove generazioni.',small,0)
end()
c.save();assert len(PdfReader(str(PDF)).pages)==5
(OUT/'Relazione_contenuto.md').write_text('\n'.join(MD),encoding='utf-8')
(OUT/'fonti_e_versioni.json').write_text(json.dumps({'git_main':'6859ea6ae5fa0b975c32098514f93e61847155be','git_branch':'esperimento-calibrazione','git_head':'9e21b5b','experiment_directory':str(ROOT),'final_summary_sha256':hashlib.sha256((ROOT/'evaluation/final_groq_v1/summary.json').read_bytes()).hexdigest(),'report_pages':5,'historical_source':'astroTutor/report/report_2026_07_26.md','note':'Pilot files include untracked work; six-model campaign is outside original Git repository.'},indent=2),encoding='utf-8')
print(PDF)
