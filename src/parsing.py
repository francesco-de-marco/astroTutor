"""
PDF Parser con Docling (Versione Locale)
Estrae testo da tutti i PDF in data/raw/ e salva JSON strutturati in data/processed/.
Risolve problemi di layout complesso, note a margine e decodifica delle formule in LaTeX.
"""

import json
import os
import re
import sys
import time
import gc  # Necessario per gestire aggressivamente la RAM in locale
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

# ─── Configurazione ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "parsed"

LEVEL_MAP = {
    "A": "bambini",
    "B": "medie",
    "C": "superiori",
    "D": "universitari",
}

# ─── Utility ──────────────────────────────────────────────────────
def parse_filename(filename: str) -> dict:
    stem = Path(filename).stem  # rimuovi .pdf
    match = re.match(r"^([A-D](?:\s*,\s*[A-D])*)\s*-\s*(.+)$", stem)
    if match:
        levels_str = match.group(1)
        title = match.group(2).strip()
        levels = [l.strip() for l in levels_str.split(",")]
    else:
        levels = ["unknown"]
        title = stem

    return {
        "difficulty_levels": levels,
        "difficulty_labels": [LEVEL_MAP.get(l, "sconosciuto") for l in levels],
        "title": title,
    }

def parse_topic_folder(folder_name: str) -> dict:
    match = re.match(r"^TOPIC\s+(\d+)\s*-\s*(.+)$", folder_name)
    if match:
        return {
            "topic_id": int(match.group(1)),
            "topic_name": match.group(2).strip(),
        }
    return {"topic_id": 0, "topic_name": folder_name}

# ─── Main ─────────────────────────────────────────────────────────
def main():
    # Trova dinamicamente tutti i PDF nelle cartelle
    pdf_files = []
    if not RAW_DIR.exists():
        print(f"ERRORE: Cartella non trovata: {RAW_DIR}")
        sys.exit(1)

    for topic_folder in sorted(RAW_DIR.iterdir()):
        if not topic_folder.is_dir():
            continue
        for pdf_path in sorted(topic_folder.glob("*.pdf")):
            pdf_files.append(pdf_path)
            
    if not pdf_files:
        print("Nessun PDF trovato in", RAW_DIR)
        sys.exit(1)

    print(f"Trovati {len(pdf_files)} PDF da processare.\n")

    # --- INIZIALIZZAZIONE DOCLING ---
    print("Caricamento modelli Docling...")
    t0 = time.time()

    # 1. Creiamo le opzioni della pipeline
    pipeline_options = PdfPipelineOptions()
    
    # Riduciamo l'uso della RAM per evitare Out of Memory / std::bad_alloc
    pipeline_options.accelerator_options.num_threads = 2
    pipeline_options.ocr_batch_size = 2
    
    # 2. ACCENDIAMO IL TRADUTTORE DELLE FORMULE E OCR
    pipeline_options.do_formula_enrichment = True
    pipeline_options.do_ocr = True
    
    # 3. Inizializziamo il convertitore passando le nostre opzioni per i PDF
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    print(f"Modelli caricati in {time.time() - t0:.1f}s\n")

    success = 0
    errors = []

    for idx, pdf_path in enumerate(pdf_files, 1):
        topic_folder = pdf_path.parent.name
        topic_info = parse_topic_folder(topic_folder)
        file_info = parse_filename(pdf_path.name)

        out_dir = PROCESSED_DIR / topic_folder
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{pdf_path.stem}.json"

        if out_path.exists():
            print(f"[{idx}/{len(pdf_files)}] SKIP (già processato): {pdf_path.name}")
            success += 1
            continue

        print(f"[{idx}/{len(pdf_files)}] Processando: {pdf_path.name} ...")

        try:
            t_start = time.time()
            
            # Conta pagine dal documento (usiamo fitz/PyMuPDF che è velocissimo)
            import fitz
            with fitz.open(str(pdf_path)) as doc:
                num_pages = len(doc)

            # --- CONVERSIONE CON DOCLING (A CHUNKS) ---
            # Elaboriamo il documento a blocchi per svuotare la RAM ed evitare crash locali
            CHUNK_SIZE = 10
            text_chunks = []
            
            for start_page in range(1, num_pages + 1, CHUNK_SIZE):
                end_page = min(start_page + CHUNK_SIZE - 1, num_pages)
                print(f"      - Processando pagine {start_page}-{end_page} su {num_pages}...")
                
                # 1. Analizza un blocco del documento
                conv_result = converter.convert(str(pdf_path), page_range=(start_page, end_page))
                
                # 2. Salva il markdown di questo blocco
                text_chunks.append(conv_result.document.export_to_markdown())
                
                # 3. Pulisci per liberare la memoria RAM
                del conv_result
                gc.collect()  # Svuota fisicamente la RAM
            
            text = "\n\n".join(text_chunks)
            elapsed = time.time() - t_start

            # Costruisci JSON
            result = {
                "source_file": str(pdf_path.relative_to(PROJECT_ROOT)),
                "topic_id": topic_info["topic_id"],
                "topic_name": topic_info["topic_name"],
                "difficulty_levels": file_info["difficulty_levels"],
                "difficulty_labels": file_info["difficulty_labels"],
                "title": file_info["title"],
                "num_pages": num_pages,
                "text_markdown": text,
            }

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"    ✓ Completato in {elapsed:.1f}s — {num_pages} pagine")
            success += 1

        except Exception as e:
            print(f"    ✗ ERRORE: {e}")
            errors.append((pdf_path.name, str(e)))

    print(f"\n{'='*60}")
    print(f"Completati: {success}/{len(pdf_files)}")
    if errors:
        print(f"Errori: {len(errors)}")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print(f"Output salvati in: {PROCESSED_DIR}")

if __name__ == "__main__":
    main()