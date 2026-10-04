# AstroTutor — interfaccia locale

## Avvio sul PC del progetto

In PowerShell (non serve attivare manualmente il venv):

```powershell
& "C:\Users\matti\Documents\Codex\2026-09-09\com\outputs\dpo_pdf_600\streamlit_app\run_app.ps1"
```

Aprire http://127.0.0.1:8501. Terminare con Ctrl+C nella console.

Scegliere livello A–D, modello e modalità Base/DPO/Confronto affiancato. Scrivere una domanda; espandere le fonti per leggere i brani effettivamente usati. Il pulsante di download esporta in JSON la sessione corrente. Le domande sono indipendenti: la cronologia visibile non è memoria conversazionale.

La scheda Risultati presenta i dati finali già salvati, senza nuove chiamate al giudice. Non occorre una chiave Groq e non vengono rifatti training o download di pesi. Serve CUDA per generare. Iniziare con Qwen 2.5 3B o 1.5B; Mistral richiede più memoria. Il primo caricamento e il retrieval su CPU possono essere lenti.

## Collegamento al progetto

- `app.py`: pagina Streamlit, impostazioni, fonti, esportazione e risultati.
- `backend.py`: riusa `AdvancedRetriever.search` e `RAGGenerator.build_prompt` dal repository originale; carica da `runs` modello e adapter finali con Transformers/PEFT/NF4.
- La modalità Base disattiva l'adapter dello stesso modello; il confronto recupera i brani una sola volta. Un lock serializza l'accesso alla GPU e viene mantenuto un solo modello caricato.
- Embedding e re-ranker sono eseguiti su CPU per lasciare VRAM al modello. La ricerca usa soltanto la query italiana. I guardrail e la traduzione automatica non sono attivi nella demo.
- Il test scientifico utilizza contesti congelati, non questa ricerca live. Le risposte della demo non sono nuove misure del test.
- Chroma apre il database esistente senza aggiungere documenti. Può aggiornare file di servizio. La sessione resta in memoria fino alla cancellazione/chiusura, salvo esportazione richiesta dall'utente.

## Riproduzione e percorsi

Il progetto richiede il venv GPU già usato per i training, il repository, l'indice Chroma, la cache Hugging Face dei modelli e gli adapter. Le dipendenze della UI sono in `.packages`, separate dal venv. Per reinstallarle su questo ambiente:

```powershell
& "C:\Users\matti\Documents\astroTutor\.venv-gpu\Scripts\python.exe" .\install_ui.py
```

`install_ui.py` scarica wheel da PyPI e ne verifica SHA256; `ui_dependencies.json` registra le versioni. Non è un installatore autonomo dell'intero stack ML.

Su un altro PC configurare prima i percorsi:

```powershell
$env:ASTROTUTOR_REPO='D:\progetti\astroTutor'
$env:ASTROTUTOR_EXPERIMENT_DIR='D:\progetti\dpo_pdf_600'
# Facoltativo: indice in una posizione differente
$env:ASTROTUTOR_DB_PATH='D:\progetti\astroTutor\data\vector_db'
.\run_app.ps1 -Python 'D:\progetti\astroTutor\.venv-gpu\Scripts\python.exe'
```

La demo usa esclusivamente la cache locale. Se mancano pesi, scaricarli separatamente con le procedure del progetto. Nessun token va inserito nei file della UI.

## Limiti

Demo didattica locale, non servizio multiutente di produzione. Non è stata validata con studenti. I modelli possono produrre errori anche in presenza di fonti; il controllo del numero di token segnala eventuali risposte interrotte. La qualità del retrieval non è garantita per domande fuori dominio. La UI non modifica né ricalcola i risultati finali del confronto.
