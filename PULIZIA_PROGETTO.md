# Audit di pulizia per il progetto finale

Data: 10 novembre 2026. Perimetro confermato: campagna Base/DPO sui sei modelli,
ricostruzione dei dati, training, valutazione e demo Streamlit.

Questo è un inventario motivato, non una cancellazione eseguita. L'unico file
aggiunto da questo audit è questo documento. `DEMO_ASSETS_MANIFEST.json` era già
presente e non tracciato prima dell'analisi; non è stato modificato.

## 1. Esito

Il materiale storico separabile dal confronto finale occupa circa **3,606 GiB
(620 file)** nelle categorie sotto. Quasi tutto lo spazio è nei due vecchi GGUF.
Questi file sono fuori dal perimetro finale, non necessariamente duplicati: la
loro eliminazione fa perdere la riproduzione delle vecchie campagne.

La vecchia `.venv/` occupa altri **5,994 GiB**: si può dismettere dopo avere
verificato completamente `.venv-consegna/`. Il risparmio potenziale complessivo
arriva quindi a circa **9,60 GiB**, esclusa la cronologia Git. Eliminare file
tracciati dalla cartella di lavoro non elimina le loro versioni dalla cronologia.

Non è corretto classificare come superflui tutti i file generati: pesi, dati
congelati, manifest e risultati finali permettono di usare e verificare il lavoro
senza ripetere download, training o giudizi esterni.

## 2. Materiale storico separabile dal progetto finale

I percorsi sono relativi alla radice del repository. Rimuovere questi gruppi
richiede anche aggiornare i riferimenti storici nei README e nella documentazione.
Le dipendenze fra vecchi script vanno eliminate insieme, non file per file.

| Gruppo | File | MiB | Motivo |
|---|---:|---:|---|
| `models/` | 41 | 3681,116 | Vecchi GGUF/Ollama e pilot SFT/DPO; i sei adapter finali sono in `experiments/dpo_pdf_600/runs/` |
| `results/` | 355 | 3,151 | Risultati dei pilot, delle penalità e della valutazione di luglio; i risultati finali sono in `experiments/dpo_pdf_600/evaluation/` |
| `data/splits/` | 3 | 0,025 | Specifiche dei pilot e vecchie domande di sviluppo |
| Tentativi precedenti dentro l'esperimento, elencati sotto | 167 | 0,931 | Generatori e dataset scartati, controlli di download, revisione preliminare |
| Vecchi generatori e preparatori, elencati sotto | 9 | 0,090 | Ricette precedenti e generazione una tantum di script già presenti |
| Dodici script storici in `scripts/`, elencati sotto | 12 | 0,113 | Pilot e confronti diagnostici; non importati dai trainer e confronti finali |
| Sei sorgenti storici in `src/`, elencati sotto | 6 | 0,111 | Allineamento/valutazione precedenti, estranei al confronto finale e alla demo |
| Tredici vecchi file direttamente in `data/`, elencati sotto | 13 | 5,543 | Training e valutazioni precedenti |
| `experiments/dpo_pdf_600/evaluation/final_local_v1/` | 12 | 1,081 | Giudice locale scartato; il giudizio finale pubblicato è `final_groq_v1` |
| `src/__pycache__/` | 2 | 0,029 | Bytecode rigenerabile |

### Dentro `models/`

- `astrotutor-3b-dpo-Q4_K_M.gguf`
- `astrotutor-3b-dpo-v2-Q4_K_M.gguf`
- `Modelfile`, `Modelfile.v2`
- `pilot_after_sft_dpo_v1/`, `pilot_after_sft_sft_control_v1/`
- `pilot_dpo_smoke_v1/`, `pilot_dpo_train_v1/`, `pilot_sft_train_v1/`

Questi GGUF non sono gli adapter usati dalla demo finale, che carica
Transformers/PEFT dai sei run `*_train_v1`. Non cancellare la diversa cartella
`experiments/dpo_pdf_600/runs/`.

### Tentativi precedenti dentro `experiments/dpo_pdf_600/`

```text
automatico/
facts_first/
rich_contexts/
dataset_v1/
dataset_v2/
dataset_v3/
dataset_v4/
revisione_locale/
checks/
runs/preload_retry_history/
```

`dataset_v5/` è trattato separatamente sotto: alcuni preparatori lo referenziano.

