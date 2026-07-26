# AstroTutor — Versioni e riproducibilità

Fotografia completa degli ambienti con cui sono stati prodotti i risultati in
`data/`, `results/` e `report/figures/`. Data della fotografia: **26/07/2026**.

Tre ambienti distinti concorrono ai risultati e vanno tenuti separati:

| Ambiente | Cosa ci gira | Dove |
|---|---|---|
| **Locale** (Windows 11 + RTX 3050) | parsing, chunking, indicizzazione, retrieval, generazione, costruzione dataset DPO, analisi | `.venv` |
| **Colab L4** | training DPO (QLoRA) + merge + quantizzazione GGUF | `src/alignment_dpo_colab.ipynb` |
| **Colab GPU** | valutazione finale con giudice 14B | `src/evaluation_colab.ipynb` |

I file di dipendenze: `requirements.txt` (dipendenze dirette, ambiente locale) e
`requirements-lock.txt` (freeze completo del `.venv`, dipendenze transitive incluse).

---

## 1. Ambiente locale

| Componente | Versione |
|---|---|
| SO | Windows 11 Home 10.0.26200 |
| Python | 3.12.10 (`C:\Python312`, venv in `.venv`) |
| GPU | NVIDIA GeForce RTX 3050 Laptop (4 GB), driver 610.74 |
| PyTorch | 2.6.0+cu124 (CUDA 12.4, `torch.cuda.is_available() == True`) |
| Ollama | 0.32.1 |

Ricostruzione:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt          # dipendenze dirette
# oppure, per l'ambiente identico:
pip install --extra-index-url https://download.pytorch.org/whl/cu124 -r requirements-lock.txt
```

Serve inoltre un file `.env` nella root con la chiave dell'oracolo (non versionato):

```
ORACLE_BASE_URL=https://api.groq.com/openai/v1
ORACLE_API_KEY=<chiave>
ORACLE_MODEL=llama-3.3-70b-versatile
```

### Librerie principali (dalle versioni installate)

| Pacchetto | Versione | Usato da |
|---|---|---|
| docling | 2.86.0 | `src/parsing.py` |
| PyMuPDF | 1.27.2.2 | `src/parsing.py` (conteggio pagine) |
| requests | 2.33.1 | `src/ingest_api_data.py` |
| beautifulsoup4 | 4.14.3 | `src/chuncking.py`, `src/ingest_api_data.py` |
| langchain-text-splitters | 1.1.2 | `src/chuncking.py` |
| chromadb | 1.5.7 | `src/indexing.py`, `src/retrieval.py` |
| sentence-transformers | 5.4.1 | embedding + cross-encoder |
| transformers | 4.57.6 | backend di sentence-transformers |
| openai | 2.46.0 | client Ollama e Groq |
| ragas | 0.4.3 | `src/evaluation.py` (Faithfulness) |
| langchain-core / -openai / -community | 1.5.0 / 1.4.0 / 0.4.2 | dipendenze di ragas |
| instructor | 1.15.4 | structured output di ragas |
| matplotlib / numpy | 3.11.1 / 2.4.4 | `src/analysis.py` |
| python-dotenv | 1.2.2 | `config.py` |

BM25 (`src/retrieval_eval.py`) è implementato a mano: **nessuna** dipendenza tipo `rank_bm25`.

> `requirements-lock.txt` contiene anche pacchetti installati nel `.venv` ma non usati
> dal progetto (`marker-pdf`, `surya-ocr`, `langgraph`, `anthropic`, `tree-sitter*`,
> residui di esperimenti di parsing e di tooling): sono innocui, ma se si vuole un
> ambiente minimo bastano `requirements.txt`.

---

## 2. Modelli

### Modelli Hugging Face (scaricati automaticamente al primo uso)

| Modello | Ruolo | Riferimento nel codice |
|---|---|---|
| `BAAI/bge-m3` | embedding multilingua dei chunk e delle query | `src/indexing.py:18`, `src/retrieval.py:32`, `src/retrieval_eval.py:293` |
| `BAAI/bge-reranker-v2-m3` | cross-encoder di re-ranking | `src/retrieval.py:44`, `src/retrieval_eval.py:296` |
| `Qwen/Qwen2.5-3B-Instruct` | modello base del training DPO | `src/alignment_dpo_colab.ipynb`, cella 6 |

Nessuna revisione HF è fissata nel codice: il download prende il branch `main` del
repo del modello al momento dell'esecuzione. Per una riproducibilità stretta conviene
aggiungere `revision=<commit>` alle chiamate di caricamento.

### Modelli Ollama (locale, `ollama list` del 26/07/2026)

| Nome | ID | Dimensione | Ruolo |
|---|---|---|---|
| `qwen2.5:3b` | `357c53fb659c` | 1,9 GB | baseline e generatore RAG (`config.LLM_MODEL`), traduttore delle query |
| `qwen2.5:7b-instruct` | `845dbda0ea48` | 4,7 GB | giudice della run di valutazione **locale** (superata) |
| `astrotutor-dpo` | `78e05629f5ec` | 1,9 GB | DPO v1, 378 triplette (training 20-21/07, Kaggle) |
| `astrotutor-dpo-v2` | `10db0dce0e69` | 1,9 GB | DPO v2, 623 triplette (training 25/07, Colab L4) |
| `qwen2.5:14b-instruct` | — (solo su Colab) | ~9 GB Q4 | giudice della run di valutazione **finale** |

Gli altri modelli presenti nella cache locale (`llama3.1:8b`, `deepseek-r1`, `qwen3.5:9b`,
`qwen2.5:1.5b`) non fanno parte della pipeline.

Ricostruzione dei due modelli allineati dai GGUF in `models/`:

```bash
ollama pull qwen2.5:3b
cd models
ollama create astrotutor-dpo    -f Modelfile        # astrotutor-3b-dpo-Q4_K_M.gguf
ollama create astrotutor-dpo-v2 -f Modelfile.v2     # astrotutor-3b-dpo-v2-Q4_K_M.gguf
```

I `Modelfile` impostano il chat template di Qwen2.5 (`<|im_start|>` / `<|im_end|>`) e i
relativi stop token: senza di essi il modello quantizzato non chiude i turni.
I `.gguf` sono esclusi da git (`.gitignore`): vanno rigenerati dal notebook di training
o recuperati dal Drive del progetto.

### Oracolo per il dataset DPO

`llama-3.3-70b-versatile` via API Groq (`https://api.groq.com/openai/v1`), configurabile
da `.env`. Genera le risposte *chosen* delle triplette in `data/alignment_data.json`.

