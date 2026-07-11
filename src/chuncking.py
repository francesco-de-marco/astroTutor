"""
Text Chunker per RAG
Legge i JSON estratti in data/processed/parsed/ e genera file JSONL frammentati 
in data/processed/chunks/ pronti per l'embedding.
"""

import json
import os
import re
import sys
import time
import html
from bs4 import BeautifulSoup
from pathlib import Path

# Assicurati di aver installato: pip install langchain-text-splitters
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# ─── Configurazione ───────────────────────────────────────────────
# Il file si trova in src/chuncking.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARSED_DIR = PROJECT_ROOT / "data" / "processed" / "parsed"
CHUNKS_DIR = PROJECT_ROOT / "data" / "processed" / "chunks"

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
# Sotto questa soglia il chunk è rumore (didascalie, colophon, rating di copertina)
MIN_CHUNK_CHARS = 150

def clean_docling_markdown(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.DOTALL)
    text = re.sub(r'!\[.*?\]\(.*?\)', ' ', text)

    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(separator=" ")

    text = re.sub(
        r'([a-z0-9,;\-][\*_\"\'»”’]*)\s*\n+\s*([\*_\"\'«“‘]*[a-zA-Z0-9])',
        r'\1 \2', text
    )
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# ─── Logica di Chunking ───────────────────────────────────────────
def process_json_document(json_path: Path) -> list:
    """
    Legge un JSON parsato, lo divide in chunk semantici e pulisce il testo.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    markdown_text = data.get("text_markdown", "")

    # --- 1. PRE-PROCESSING: Pulizia HTML robusta e ricongiungimento righe PDF ---
    markdown_text = clean_docling_markdown(markdown_text)
    
    # Estraiamo i metadati base dal JSON (prendiamo solo il primo livello di difficoltà per semplicità)
    base_metadata = {
        "source_file": data.get("source_file"),
        "topic_id": data.get("topic_id"),
        "topic_name": data.get("topic_name"),
        "difficulty_level": data.get("difficulty_levels", [])[0] if data.get("difficulty_levels") else None,
        "difficulty_label": data.get("difficulty_labels", [])[0] if data.get("difficulty_labels") else None,
        "title": data.get("title")
    }

    # 1. Split Semantico (per titoli Markdown)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(markdown_text)

    # 2. Split Ricorsivo (se i blocchi sotto i titoli sono troppo lunghi)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    final_chunks = text_splitter.split_documents(md_header_splits)

    # 3. Assemblaggio e Pulizia
    processed_chunks = []
    for chunk in final_chunks:
        # Uniamo i metadati del documento con quelli generati dall'header splitter
        chunk_metadata = {**base_metadata, **chunk.metadata}
        
        # Pulizia post-split (già passata per clean_docling_markdown, togliamo solo spazi superflui)
        cleaned_content = chunk.page_content.strip()
        
        # Salviamo solo se c'è testo reale (scarta frammenti sotto la soglia minima)
        if len(cleaned_content) >= MIN_CHUNK_CHARS:
            processed_chunks.append({
                "content": cleaned_content,
                "metadata": chunk_metadata
            })

    return processed_chunks


# ─── Main ─────────────────────────────────────────────────────────
def main():
    if not PARSED_DIR.exists():
        print(f"Cartella di input non trovata: {PARSED_DIR}")
        sys.exit(1)

    # Trova tutti i JSON nella cartella parsed (e nelle sue sottocartelle)
    json_files = list(PARSED_DIR.rglob("*.json"))
    #json_files = [PARSED_DIR / "TOPIC 1 - Black Hole" / "B,C - Death by Black Hole And Other Cosmic Quandaries (Neil deGrasse Tyson).json"]
    
    if not json_files:
        print("Nessun JSON trovato in", PARSED_DIR)
        sys.exit(1)

    print(f"Trovati {len(json_files)} file JSON da frammentare.\n")

    success = 0
    errors = []
    total_chunks_generated = 0

    t0 = time.time()

    for idx, json_path in enumerate(json_files, 1):
        # Mantiene la struttura delle cartelle (es. TOPIC 1 - Black Hole)
        relative_path = json_path.relative_to(PARSED_DIR)
        
        out_path = CHUNKS_DIR / relative_path.with_suffix('.jsonl')
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        if out_path.exists():
            print(f"[{idx}/{len(json_files)}] SKIP (già chunkato): {json_path.name}")
            success += 1
            continue

        print(f"[{idx}/{len(json_files)}] Chunking di: {json_path.name} ...")

        try:
            t_start = time.time()
            chunks = process_json_document(json_path)
            
            # Salvataggio in formato JSONL (JSON Lines)
            with open(out_path, "w", encoding="utf-8") as f:
                for chunk in chunks:
                    # json.dumps converte il dizionario in stringa su una singola riga
                    f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

            elapsed = time.time() - t_start
            print(f"    ✓ Completato in {elapsed:.2f}s — Generati {len(chunks)} chunk")
            
            success += 1
            total_chunks_generated += len(chunks)

        except Exception as e:
            print(f"    ✗ ERRORE: {e}")
            errors.append((json_path.name, str(e)))

    # Riepilogo
    print(f"\n{'='*60}")
    print(f"Tempo totale: {time.time() - t0:.1f}s")
    print(f"File completati: {success}/{len(json_files)}")
    print(f"Chunk totali generati: {total_chunks_generated}")
    
    if errors:
        print(f"Errori: {len(errors)}")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print(f"Output salvati in: {CHUNKS_DIR}")

if __name__ == "__main__":
    main()