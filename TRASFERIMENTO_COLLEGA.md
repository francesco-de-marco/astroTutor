# Installazione e trasferimento dei file locali

## 1. Ambiente del collega

Questo requirements descrive **Windows x64, Python 3.14 e NVIDIA/CUDA 12.8**.
Non è una ricetta per Mac, CPU-only o altri sistemi. Il driver NVIDIA deve supportare
la build CUDA scelta; non serve installare il CUDA Toolkit per usare le wheel.
I pin ML provengono dal venv dei run, quelli Streamlit dalla demo e quelli PDF
dal runtime usato per le relazioni. Non è un lock completo delle dipendenze transitive.

Dalla radice del repository aggiornato:

```powershell
py -3.14 -m venv .venv-consegna
.\.venv-consegna\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-consegna-win-cu128.txt
python -m pip check
python -c "import torch, streamlit, chromadb, transformers, peft, trl; print(torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

CUDA deve risultare True per la demo quantizzata. Questa installazione comprende
la UI, quindi **non occorre eseguire install_ui.py**. Ollama è necessario solo per
le vecchie funzioni che lo invocano, non per la nuova demo Transformers/PEFT.

## 2. Materiale da passare separatamente

Trasferire con chiavetta/disco esterno oppure cartella privata Drive/OneDrive:

Per preparare un unico ZIP con struttura già corretta, usare lo script del repository
`scripts/package_demo_assets.py`, passando le cartelle originali con `--experiment`,
`--index` e un nuovo file `--output`. Il parametro `--database-closed` conferma che
indicizzatore e applicazioni che scrivono nel database sono stati chiusi.
Lo ZIP contiene tutti i sei adapter finali e l'indice, con SHA256 di ogni file;
non contiene modelli base, credenziali o PDF. Il collega lo estrae nella radice
del clone (quella che contiene README.md), sovrapponendo le cartelle previste.

| Dal PC dei run | Al collega, dentro il clone del repository |
|---|---|
| `astroTutor/data/vector_db/` (intera cartella) | `data/vector_db/` |
| `outputs/dpo_pdf_600/runs/<modello>_train_v1/adapter/` | `experiments/dpo_pdf_600/runs/<modello>_train_v1/adapter/` |

Trasferire **tutta** la cartella adapter, compresi `adapter_model.safetensors`,
configurazione e tokenizer. Servono gli adapter finali dei sei run `train_v1`,
non smoke, checkpoint intermedi o pilot. Si può iniziare solo con Qwen 3B.
Per evitare copie incoerenti dell'indice, chiudere processi di indicizzazione e
applicazioni che scrivono nel database prima di comprimerlo. Copiare anche le
sottocartelle UUID di Chroma, non soltanto `chroma.sqlite3`.

Gli adapter GitHub contengono solo metadati: sovrapporre le cartelle trasferite
aggiunge i pesi mancanti. Non modificare manifest, nomi dei run o adapter_config.json.

**Non trasferire** `.env`, token, `.venv`, `.git`, cache generiche o credenziali.
I PDF originali e i chunk servono per ricostruire l'indice e consultare le fonti;
per interrogare l'indice già completo non è necessario copiarli nuovamente.

## 3. Modelli base ed encoder

Gli adapter non contengono il modello base. Il collega deve avere nella propria
cache Hugging Face i pesi del modello scelto, BAAI/bge-m3 e BAAI/bge-reranker-v2-m3.
La UI lavora offline e non li scarica automaticamente.

Per scaricare Qwen 3B e i due encoder (diversi GB), dopo aver attivato il venv:

```powershell
python scripts/download_demo_models.py
```

Per tutti i sei modelli usare `--all`. Llama e Gemma richiedono accesso approvato
sul **proprio** account Hugging Face e login `hf auth login`. Non condividere il token.
Se la cache esiste già, vengono riutilizzati i file corrispondenti; lo script usa
la revisione del modello base registrata nel training.

In alternativa è possibile trasferire soltanto le cartelle `models--...` necessarie
della cache HF, preservando la struttura snapshots/blobs e risolvendo correttamente
eventuali symlink. Il download con lo script è la procedura più semplice da verificare.

## 4. Avvio

```powershell
& .\experiments\dpo_pdf_600\streamlit_app\run_app.ps1
```

Aprire http://127.0.0.1:8501. Iniziare con Qwen 3B, livello B e una domanda semplice.
Verificare che compaiano le fonti e che funzionino Base e DPO. Non servono nuove
chiamate Groq, valutazioni o training. Consultare README_COLLEGA.md per i risultati.