---

## 3. Ambiente Colab — training DPO (`src/alignment_dpo_colab.ipynb`)

**Runtime: GPU L4** (Ada, bf16 nativo; la T4 non è utilizzabile — niente bf16 —
e su >= 24 GB si può disattivare Liger). Picco di VRAM misurato: **11,03 GB**.

Installazione eseguita dal notebook (cella 4):

```bash
pip install -q -U trl peft bitsandbytes datasets accelerate transformers sentencepiece huggingface_hub liger-kernel
pip uninstall -q -y torchao     # Colab preinstalla 0.10, PEFT pretende > 0.16 e va in ImportError
```

⚠️ **Le versioni non sono fissate**: il notebook installa l'ultima disponibile al momento
dell'esecuzione, e le celle sono state salvate senza output, quindi le versioni esatte del
25/07/2026 non sono ricostruibili dal repository. L'unico vincolo registrato nei report è
**TRL 1.8** (in quella versione `max_prompt_length` è stato rimosso da `DPOConfig` e i
logits interi non vengono materializzati grazie a `use_liger_kernel=True`). Per rendere il
training ripetibile, la prima esecuzione futura dovrebbe salvare l'output di
`pip freeze | grep -E "trl|peft|bitsandbytes|transformers|torch|liger"` accanto ai risultati.

Anche `llama.cpp` (usato per convertire in GGUF e quantizzare in Q4_K_M) è clonato in
`--depth 1` da `https://github.com/ggml-org/llama.cpp` senza commit fissato.

### Iperparametri DPO (identici per v1 e v2)

| Parametro | Valore |
|---|---|
| modello base | `Qwen/Qwen2.5-3B-Instruct` |
| quantizzazione | 4-bit NF4, double quant, compute dtype bf16 |
| LoRA | r=16, alpha=32, dropout=0.05, bias none |
| target modules | q/k/v/o_proj, gate/up/down_proj |
| beta (DPO) | 0.1 |
| learning rate | 5e-6, scheduler cosine, warmup ratio 0.1 |
| epoche | 2 |
| batch | `per_device_train_batch_size=1` × `gradient_accumulation_steps=16` (effettivo 16) |
| eval batch | 1 (il default 8 causava OOM) |
| max_length | 3584 (massimo reale misurato ~3.020 token) |
| optimizer | `paged_adamw_8bit` |
| precision | bf16 |
| gradient checkpointing | attivo |
| `use_liger_kernel` | True; `precompute_ref_log_probs` **deve** restare False (incompatibile con Liger) |
| dataset | v1: 378 triplette · v2: 623 triplette (`data/alignment_data.json`) |

