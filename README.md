# 🔭 AstroTutor – Adaptive Educational RAG & DPO System

![Project Status](https://img.shields.io/badge/Status-Completed-success)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.11%2Bcu128-orange)
![CUDA](https://img.shields.io/badge/CUDA-12.8-green)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B)
![VectorDB](https://img.shields.io/badge/VectorDB-ChromaDB-purple)
![HuggingFace](https://img.shields.io/badge/HuggingFace-TRL%20%7C%20PEFT-yellow)

**AstroTutor** is an educational astronomy assistant combining **Retrieval-Augmented Generation (RAG)** with **Direct Preference Optimization (DPO)**. The system dynamically tailors scientific explanations to four distinct target audiences:

| Level | Target Audience | Educational Stage |
|:---:|:---|:---|
| **A** | Primary School | Elementary fundamentals and intuitive analogies |
| **B** | Middle School | Conceptual clarity and introductory physics |
| **C** | High School | Quantitative concepts and scientific terminology |
| **D** | University | In-depth astrophysical rigor and mathematical formalisms |

The project features a full end-to-end pipeline: document parsing and hybrid retrieval over educational astronomy corpora, QLoRA-based DPO alignment across **six distinct LLM families**, an automated LLM-as-a-Judge evaluation framework on 960 answers, and an interactive **Streamlit** application with live retrieval and comparative generation.

---

## 🎯 Objectives

*   **Multi-Level Pedagogical Adaptation**: Dynamically adjust tone, depth, and vocabulary across four school tiers without hallucinating or losing core scientific accuracy.
*   **Hybrid Retrieval-Augmented Generation**: Combine BM25 lexical search, dense semantic search with `BAAI/bge-m3`, and cross-encoder reranking with `BAAI/bge-reranker-v2-m3` on specialized astronomy corpora (EduINAF, Vikidia, academic textbooks).
*   **Efficient DPO Alignment on Consumer Hardware**: Adapt open-source LLMs using QLoRA (NF4 double quantization with BF16 compute, LoRA rank 8) within the strict memory constraints of a single consumer GPU (**RTX 4070 Laptop, 8 GiB VRAM**).
*   **Systematic Multi-Model Benchmarking**: Empirically evaluate Base vs. DPO performance across six model architectures under identical frozen test contexts using an automated LLM-as-a-Judge (`openai/gpt-oss-120b`).
*   **End-to-End Interactive Prototyping**: Deliver a responsive Streamlit interface featuring live hybrid retrieval, side-by-side Base vs. DPO comparisons, and inspectable source attributions.

---

## 🧠 System Architecture

The project decouples knowledge extraction, retrieval, alignment training, and interactive serving:

```text
progetto_IR/
├── config.py                           # Global environment and model configuration
├── DEMO_ASSETS_MANIFEST.json           # SHA256 checksums of distributed assets
├── src/                                # Corpus ingestion, indexing, and retrieval
│   ├── parsing.py                      # Docling-based PDF parser
│   ├── chuncking.py                    # Multi-level hierarchical text chunker
│   ├── indexing.py                     # ChromaDB vector store builder (BAAI/bge-m3)
│   └── retrieval_eval.py               # Evaluation of BM25, dense search, and reranker
└── experiments/dpo_pdf_600/            # Final experimental suite
    ├── data/                           # Frozen datasets (600 train pairs, dev, test)
    ├── training/                       # QLoRA DPO trainers for all model families
    ├── evaluation/                     # Inference scripts and Groq judge client
    ├── demo/                           # Streamlit web application
    ├── launchers/                      # PowerShell scripts for automated workflows
    ├── reporting/                      # PDF/HTML report generators and matplotlib charts
    └── results/                        # Evaluation metrics, figures, and final report
```

### Key Modules
*   `src/parsing.py` & `src/chuncking.py`: Parse domain PDFs with Docling and apply structure-aware chunking preserving audience level metadata.
*   `src/indexing.py`: Embeds chunks into **ChromaDB** using `BAAI/bge-m3` with metadata filtering.
*   `experiments/dpo_pdf_600/training/`: Specialized trainers (`train_dpo_600.py`, `train_smollm3_600.py`, etc.) configuring TRL `DPOTrainer` with PEFT QLoRA.
*   `experiments/dpo_pdf_600/evaluation/`: Executes frozen test runs across 80 prompts and orchestrates automated grading with `openai/gpt-oss-120b`.
*   `experiments/dpo_pdf_600/demo/app.py`: Streamlit application serving real-time hybrid retrieval and dual Base/DPO model inference.

---

## 🚀 Installation

### Prerequisites
*   **OS**: Windows 11 / x64 (launchers formatted for PowerShell).
*   **Python**: 3.14.3 (recorded training environment).
*   **GPU**: NVIDIA RTX GPU with CUDA 12.8 support (minimum 8 GiB VRAM for BF16/NF4 execution).

### Setup
1. Clone the repository:
   ```powershell
   git clone https://github.com/francesco-de-marco/astroTutor.git
   cd astroTutor
   ```

2. Create a virtual environment and activate it:
   ```powershell
   py -3.14 -m venv .venv
   ./.venv/Scripts/Activate.ps1
   ```

3. Upgrade pip and install pinned dependencies:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   python -m pip check
   ```

4. Configure environment variables (optional for oracle evaluation):
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

> **Note on Assets**: Large artifacts (raw PDFs under `data/raw/`, pre-indexed ChromaDB in `data/vector_db/`, and fine-tuned LoRA adapters under `experiments/dpo_pdf_600/runs/`) must be present before running inference. Verify asset integrity against `DEMO_ASSETS_MANIFEST.json`.

---

## 💻 Usage

### 1. Interactive Streamlit Demo
Launch the web interface for real-time educational question answering:

```powershell
./experiments/dpo_pdf_600/launchers/run_app.ps1
```

Access the UI at `http://127.0.0.1:8501`. Features include:
*   Selection of audience level (**A**, **B**, **C**, **D**).
*   Generation mode: **Base Model**, **DPO Adapter**, or **Side-by-Side Comparison**.
*   Inspectable retrieved source passages with relevance and reranking scores.
*   Session history export to JSON.

---

### 2. DPO Training Pipeline
Train LoRA adapters for any of the six supported model families using the provided launchers:

| Model | Architecture | Parameters | Launcher |
|:---|:---|:---:|:---|
| `Qwen/Qwen2.5-1.5B-Instruct` | Qwen2 | 1.5B | `./experiments/dpo_pdf_600/launchers/run_qwen15.ps1 -Mode all` |
| `Qwen/Qwen2.5-3B-Instruct` | Qwen2 | 3.0B | Direct Python trainer (see below) |
| `HuggingFaceTB/SmolLM3-3B` | SmolLM3 | 3.0B | `./experiments/dpo_pdf_600/launchers/run_smollm3.ps1 -Mode all` |
| `google/gemma-3-1b-it` | Gemma3 | 1.0B | `./experiments/dpo_pdf_600/launchers/run_gemma.ps1 -Mode all` |
| `meta-llama/Llama-3.2-3B-Instruct` | Llama3 | 3.2B | `./experiments/dpo_pdf_600/launchers/run_llama.ps1 -Mode all` |
| `mistralai/Mistral-7B-Instruct-v0.3` | Mistral | 7.3B | `./experiments/dpo_pdf_600/launchers/run_mistral.ps1 -Mode all` |

To run training and evaluation directly for Qwen 2.5 3B:
```powershell
# Verify GPU stack
python experiments/dpo_pdf_600/training/train_dpo_600.py check

# Run DPO fine-tuning (QLoRA)
python experiments/dpo_pdf_600/training/train_dpo_600.py train --revision aa8e72537993ba99e69dfaafa59ed015b17504d1

# Generate test predictions
python experiments/dpo_pdf_600/evaluation/compare_test_600.py
```

---

### 3. Automated LLM-as-a-Judge Evaluation
Run the automated evaluation on the 960 test answers using Groq's `gpt-oss-120b`:

```powershell
./experiments/dpo_pdf_600/launchers/run_final_evaluation.ps1 -Mode all
./experiments/dpo_pdf_600/launchers/run_final_evaluation.ps1 -Mode summary
```

To regenerate the scientific figures and the complete technical report:
```powershell
python experiments/dpo_pdf_600/reporting/make_relation_charts.py
python experiments/dpo_pdf_600/reporting/build_extended_report.py
```

---

## 📊 Experimental Results

The benchmark evaluates **6 base models vs. their DPO adapters** over **80 frozen test prompts** (20 questions × 4 audience levels) producing **960 answers**:

1.  **Correctness Gains**: DPO fine-tuning increased the percentage of scientifically correct answers in **5 out of 6 models**, with the most substantial gains observed on smaller architectures (`gemma-3-1b-it` and `Qwen2.5-1.5B`).
2.  **Conciseness and Pacing**: Across all architectures, DPO-aligned models demonstrated a pronounced tendency toward more concise answers, filtering out unnecessary preamble and overly verbose introductory filler.
3.  **Pedagogical Adequacy**: Level adaptation showed conditioned improvements: high alignment on Level A (primary school analogies) and Level D (university rigor), with minor stylistic overlaps between Levels B and C.
4.  **Hardware Efficiency**: NF4 double quantization coupled with BF16 compute allowed training 7B parameter models (`Mistral-7B-Instruct-v0.3`) within **8 GiB VRAM**, maintaining peak memory below 7.2 GiB with gradient accumulation.
5.  **Retrieval Synergy**: Integrating `bge-reranker-v2-m3` on top of dense search delivered an average **+14.2% MRR** increase over baseline BM25 across multilingual queries.

---

## 👤 Authors

*   **Francesco De Marco**
*   **Attilio Mattia D'Agostino**

*Information Retrieval & Natural Language Processing Project — A.Y. 2025/2026*
