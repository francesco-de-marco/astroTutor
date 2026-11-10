# AstroTutor – Adaptive Educational RAG System

This repository contains the source code for **AstroTutor**, an AI-powered educational assistant developed to provide astronomy explanations tailored to different levels of knowledge.

The project combines **Retrieval-Augmented Generation (RAG)**, semantic search, Large Language Models (LLMs), and **Direct Preference Optimization (DPO)** to generate context-grounded and educationally appropriate responses.

The main objective is to investigate how retrieval techniques and preference-based alignment can improve factual reliability, response quality, and adaptation to different educational audiences.

## 📄 Project Description

AstroTutor addresses the challenge of generating accurate and understandable explanations from heterogeneous educational resources, including scientific documents, textbooks, and educational websites.

The system supports four educational levels:

| Level | Target Audience |
|---|---|
| A | Children |
| B | Middle School Students |
| C | High School Students |
| D | University Students |

The architecture integrates several components:

1. **Document Processing:** Extraction and preprocessing of educational content from PDFs and public APIs.
2. **Semantic Retrieval:** Dense embeddings, vector search, and Cross-Encoder re-ranking.
3. **Retrieval-Augmented Generation:** Context-aware answer generation using locally hosted LLMs.
4. **Preference Alignment:** DPO-based fine-tuning to investigate improvements in response quality and educational adaptation.
5. **Evaluation:** Experimental comparison of baseline and aligned models using retrieval and generation quality metrics.

### Experimental Evaluation

The project investigates multiple configurations, including:

- **Baseline LLM:** Answer generation without external retrieval.
- **RAG:** Generation grounded in retrieved educational documents.
- **DPO-Aligned Models:** Preference-optimized variants of the base language model.
- **RAG + Aligned Models:** Evaluation of preference alignment within the retrieval-augmented pipeline.

The experimental workflow includes evaluations of answer quality, faithfulness to retrieved context, and behavior on out-of-domain questions.

Results, evaluation artifacts, and visualizations are organized in the `results/`, `experiments/`, and `report/` directories.

## 🧠 System Architecture

The AstroTutor pipeline consists of five main stages:

1. **Data Ingestion:** Educational content is collected from PDFs and public resources, including Vikidia and EduINAF.
2. **Processing and Chunking:** Documents are parsed with Docling, cleaned, and segmented into retrievable passages.
3. **Indexing:** Text passages are encoded using `BAAI/bge-m3` and stored in a ChromaDB vector database.
4. **Retrieval and Re-ranking:** Relevant passages are retrieved and reordered using `BAAI/bge-reranker-v2-m3`.
5. **Generation:** A locally hosted language model generates an answer conditioned on the retrieved context and the selected educational level.

Preference-based alignment is implemented through a separate DPO training pipeline using QLoRA.

## 📂 Repository Contents

The repository is organized into the following main components:

- `src/`: Core implementations for document processing, retrieval, generation, alignment, and evaluation.
- `data/`: Educational datasets, processed documents, training data, and retrieval artifacts.
- `models/`: Model configuration files and locally stored model artifacts.
- `experiments/`: Experimental configurations and outputs related to model alignment and evaluation.
- `results/`: Generated responses, evaluation metrics, and experimental results.
- `report/`: Project documentation, figures, and analysis.
- `main.py`: Interactive entry point for testing the RAG system.
- `compare.py`: Comparison between baseline LLM generation and retrieval-augmented generation.
- `config.py`: Centralized project configuration.
- `requirements.txt`: Python dependencies.
- `VERSIONI.md`: Detailed information about experimental environments, model versions, and reproducibility.

## 🚀 Technologies Used

- **Python** – Core implementation
- **PyTorch** – Deep Learning framework
- **Hugging Face Transformers** – Language models and training infrastructure
- **Sentence Transformers** – Dense embeddings and Cross-Encoder re-ranking
- **ChromaDB** – Vector database
- **Docling** – PDF document parsing
- **Ollama** – Local LLM inference
- **PEFT, TRL & bitsandbytes** – QLoRA and Direct Preference Optimization
- **RAGAS** – Evaluation of retrieval-augmented generation
- **Streamlit** – Interactive demonstration interface

## ⚙️ Installation

The consolidated dependency configuration targets Windows, Python 3.14, and an NVIDIA GPU compatible with the PyTorch CUDA 12.8 build.

Clone the repository:

```bash
git clone https://github.com/francesco-de-marco/astroTutor.git
cd astroTutor
```

Create a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install [Ollama](https://ollama.com/) and download the base language model:

```bash
ollama pull qwen2.5:3b
```

### Running AstroTutor

Launch the interactive RAG system:

```bash
python main.py
```

Compare baseline generation against RAG:

```bash
python compare.py
```

The retrieval pipeline requires an initialized knowledge base. Dataset preparation, indexing, and experimental reproduction procedures are documented in `VERSIONI.md`.

Some preprocessing, alignment, and evaluation workflows require additional datasets, model artifacts, or external API credentials.

## 👥 Authors

- **Francesco De Marco**
- **Mattia D'agostino**