Output: adapter LoRA (~120 MB) → merge → GGUF f16 → quantizzazione Q4_K_M in `models/`.
Metriche per epoca in `data/training_metrics.json`, log v1 in `data/training_log_dpo_v1_378triplette.txt`.

---

## 4. Ambiente Colab — valutazione (`src/evaluation_colab.ipynb`)

Qui le versioni **sono** fissate (cella di installazione):

```bash
pip install -q "ragas==0.4.3" "langchain-core==1.5.0" "langchain-openai==1.4.0" \
               "langchain-community==0.4.2" "openai==2.46.0" "instructor==1.15.4" \
               chromadb sentence-transformers python-dotenv rank_bm25
curl -fsSL https://ollama.com/install.sh | sh      # Ollama: ultima release disponibile
```

`chromadb`, `sentence-transformers`, `python-dotenv` e `rank_bm25` restano non fissati; le
prime tre in locale sono rispettivamente 1.5.7, 5.4.1 e 1.2.2.

Configurazione della run finale (`results/eval_qwen2.5_14b-instruct_20260726_1039/run_meta.json`):

| Parametro | Valore |
|---|---|
| giudice | `qwen2.5:14b-instruct` |
| bracci | `qwen2.5:3b`, `astrotutor-dpo`, `astrotutor-dpo-v2` |
| generazione | `temperature=0.0`, `seed=42` (patchati in tutti e 4 i punti di chiamata di `generation.py`) |
| embedder / re-ranker | bge-m3 e cross-encoder su `cuda` |
| domande | 40 in dominio (10 per livello) + 20 OOD per braccio |
| `OLLAMA_MAX_LOADED_MODELS` | 2 |

Il notebook parte da uno `astrotutor.zip` del repo caricato su Drive e applica le patch
di configurazione via regex sui sorgenti: se `generation.py`, `evaluation.py` o
`retrieval.py` cambiano nelle righe interessate, le sostituzioni vanno riverificate
(il notebook stampa un avviso se non hanno effetto).

---

## 5. Ordine di esecuzione per riprodurre da zero

```bash
# 1. Ingestione e parsing            → data/processed/parsed/
python src/ingest_api_data.py                 # Vikidia (liv. A), EduINAF (liv. B)
python src/parsing.py                         # PDF liv. C/D con Docling

# 2. Chunking + indicizzazione       → data/vector_db/
python src/chuncking.py
python src/indexing.py                        # bge-m3 su ChromaDB

# 3. Uso interattivo / baseline
python main.py
python compare.py

# 4. Dataset di allineamento         → data/alignment_data.json
python src/alignment.py                       # triplette con oracolo Groq
python src/alignment_register.py              # variante di registro (stesso modello sui due lati)

# 5. Training DPO                    → models/*.gguf   [Colab L4]
#    src/alignment_dpo_colab.ipynb, celle 1-9

# 6. Valutazione                     → results/eval_*/  [Colab GPU]
#    src/evaluation_colab.ipynb  (oppure src/evaluation.py in locale, giudice 7B)

# 7. Valutazione del retrieval       → data/retrieval_eval*.json
python src/retrieval_eval.py

# 8. Grafici del report              → report/figures/
python src/analysis.py
```

## 6. Limiti noti di riproducibilità

- **Run di valutazione locale (23-25/07)**: `temperature=0.1` senza seed e contesti non
  salvati → non riproducibile e non ricostruibile a posteriori. È marcata come superata in
  `data/run_meta.json`; le conclusioni si basano sulla run Colab del 26/07.
- **Run Colab del 26/07**: `temperature=0`, `seed=42`, contesti e sorgenti salvati in ogni
  riga dei file di progresso → rigiudicabile senza rifare il retrieval. Resta il caveat
  registrato in `run_meta.json`: la colonna OOD di `eval_results.json` usa il match
  letterale della frase di rifiuto (`src/evaluation.py:77`) e misura conformità al
  template, non rifiuto reale.
- **Versioni del training DPO non registrate** (vedi §3): una ri-esecuzione del notebook
  installerà versioni più recenti di TRL/PEFT e potrebbe non riprodurre gli stessi pesi.
- **Modelli HF senza revision fissata**: un aggiornamento upstream di `bge-m3` o
  `bge-reranker-v2-m3` cambierebbe gli embedding e quindi il retrieval.
- **Sorgenti dati**: `data/raw/` (PDF) e `data/vector_db/` sono esclusi da git; le API
  pubbliche (Vikidia, EduINAF) restituiscono contenuti che possono cambiare nel tempo.