### Vecchi generatori dentro `experiments/dpo_pdf_600/`

```text
build_dataset.py
list_groq_models.py
run_automatic.ps1
run_facts_first.ps1
run_groq.ps1
run_rich_contexts.ps1
source_candidates.json
prepare_trainer.py
prepare_development.py
```

`build_dataset.py` è il vecchio generatore: **non confonderlo con
`dataset_consegna/build.py`, da conservare**.

`prepare_trainer.py` legge il vecchio trainer del pilot per costruire il trainer
finale, già salvato. `prepare_development.py` costruisce il vecchio sviluppo e il
relativo script, usando anche percorsi assoluti della macchina originaria.
Rimuoverli è coerente con la riproduzione del confronto finale a partire dai dati
congelati; se si vuole ricostruire anche lo sviluppo storico, vanno invece
riparati e conservati con le loro dipendenze. Conservare comunque
`development_600_v1.json` e il suo manifest come prova della separazione dei dati.

### Dentro `scripts/`

```text
compare_continuations.py
compare_dpo_pilot.py
compare_sft_pilot.py
continue_sft_pilot.py
dpo_pilot.py
dpo_pilot_v2.py
judge_dev.py
prepare_curated_pilot.py
probe_base_bf16.py
run_dev.py
train_dpo_pilot.py
train_sft_pilot.py
```

Conservare `download_demo_models.py` e `package_demo_assets.py`.
`compare_dpo_pilot.py` e `train_dpo_pilot.py` servono ai vecchi preparatori citati
sopra: non togliere soltanto i primi lasciando i preparatori come comandi supportati.

### Dentro `src/`

```text
alignment_register.py
analysis.py
evaluation.py
retrieval_eval.py
alignment_dpo_colab.ipynb
evaluation_colab.ipynb
```

Questa scelta esclude deliberatamente la vecchia valutazione RAGAS e le metriche
IR del retrieval. Il confronto finale Base/DPO usa contesti congelati e **non
misura il retrieval**. Se tali metriche devono far parte della consegna finale,
conservare `retrieval_eval.py`, i suoi dati e la documentazione pertinente.

Non includere `alignment.py` in questo elenco: è ancora importato da
`generation.py`, usato dalla demo.

### Vecchi file direttamente in `data/`

```text
alignment_data.json
eval_progress_astrotutor-dpo-v2.jsonl
eval_progress_astrotutor-dpo.jsonl
eval_progress_qwen2.5_3b.jsonl
eval_questions.json
eval_results.json
query_translations.json
retrieval_eval.json
retrieval_eval_details.jsonl
retrieval_eval_meta.json
run_meta.json
training_log_dpo_v1_378triplette.txt
training_metrics.json
```

Sono legati ai sorgenti storici sopra. In particolare `alignment_data.json` e la
cache delle traduzioni servono alla vecchia valutazione del retrieval. La demo
non li legge, anche se importa le classi contenute in `alignment.py`.

## 3. Da togliere solo dopo una scelta o una modifica precisa

