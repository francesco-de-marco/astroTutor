# AstroTutor – Adaptive Educational RAG System

AstroTutor is an educational astronomy assistant that combines Retrieval-Augmented
Generation (RAG) with Direct Preference Optimization (DPO). It adapts explanations
to four educational levels:

| Level | Audience |
|---|---|
| A | Primary school |
| B | Middle school |
| C | High school |
| D | University |

The final experiment compares six base models with their DPO adapters on the same
frozen contexts. The Streamlit demo uses these adapters with live retrieval.

## Architecture and evaluation

The corpus includes astronomy PDFs and educational content from Vikidia and
EduINAF. Docling parses PDFs; the chunking pipeline splits the extracted content;
`BAAI/bge-m3` embeds passages in ChromaDB; `BAAI/bge-reranker-v2-m3` reranks
retrieved passages before answer generation.

The project has three distinct evaluation/use cases:

- **Final Base/DPO experiment:** 600 synthetic preference pairs for training
  (75 questions × 4 levels × 2 rejected answers), 32 development prompts and
  80 frozen test prompts. Six models × 2 conditions × 80 prompts produce
  **960 answers**. No live retrieval or response guardrails are used in this test.
- **Retrieval evaluation:** BM25, dense retrieval, reranking, query expansion and
  level bonus are compared using Recall@k, MRR and nDCG.
- **Live demo:** retrieves passages for a new question and generates a Base,
  DPO or side-by-side answer. Demo conversations are not additional test results.

The final saved judge is `openai/gpt-oss-120b` on Groq. Its scores are automated
estimates, not independent human validation. Repeated levels of the same question
are not independent observations.

## Repository structure

```text
progetto_IR/
├── README.md
├── requirements.txt
├── config.py
├── main.py                       # Original Ollama terminal interface
├── compare.py                    # Original comparison with/without retrieval
├── DEMO_ASSETS_MANIFEST.json      # Checksums of distributed adapters and index
├── src/                          # Corpus processing, retrieval and shared generation
├── data/                         # Corpus, Chroma index and retrieval evaluation
├── experiments/dpo_pdf_600/
│   ├── paths.py                  # Current paths and historical manifest compatibility
│   ├── data/                     # Frozen training, development and test data
│   ├── training/                 # DPO trainers
│   ├── evaluation/               # Base/DPO generation and judging scripts
│   ├── reporting/                # Chart and report generation
│   ├── demo/                     # Streamlit application
│   ├── launchers/                # PowerShell launchers
│   ├── tests/                    # Evaluation and UI tests
│   ├── runs/                     # Adapters, tokenizers, training manifests and logs
│   └── results/
│       ├── evaluation/           # Answers, judgments, scores and evaluation reports
│       ├── figures/              # Charts and provenance
│       └── reports/              # Detailed report: PDF, HTML and Markdown
├── models/                       # Outside the final experiment's adapter storage
├── results/                      # Outside the final experiment's result storage
└── report/                       # Original corpus/retrieval analysis
```

The final models and results are under `experiments/dpo_pdf_600/`, as shown above.
Training and evaluation manifests retain their original paths and hashes:
do not rewrite them when relocating the repository.

## Environment and installation

The six final training manifests record **Python 3.14.3**, **PyTorch
2.11.0+cu128**, CUDA build **12.8**, and an **NVIDIA GeForce RTX 4070 Laptop
GPU with 8 GiB VRAM**. Training and final model inference require CUDA/BF16.
The dependency configuration targets Windows x64; the report generator also
uses the Arial fonts in `C:/Windows/Fonts/`.

`requirements.txt` contains pinned packages, including the training versions
recorded in the manifests. It is a consolidated dependency list, not a complete
transitive lockfile. Installation of the whole consolidated environment has not
been verified on a clean machine or on CPU/macOS/Linux.

From the repository root, using Python 3.14.3 for the recorded training setup:

