"""Build the final report from the verified concise report, adding the live UI."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'build_short_report.py').read_text(encoding='utf8')
s=s.replace("OUT=ROOT/'relazione_sintetica'","OUT=ROOT/'relazione_finale'")
s=s.replace('AstroTutor_relazione_sintetica.pdf','AstroTutor_relazione_finale.pdf')
s=s.replace('ASTROTUTOR | RELAZIONE SINTETICA | 02.10.2026','ASTROTUTOR | RELAZIONE FINALE | 03.10.2026')
s=s.replace("f'{page}/5'","f'{page}/6'")
s=s.replace("start('AstroTutor: obiettivo e versione originale',\n      'Dalla consultazione dei documenti al confronto sperimentale dell’allineamento DPO.')", "start('AstroTutor',\n      'Relazione finale di progetto — Tutor astronomico basato su RAG e valutazione del DPO su sei modelli linguistici.')")
s=s.replace('Cosa è cambiato e dove si trova il codice','Evoluzione del progetto e tracciabilità')
s=s.replace('Una distinzione necessaria per la consegna','Organizzazione degli artefatti')
s=s.replace('Limiti e passo finale:', 'Limiti e sviluppi futuri:')
s=s.replace('ancora revisionato da una persona','sottoposto a revisione umana indipendente')
extra="""
start('Interfaccia dimostrativa e riproducibilità')
section('8. Utilizzo del tutor con Streamlit')
put('Il progetto è completato da una semplice interfaccia web locale. L’utente seleziona il livello scolastico, uno dei sei modelli e la modalità <b>Base, DPO o confronto affiancato</b>. Alla domanda seguono le risposte e i brani effettivamente recuperati, consultabili in un pannello espandibile. La sessione può essere esportata in JSON; le domande sono elaborate separatamente, senza memoria conversazionale.')
table([
 ['Componente','Responsabilità'],
 ['app.py','Gestisce la pagina Streamlit, le impostazioni, la visualizzazione delle risposte e delle fonti; presenta anche i risultati congelati dell’esperimento.'],
 ['TutorService (backend.py)','Riusa la ricerca di AdvancedRetriever e la costruzione del prompt di RAGGenerator. Carica i pesi e gli adapter finali da disco tramite Transformers e PEFT.'],
 ['Confronto Base/DPO','Recupera i brani una sola volta; usa il medesimo modello con adapter disattivato o attivo. Un lock serializza l’accesso e un solo modello rimane caricato.'],
 ['run_app.ps1; install_ui.py','Avviano il server su localhost e gestiscono le dipendenze della UI in una cartella separata, preservando l’ambiente usato per i training.']
],[150,WIDTH-150])
put('La generazione usa la GPU e i pesi quantizzati NF4. Embedding e re-ranker restano su CPU per lasciare memoria al modello linguistico. Non sono necessarie chiamate Groq: la demo usa i modelli già scaricati e l’indice RAG esistente. La scheda dei risultati legge i file dell’esperimento senza ricalcolarli.')
section('9. Confini della dimostrazione')
put('La demo esegue retrieval live con la sola query italiana e il prompt RAG del progetto; non applica i guardrail. Il test sperimentale, invece, confronta i modelli con contesti già fissati. Le risposte ottenute dall’interfaccia non sono quindi ulteriori osservazioni del test né una replica esatta della pipeline Ollama originale. Le fonti rendono il risultato ispezionabile, ma non garantiscono da sole la correttezza della risposta.')
put('Sono stati verificati l’avvio della pagina, la lettura dei sei risultati e un confronto reale Base/DPO con Qwen 2.5 3B, recuperando due brani dall’indice. Questa prova controlla il collegamento dei componenti; non costituisce una nuova valutazione della qualità didattica o un collaudo esteso di tutti i modelli.')
section('10. Materiale consegnabile')
put('La relazione riassume architettura, modifiche e risultati; il fascicolo dei grafici contiene le analisi supplementari. La cartella dell’esperimento conserva dataset, manifest, adapter, log e valutazioni. La cartella <b>streamlit_app</b> contiene la demo e le istruzioni di avvio. Questi artefatti devono accompagnare il repository: la campagna esterna e l’interfaccia non risultano automaticamente incluse nel branch Git.')
put('<b>Riproducibilità:</b> i manifest registrano revisioni dei modelli, configurazioni e hash dei dati. Una nuova esecuzione richiede i pesi locali, l’indice e l’ambiente descritto; i soli sorgenti della UI non includono diversi gigabyte di modelli.',small)
put('<b>Nota metodologica:</b> il dataset finale e la redazione sono stati assistiti da IA. I risultati numerici provengono dai file salvati della campagna. Non si attribuisce ai giudizi automatici il valore di una validazione indipendente con docenti o studenti.',small,0)
end()
"""
s=s.replace('c.save();assert len(PdfReader(str(PDF)).pages)==5',extra+'\nc.save();assert len(PdfReader(str(PDF)).pages)==6')
s=s.replace("'report_pages':5","'report_pages':6")
(ROOT/'build_final_report.py').write_text(s,encoding='utf8')
print(ROOT/'build_final_report.py')