| Percorso | Condizione |
|---|---|
| `.venv/` | Ambiente storico Python 3.12 con torch 2.6/cu124, senza PEFT/TRL/Streamlit nei metadati rilevati. Verificare la demo completa nel nuovo ambiente prima di dismetterlo. |
| `.venv-consegna/` | Escluderlo da una consegna trasferibile, ma conservarlo sul PC per eseguire il progetto. Occupa circa 5,737 GiB. |
| `runs/*_smoke_v1/` dentro l'esperimento | I cinque launcher di famiglia controllano questi run prima di `-Mode train`. Si possono rigenerare con lo smoke, oppure adeguare i launcher; non sono cache del tutto scollegate. In totale pesano meno di 0,1 MiB. |
| `dataset_v5/` | Non serve alla ricostruzione del dataset finale se si conserva `source_snapshot.json`, ma resta referenziato da `prepare_final_test.py` e `prepare_development.py`. Risolvere prima il problema descritto nella sezione 5. |
| `compare_dpo_600.py` | È il confronto di sviluppo, ma `prepare_final_test.py` ne legge il sorgente per generare `compare_test_600.py`. Separare la preparazione dei dati dalla generazione di codice prima di rimuoverlo. |
| `evaluation/qwen3b_development_v1/` | Escludibile dal solo ricalcolo finale, utile per documentare lo sviluppo. Non scambiarlo per un secondo test finale. |
| `relazione_sintetica/`, `relazione_finale/` | Versioni precedenti della relazione approfondita; rimuovere insieme ai relativi generatori se si mantiene una sola relazione. |
| `build_short_report.py`, `build_final_report.py`, `prepare_final_report.py`, `package_submission.py` | Riguardano le precedenti relazioni; il pacchetto usa `relazione_finale/`. Conservare invece `build_extended_report.py`. |
| `main.py`, `compare.py` | CLI storiche Ollama: opzionali se la sola interfaccia supportata diventa Streamlit. Aggiornare il README principale. |
| `report/`, `TODO.md`, `feedback.md`, `Information Retrieval.md` | Documentazione storica o di progetto: non richiesta per il runtime; conservarla in archivio se serve a motivare il lavoro o i requisiti del corso. |
| `VERSIONI.md` | Descrive l'ambiente e la campagna di luglio, inclusa la costruzione del corpus; migrare le informazioni ancora utili prima di rimuoverlo. |
| `src/parsing_colab.ipynb`, `src/parsing_kaggle.ipynb`, `src/parsing_mineru_kaggle.ipynb` | Alternative di parsing. L'assenza di import non dimostra che non siano state usate per produrre il corpus. Conservare finché non si stabilisce quale procedura ricostruisce gli estratti adottati. |
| `requirements.txt`, `requirements-lock.txt`, `requirements-gpu-win.txt`, `requirements-local-win-py314.txt` | Ricette/ambienti precedenti. Consolidare la guida sul requirements di consegna; non sono tutti lock equivalenti dell'esperimento finale. |
| `requirements-dpo-pilot.txt`, `constraints-dpo-pilot.txt` | I pin sono già inclusi nel requirements di consegna. Eliminabili dopo avere aggiornato i messaggi dei trainer e i README che li indicano ancora. |

Il file attualmente aperto, **`constraints-dpo-pilot.txt`**, contiene i pin di
torch, transformers, datasets e accelerate già presenti in
`requirements-consegna-win-cu128.txt`. Non è letto dai trainer a runtime.
Il suo valore residuo è documentare la vecchia procedura di installazione.

## 4. Da conservare

### Corpus e RAG

- `data/raw/`: fonti originali per ricostruire il parsing.
- `data/processed/parsed/`: snapshot estratti, inclusi contenuti API che possono cambiare.
- `data/processed/chunks/`: input effettivo per l'indicizzazione e provenienza dei dati.
- `data/vector_db/`: database completo, comprese le sottocartelle UUID; serve alla demo già pronta.
- `src/ingest_api_data.py`, `src/parsing.py`, `src/chuncking.py`, `src/indexing.py`.
- `src/retrieval.py`, `src/generation.py`, `src/alignment.py`, `config.py`.

Catena verificata: `streamlit_app/backend.py` usa `AdvancedRetriever` e
`RAGGenerator.build_prompt`; `generation.py` importa `alignment.py` e `config.py`.
Il database è ricostruibile dai chunk, ma eliminarlo impone una nuova
indicizzazione e non garantisce identico stato binario dell'indice.

### Campagna finale in `experiments/dpo_pdf_600/`

- Tutto `dataset_consegna/`, incluso `source_snapshot.json`, `content.py`,
  `build.py`, provenienza e manifest. Anche `train_sft.jsonl` viene ricostruito
  ed è registrato nel pacchetto: il suo nome non basta a considerarlo spazzatura.
- `test_common_v1.json`, `test_common_v1_manifest.json`, `PROTOCOLLO_TEST_COMUNE.md`.
- `development_600_v1.json`, `development_600_v1_manifest.json` per la tracciabilità.
- I cinque trainer: `train_dpo_600.py`, `train_smollm3_600.py`,
  `train_gemma_600.py`, `train_llama_600.py`, `train_mistral_600.py`.
- I cinque `compare_test_*600.py` attuali: Qwen usa lo stesso script per 1.5B e 3B.
- `run_qwen15.ps1`, `run_smollm3.ps1`, `run_gemma.ps1`, `run_llama.ps1`, `run_mistral.ps1`.
- Tutti i sei `runs/*_train_v1/`, con adapter completi, tokenizer, revisioni,
  manifest, `result.json` e `training_history.json`.
