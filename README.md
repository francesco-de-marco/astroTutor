# AstroTutor 🚀

**AstroTutor** è un sistema di Information Retrieval e RAG (Retrieval-Augmented Generation) sviluppato per rispondere a domande basate su documenti PDF (es. dispense, libri, appunti) adattando le risposte al livello di comprensione dell'utente. 

Il sistema permette di fornire spiegazioni personalizzate scegliendo tra i seguenti livelli:
- **A** = Bambini
- **B** = Scuole Medie
- **C** = Scuole Superiori
- **D** = Universitari

## 📌 Architettura e Tecnologie

Il progetto è basato su un'architettura modulare ed esegue i modelli interamente in locale:
- **Ingestion API**: Integrazione diretta tramite API pubbliche (es. Vikidia per Livello A, EduINAF per Livello B) per bypassare il parsing pesante e ottenere testi divulgativi puliti.
- **Parsing PDF**: [Docling](https://github.com/DS4SD/docling) per estrarre in modo accurato testo strutturato, formule matematiche LaTeX e tabelle dai PDF di alto livello (C/D).
- **Vector Database & Retrieval**: ChromaDB per memorizzare i vettori (embeddings BAAI/bge-m3) affiancato da un **Cross-Encoder (Re-ranker)** per la massima precisione semantica.
- **LLM**: Esecuzione locale tramite **Ollama** (es. `qwen2.5:3b`), per garantire la privacy e permettere l'utilizzo offline.

## 📂 Struttura del Progetto

```text
progetto_IR/
│
├── data/
│   ├── raw/                 # PDF originali suddivisi in cartelle per TOPIC
│   └── processed/parsed/    # Output del parsing (file JSON strutturati e Markdown)
│
├── src/                     # Moduli core del sistema RAG
│   ├── ingest_api_data.py   # Ingestione dati da API pubbliche (Vikidia, EduINAF)
│   ├── parsing.py           # Pipeline di conversione PDF -> JSON usando Docling
│   ├── parsing_kaggle.py    # Script alternativo di parsing per ambienti tipo Kaggle
│   ├── chuncking.py         # Pulizia HTML (BeautifulSoup) e chunking intelligente
│   ├── indexing.py          # Embedding (BGE-m3) dei chunk nel Vector DB (ChromaDB)
│   ├── retrieval.py         # Ricerca vettoriale e riordino tramite Re-Ranker
│   ├── generation.py        # Generazione della risposta tramite LLM basata sul contesto
│   ├── evaluation.py        # Metriche per valutare le prestazioni del RAG
│   └── alignment.py         # Moduli per la verifica di allineamento delle risposte
│
├── main.py                  # CLI interattiva per testare il sistema RAG (RAG Tester)
├── compare.py               # Script per confrontare il RAG con la sola memoria dell'LLM (Baseline)
├── config.py                # File di configurazione centralizzata
└── README.md                # Questo file
```

## 🧠 Flusso dei Dati (Pipeline)

1. **Ingestion & Parsing**: I documenti arrivano da due vie. I PDF (`data/raw/`) vengono estratti tramite `src/parsing.py` (Docling). I contenuti divulgativi vengono invece scaricati direttamente tramite chiamate REST (`src/ingest_api_data.py`). Tutto converge in formato JSON strutturato in `data/processed/parsed/`.
2. **Chunking** (`src/chuncking.py`): I JSON vengono puliti dal rumore HTML tramite `BeautifulSoup` (preservando i segni matematici) e suddivisi in frammenti ottimali (chunk).
3. **Indexing** (`src/indexing.py`): I chunk vengono passati a un modello di embedding multilingua (`BAAI/bge-m3`) e memorizzati in ChromaDB.
4. **Retrieval** (`src/retrieval.py`): All'inserimento di una query, il sistema recupera i chunk semanticamente simili e utilizza un **Cross-Encoder** per riordinarli (Re-ranking) garantendo la massima aderenza alla domanda.
5. **Generation** (`src/generation.py`): Il contesto recuperato viene iniettato nel prompt assieme alla domanda originale e al livello di difficoltà richiesto. L'LLM genera così una risposta chiara e mirata.

## 🚀 Come avviare il progetto

### Prerequisiti
1. **Python 3.10+** (consigliato l'uso di un virtual environment).
2. Installare le dipendenze del progetto.
3. Installare [Ollama](https://ollama.com/) per eseguire i Large Language Models in locale.
4. Scaricare il modello predefinito tramite terminale:
   ```bash
   ollama run qwen2.5:3b
   ```

### 1. Eseguire il RAG Interattivo
Per fare domande direttamente ai tuoi PDF utilizzando il RAG:
```bash
python main.py
```
Ti verrà richiesto di digitare una query e di indicare il livello di difficoltà (A, B, C o D). Il sistema elaborerà la richiesta e stamperà la risposta.

### 2. Confrontare la Baseline con il RAG
Per verificare concretamente il beneficio del sistema RAG rispetto al modello base (cioè LLM senza accesso ai PDF), puoi lanciare lo script di comparazione:
```bash
python compare.py
```
Questo eseguirà due test paralleli sulla tua domanda:
- ❌ **Versione 1**: Senza RAG (il modello usa solo quello che ha "studiato" durante il training).
- ✅ **Versione 2**: Con RAG (il modello consulta la knowledge base prima di rispondere).

## 🚧 TODO e Sviluppi Futuri

Ci sono ancora alcune aree in fase di sviluppo:

- [ ] **Valutazione del Modello (`src/evaluation.py`)**: Implementazione di metriche avanzate (LLM-as-a-Judge, RAGAS) per calcolare l'accuratezza e la fedeltà al contesto del RAG.
- [ ] **Allineamento e Sicurezza (`src/alignment.py`)**: Preparazione del dataset DPO e implementazione di guardrails per assicurare che il tono e i contenuti siano adatti al target (es. Bambini).
- [ ] **Interfaccia Utente (UI)**: Passaggio dalla CLI attuale (`main.py`) a un'interfaccia web user-friendly (es. Streamlit) per un'interazione più fluida.
- [x] **Advanced RAG**: Integrare tecniche di recupero avanzato come Multi-Query Expansion e **Re-ranker (CrossEncoder)** per migliorare la precisione (COMPLETATO).
- [ ] **Containerizzazione**: Creare un `Dockerfile` e un `docker-compose.yaml` per semplificare il deploy del database vettoriale e dell'applicazione in ambienti cloud.


## Aggiornamento sperimentale e consegna

Il branch esperimento-calibrazione include pilot, confronto Base/DPO su sei modelli,
dataset sintetico, risultati, grafici, relazione approfondita e demo Streamlit.
Vedere [README per il collega](README_COLLEGA.md) per orientarsi e avviare la demo.