```powershell
py -3.14 -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

The Python executable, NVIDIA driver, model weights and corpus are not installed
by `requirements.txt`. Use a separate environment if an existing `.venv`
belongs to the earlier Python 3.12/CUDA 12.4 setup.

### Required assets

A source checkout alone does not include all runtime assets:

- Original PDFs under `data/raw/`, or the saved parsed documents/chunks.
- The populated Chroma index under `data/vector_db/`.
- Each final run's complete `adapter/` directory, including tokenizer files,
  plus `run_manifest.json` and `result.json`.
- The locally cached base models at the `revision` recorded in each run
  manifest, plus `BAAI/bge-m3` and `BAAI/bge-reranker-v2-m3`.

The model cache and large assets must be obtained separately. Configure Hugging
Face access where a model requires it. The demo loads weights from the local
cache and does not download missing models. `DEMO_ASSETS_MANIFEST.json` records
checksums of the distributed adapters and index; it is not a downloader.

## Reproduce the corpus and retrieval

Place PDFs in topic subdirectories under `data/raw/`, following the
level-prefixed filename convention read by `src/parsing.py`, then run:

```powershell
python src/ingest_api_data.py
python src/parsing.py
python src/chuncking.py
python src/indexing.py
```

These stages write parsed documents, chunks and the vector index. Reuse the
original corpus snapshot for comparisons: live websites and model repositories
can change. The encoder/reranker loading code does not pin a Hugging Face commit.

Retrieval evaluation uses `data/alignment_data.json` entries with
`source_chunk_file`, the processed chunks and the vector index:

```powershell
python src/retrieval_eval.py
```

It writes `data/retrieval_eval.json`, `retrieval_eval_meta.json` and
`retrieval_eval_details.jsonl`, reusing `query_translations.json`. Query
expansion requires the configured Ollama translator when translations are not
already cached. BM25 is implemented directly; `rank_bm25` is not required.

The reference labels are a document-level silver standard derived from source
chunks, not exhaustive human relevance annotations. `src/analysis.py` also
uses historical evaluation files; its plots are separate from the final
six-model charts.

## Reproduce the final DPO experiment

All following paths are relative to the repository root.

### Dataset

```powershell
python experiments/dpo_pdf_600/data/dataset_consegna/build.py
```

This reconstructs the training dataset offline from `source_snapshot.json`
and `content.py`. Keep the entire `dataset_consegna/` directory: its manifest
covers the source data, construction code and original documentation.
The development and test JSON files in `experiments/dpo_pdf_600/data/` are
separate frozen inputs and must be kept with their manifests; the training
build does not generate them.

### Models and training

| Base model | Trainer in `training/` | Launcher in `launchers/` |
|---|---|---|
| `Qwen/Qwen2.5-1.5B-Instruct` | `train_dpo_600.py` | `run_qwen15.ps1` |
| `Qwen/Qwen2.5-3B-Instruct` | `train_dpo_600.py` | Direct Python commands below |
| `HuggingFaceTB/SmolLM3-3B` | `train_smollm3_600.py` | `run_smollm3.ps1` |
| `google/gemma-3-1b-it` | `train_gemma_600.py` | `run_gemma.ps1` |
| `meta-llama/Llama-3.2-3B-Instruct` | `train_llama_600.py` | `run_llama.ps1` |
| `mistralai/Mistral-7B-Instruct-v0.3` | `train_mistral_600.py` | `run_mistral.ps1` |

Common saved settings: NF4 double quantization with BF16 compute; LoRA rank 8,
alpha 16, dropout 0 on q/k/v/o projections; DPO beta 0.1; learning rate 5e-6;
two epochs; batch size 1 with four accumulation steps; seed 42;
`adamw_torch`. The final runs have 300 optimizer steps and no validation set.
Sequence lengths and chat-template policies differ by model; their manifests
are the authoritative configuration.

For example, the Qwen 1.5B launcher supports `all`, `smoke`, `train`, `test`:

```powershell
./experiments/dpo_pdf_600/launchers/run_qwen15.ps1 -Mode all
```

The Qwen 3B direct commands are:

```powershell
python experiments/dpo_pdf_600/training/train_dpo_600.py check
python experiments/dpo_pdf_600/training/train_dpo_600.py smoke --revision aa8e72537993ba99e69dfaafa59ed015b17504d1
python experiments/dpo_pdf_600/training/train_dpo_600.py train --revision aa8e72537993ba99e69dfaafa59ed015b17504d1
python experiments/dpo_pdf_600/evaluation/compare_test_600.py --check-data
python experiments/dpo_pdf_600/evaluation/compare_test_600.py
```

The trainer's `check` requires the GPU stack; the comparison's `--check-data`
does not load a model. Trainers reject an already populated output directory.
For a new replica use a new `--output-dir`, pass its location to the comparison
with `--training-dir`, and choose a separate comparison `--output-dir`.
For every family, use the recorded base-model `revision` for strict reproduction;
launchers otherwise use the trainer's default revision resolution.

The final judge collects the six canonical `*_test_v1` result directories and
their matching `*_train_v1` runs. An independently named replica is not
automatically included in that aggregate.

`evaluation/compare_dpo_600.py` uses development prompts; `compare_test_*.py`
uses the frozen test. Historical API dataset-generation tools are still present
(`data/build_dataset.py`, `run_groq.ps1`, `run_rich_contexts.ps1`), but are
not part of this reproduction sequence and reference previous stages.

### Final judge and reports

```powershell
./experiments/dpo_pdf_600/launchers/run_final_evaluation.ps1 -Mode check
./experiments/dpo_pdf_600/launchers/run_final_evaluation.ps1 -Mode all
./experiments/dpo_pdf_600/launchers/run_final_evaluation.ps1 -Mode summary
```

The launcher selects Groq. `check` verifies inputs and prepares the evaluation;
`all` sends contexts and outstanding answers to the API; `summary` regenerates
reports from saved judgments. The launcher reads `ORACLE_API_KEY` from the
environment or requests it through hidden input. A standalone evaluator also
accepts `GROQ_API_KEY`. The launcher does not automatically load `.env`.

Results are stored in
`experiments/dpo_pdf_600/results/evaluation/final_groq_v1/`.
There are 952 unique judgments for 960 answers because identical answers to the
same prompt share a judgment. Keep individual judgments and records, not only
the summary.

To regenerate figures and the detailed report from saved results:

```powershell
python experiments/dpo_pdf_600/reporting/make_relation_charts.py
python experiments/dpo_pdf_600/reporting/make_charts_booklet.py
python experiments/dpo_pdf_600/reporting/build_extended_report.py
```

These commands write to `results/figures/` and `results/reports/` within the
experiment. They do not rerun training or inference.

## Streamlit demo

With the required assets and environment available:

```powershell
./experiments/dpo_pdf_600/launchers/run_app.ps1
```

Open `http://127.0.0.1:8501`. Select a model, level and Base/DPO/side-by-side
mode. Sources can be expanded and the session exported as JSON. Questions are
independent; the visible history is not conversational memory.