- Le sei `evaluation/*_test_v1/`, inclusi record, chiavi e manifest.
- Tutta `evaluation/final_groq_v1/`, inclusi giudizi, riepiloghi e materiale per revisione.
- `evaluate_final_local.py`, **nonostante il nome**: implementa anche il giudice Groq finale.
- `run_final_evaluation.ps1`, `test_final_evaluation.py`, `VALUTAZIONE_FINALE.md`.
- `make_relation_charts.py`, `grafici_relazione/`, `make_charts_booklet.py`.
- `build_extended_report.py`, `relazione_approfondita/`.
- `streamlit_app/`, compresi test, launcher e istruzioni per reinstallare la UI.
- Documentazione delle differenze fra modelli e protocolli. `prepare_extra_families.py`
  è un generatore storico di varianti: piccolo e utile come provenienza, non da
  rilanciare per sovrascrivere gli script attuali.

### Installazione e trasferimento

- `requirements-consegna-win-cu128.txt`, `README_COLLEGA.md`, `TRASFERIMENTO_COLLEGA.md`.
- `scripts/download_demo_models.py`, `scripts/package_demo_assets.py`.
- `DEMO_ASSETS_MANIFEST.json`: verifica del trasferimento degli asset.
- `.git/`, `.gitignore`, `.gitattributes`: controllo di versione e regole del repository.

`.env` e `apikey.txt` non vanno inclusi nel pacchetto finale: sono configurazione
locale/credenziali, non spazzatura da cancellare automaticamente. Non ne è stato
letto il contenuto. I modelli base Hugging Face sono una dipendenza esterna alla
cartella del progetto; eliminarne la cache richiederebbe nuovi download.

## 5. Problemi preesistenti da risolvere prima di dichiarare la riproduzione completa

1. **Rigenerazione del test non autonoma.** `prepare_final_test.py:57` legge
   `dataset_v5/contexts_test.json` e, alle righe successive, gli analoghi file train
   e development. Tutti e tre sono assenti. Il test congelato conserva però i
   dieci brani originali, i contesti riformulati e gli 80 prompt. Usare il test
   congelato funziona; ricrearlo con questo preparatore, nello stato attuale, no.
   Rendere il preparatore indipendente dai vecchi tentativi prima di eliminare
   definitivamente i relativi riferimenti.
2. **Generazione di codice mescolata alla preparazione dei dati.** Il preparatore
   del test riscrive `compare_test_600.py` partendo da `compare_dpo_600.py`.
   La preparazione dello sviluppo legge un percorso assoluto del PC originario.
   Non usare questi preparatori per sovrascrivere alla cieca i sorgenti finali.
3. **Ambiente documentato e ambiente locale non identici.** I manifest dei training
   indicano Python 3.14.3. Entrambi i venv locali hanno `pyvenv.cfg` con Python 3.12.10.
   I metadati ML di `.venv-consegna` corrispondono ai pin principali, ma questo non
   dimostra una riproduzione numericamente identica né verifica l'intera demo GPU.
4. **Documentazione da consolidare.** Il README principale descrive ancora la CLI
   Ollama e contiene sezioni di sviluppo superate. Dopo la pulizia deve presentare
   la campagna finale, i comandi attuali e un'unica procedura di installazione.

## 6. Verifiche effettivamente eseguite

- Inventario della cartella di lavoro, inclusi file ignorati da Git e dimensioni dei venv.
- Nessun grafo `graphify-out/graph.json` presente: dipendenze verificate direttamente sui sorgenti.
- Lettura dei README, degli import Python e dei percorsi usati da dataset, trainer,
  confronti, giudice, grafici, relazioni e backend Streamlit.
- Validazione del training con `train_dpo_600.load_data`: **600 coppie, 75 domande**.
- Validazione dei dati di confronto per tutti i sei run: **80 prompt per modello**.
- Raccolta finale con `evaluate_final_local.collect`: **960 risposte**, sei modelli,
  controllo dei manifest e degli hash dei pesi adapter presenti.
- Ricostruzione di `dataset_consegna` in una cartella temporanea isolata, senza
  `dataset_v5`: **nessuna differenza nei byte dei file prodotti**.

Non sono stati eseguiti nuovi training, nuovi giudizi API, download, ricostruzione
del database o prove complete della demo su GPU. Le categorie di pulizia sono
basate su queste verifiche e sul perimetro confermato, non su una nuova replica
integrale dell'esperimento.
