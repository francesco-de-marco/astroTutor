# Novità del branch esperimento-calibrazione

## Scaricare gli aggiornamenti

Per un clone esistente, salvare prima eventuali modifiche proprie, poi:

```powershell
git fetch origin
git switch --track origin/esperimento-calibrazione
```

Se il branch locale esiste già: `git switch esperimento-calibrazione`, poi
`git pull --ff-only origin esperimento-calibrazione`.

## Leggere i risultati senza eseguire nulla

- [Relazione approfondita PDF](experiments/dpo_pdf_600/relazione_approfondita/AstroTutor_relazione_esame.pdf)
- [Riepilogo del confronto finale](experiments/dpo_pdf_600/evaluation/final_groq_v1/REPORT.md)
- [Protocollo del test](experiments/dpo_pdf_600/PROTOCOLLO_TEST_COMUNE.md)
- [Grafici e relative spiegazioni](experiments/dpo_pdf_600/grafici_relazione/LEGGIMI.md)
- [Dataset finale e provenienza](experiments/dpo_pdf_600/dataset_consegna/README.md)
- [Organizzazione della cartella sperimentale](experiments/dpo_pdf_600/PUBBLICAZIONE.md)

Sono presenti i pilot SFT/DPO, la campagna Base/DPO su sei modelli, i dati e i
giudizi finali. Non confondere i pilot con il test finale: SFT non è un braccio
del confronto finale. Le 600 coppie sono sintetiche (75 domande a quattro livelli
con due negativi). I giudizi sono automatici, senza validazione umana indipendente.

## Usare l’interfaccia

Serve l’ambiente GPU del progetto, con i modelli base nella cache Hugging Face,
l’indice `data/vector_db` e gli adapter nelle rispettive cartelle
`experiments/dpo_pdf_600/runs/<modello>_train_v1/adapter`.
Questi pesi e l’indice non sono caricati su GitHub: trasferirli dal PC originario
oppure ricostruirli con le procedure del progetto. Il repository contiene i log,
le configurazioni e i file di valutazione già completati.

Dalla radice del repository, dopo aver attivato il venv GPU:

```powershell
python .\experiments\dpo_pdf_600\streamlit_app\install_ui.py
& .\experiments\dpo_pdf_600\streamlit_app\run_app.ps1
```

Aprire http://127.0.0.1:8501. Non occorre Groq per la demo.
In alternativa usare `-Python 'percorso\python.exe'` nel launcher.
La UI rileva la radice del repository automaticamente; è possibile impostare
`ASTROTUTOR_REPO`, `ASTROTUTOR_EXPERIMENT_DIR` e `ASTROTUTOR_DB_PATH`.

Le dipendenze della UI vengono installate nella sua `.packages`, senza aggiornare
le librerie ML del venv. Il file `requirements-gpu-win.txt` descrive l’ambiente
Windows del lavoro, mentre requirements/constraints del pilot documentano i pin ML.
Non installare indiscriminatamente tutte le ricette in un ambiente già funzionante.

## Riproduzione

Gli script principali sono nella cartella sperimentale: `train_dpo_600.py`, varianti
per famiglia, `compare_test_*600.py`, `evaluate_final_local.py` e
`make_relation_charts.py`. Consultare `--help` e scegliere directory nuove per nuovi
esperimenti: i run pubblicati sono risultati storici, non destinazioni da sovrascrivere.
I launcher PowerShell usano `python` dell’ambiente attivo o il parametro `-Python`.
Le ricette storiche di preparazione possono conservare percorsi della macchina originale.

Le relazioni descrivono lo stato al 3 ottobre, quando la campagna era ancora esterna
al repository. Questo commit ne integra una copia documentata: non modifica i numeri
né ripete training o giudizi. Cache, chiavi API, PDF grezzi e pesi restano esclusi.