The comparison retrieves once and generates with the same adapter enabled or
disabled. Embedding/reranking run on CPU, one language model is loaded at a time,
and access to the GPU is serialized. The live demo uses the Italian query
without expansion or response guardrails. It requires no Groq key.
The results tab reads the saved scientific evaluation.

Optional path overrides: `ASTROTUTOR_REPO`, `ASTROTUTOR_EXPERIMENT_DIR`
(the `dpo_pdf_600` directory), and `ASTROTUTOR_DB_PATH`.
The launcher accepts `-Python <executable>` and `-Port <number>`.

## Checks

```powershell
python -B -m unittest discover -s experiments/dpo_pdf_600/tests -p "test_final_evaluation.py" -v
python -B experiments/dpo_pdf_600/tests/test_ui.py
```

Evaluation tests use temporary outputs and no API. The full integrity test
requires the original adapters; otherwise it is skipped. The UI test requires
Streamlit and uses the saved `demo/qa_live.json` response without model generation.

## Original pipeline and historical environments

The information previously in `VERSIONI.md` is consolidated here and in the
comments of `requirements.txt`. The earlier experiment is distinct from the
final six-model campaign:

| Historical stage (July 2026) | Recorded environment or setup |
|---|---|
| Local corpus/RAG work | Windows 11, Python 3.12.10, RTX 3050 Laptop 4 GB, driver 610.74, PyTorch 2.6.0+cu124, Ollama 0.32.1 |
| Earlier DPO training | Kaggle/Colab, including an L4 run; 378-pair v1 and 623-pair v2; merge and GGUF Q4_K_M export |
| Earlier final RAG evaluation | Colab, Ollama `qwen2.5:14b-instruct` judge; `qwen2.5:3b`, `astrotutor-dpo`, `astrotutor-dpo-v2`; 40 in-domain and 20 OOD questions per model |

The original terminal interfaces remain available with Ollama running:

```powershell
ollama pull qwen2.5:3b
python main.py
python compare.py
```

`compare.py` compares generation with and without retrieval.
`config.py` reads `.env` for `LLM_MODEL` and the optional oracle configuration
`ORACLE_BASE_URL`, `ORACLE_API_KEY`, `ORACLE_MODEL`. The historical oracle
was Groq's `llama-3.3-70b-versatile`; it generated chosen answers in
`data/alignment_data.json`. This oracle step is not needed to rebuild the
final frozen 600-pair dataset.

Earlier DPO settings included rank 16/alpha 32/dropout 0.05 on attention and MLP
projections, beta 0.1, learning rate 5e-6, cosine scheduling with 0.1 warmup,
two epochs, effective batch 16, max length 3584 and `paged_adamw_8bit`.
The L4 run used Liger with no precomputed reference log probabilities and
recorded a peak of 11.03 GB VRAM. Those settings do not describe the final adapters.

The old training notebook installed unpinned packages and cloned `llama.cpp`
without a recorded commit. Its full environment cannot be reconstructed from
the saved notes. A reported TRL 1.8 constraint was not backed by a complete
package freeze and is not an active requirement here. The old evaluation
recorded `langchain-community==0.4.2`; the current consolidated requirements
contain `0.3.31`, so they must not be treated as that historical environment.

Earlier local evaluation used temperature 0.1 without saved seeds/contexts;
the later July Colab run used temperature 0 and seed 42. Its OOD indicator
matched a fixed refusal string rather than measuring refusal quality.
Historical GGUFs, notebooks and their former commands are not prerequisites
for the final experiment documented above.

## Reproducibility limits

- Preserve corpus snapshots, model revisions, adapter/tokenizer files, run
  manifests and answer records. Seeds and package pins alone do not guarantee
  identical outputs on different hardware.
- Live source websites and unpinned encoder/reranker revisions can change.
- The cloud judge's implementation may change; saved judgments are the record
  of the completed evaluation.
- Training preferences are synthetic; neither the final judgments nor the demo
  have been independently validated with students.
- Reports and saved manifests may contain historical paths. Their contents
  describe the original runs and should not be edited just to match a new layout.

## Authors

- **Francesco De Marco**
- **Attilio Mattia D'agostino**
