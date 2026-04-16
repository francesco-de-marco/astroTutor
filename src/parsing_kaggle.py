# %%writefile parsing_kaggle_multi_gpu.py
"""
PDF Parser DUAL-GPU per Kaggle con Docling e Multiprocessing

Istruzioni per l'uso nel Kaggle Notebook:
1. Imposta l'Acceleratore su GPU T4 x2
2. Installa le librerie: !pip install docling PyMuPDF
3. Esegui questo script.
"""

import json
import os
import re
import sys
import time
import shutil
import gc
import multiprocessing as mp
from pathlib import Path

# ─── Configurazione per Kaggle ──────────────────────────────────
KAGGLE_INPUT_DIR = "/kaggle/input/datasets/francescodemarco7/rawfile/raw" 
KAGGLE_WORKING_DIR = "/kaggle/working/processed"

RAW_DIR = Path(KAGGLE_INPUT_DIR)
PROCESSED_DIR = Path(KAGGLE_WORKING_DIR)

LEVEL_MAP = {
    "A": "bambini",
    "B": "medie",
    "C": "superiori",
    "D": "universitari",
}

# ─── Utility ──────────────────────────────────────────────────────
def parse_filename(filename: str) -> dict:
    stem = Path(filename).stem
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


# ─── Processo Worker (Lavora su una singola GPU) ──────────────────
def worker_process(tasks, gpu_id):
    """
    Questa funzione viene eseguita in un processo separato.
    Vede SOLO la GPU che le viene assegnata.
    """
    # 1. Isola la GPU prima di importare PyTorch/Docling
    os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
    
    # 2. Importiamo qui dentro così PyTorch si inizializza nella GPU corretta
    import fitz
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat

    print(f"[GPU {gpu_id}] Avviata con {len(tasks)} PDF assegnati. Inizializzazione modelli...")
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.accelerator_options.num_threads = 2
    pipeline_options.ocr_batch_size = 2
    pipeline_options.do_formula_enrichment = True
    pipeline_options.do_ocr = True

    try:
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        print(f"[GPU {gpu_id}] Modelli caricati con successo!")
    except Exception as e:
        print(f"[GPU {gpu_id}] ERRORE INIZIALIZZAZIONE MODELLI: {e}")
        return

    success = 0
    
    for idx, task in enumerate(tasks, 1):
        pdf_path_str = task['pdf_path_str']
        pdf_name = task['pdf_name']
        print(f"[GPU {gpu_id}] ({idx}/{len(tasks)}) Inizio: {pdf_name}")
        
        try:
            t_start = time.time()
            
            with fitz.open(pdf_path_str) as doc:
                num_pages = len(doc)

            # --- CONVERSIONE A CHUNKS ---
            CHUNK_SIZE = 10
            text_chunks = []
            
            for start_page in range(1, num_pages + 1, CHUNK_SIZE):
                end_page = min(start_page + CHUNK_SIZE - 1, num_pages)
                print(f"[GPU {gpu_id}] -> Elaborando pagine {start_page}-{end_page}/{num_pages}...")
                
                conv_result = converter.convert(pdf_path_str, page_range=(start_page, end_page))
                text_chunks.append(conv_result.document.export_to_markdown())
                
                del conv_result
                gc.collect()
            
            text = "\n\n".join(text_chunks)
            elapsed = time.time() - t_start

            # Salvataggio
            result = {
                "source_file": task['source_file_name'],
                "topic_id": task['topic_info']["topic_id"],
                "topic_name": task['topic_info']["topic_name"],
                "difficulty_levels": task['file_info']["difficulty_levels"],
                "difficulty_labels": task['file_info']["difficulty_labels"],
                "title": task['file_info']["title"],
                "num_pages": num_pages,
                "text_markdown": text,
            }

            with open(task['out_path_str'], "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"[GPU {gpu_id}] ✓ Finito in {elapsed:.1f}s: {pdf_name}")
            success += 1
            
        except Exception as e:
            print(f"[GPU {gpu_id}] ✗ ERRORE su {pdf_name}: {e}")

    print(f"[GPU {gpu_id}] Processo terminato. {success}/{len(tasks)} completati.")


# ─── Main (Orchestratore) ─────────────────────────────────────────
def main():
    if not RAW_DIR.exists():
        print(f"ERRORE: Cartella {RAW_DIR} non trovata.")
        sys.exit(1)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = []
    # Ricerca ricorsiva dei PDF
    for parent_dir in RAW_DIR.iterdir():
        if parent_dir.is_dir():
            pdf_files.extend(list(parent_dir.glob("**/*.pdf")))
            
    if not pdf_files:
         print("Nessun PDF trovato in", RAW_DIR)
         sys.exit(1)
         
    tasks_to_run = []

    for pdf_path in pdf_files:
        topic_folder = pdf_path.parent.name
        topic_info = parse_topic_folder(topic_folder)
        file_info = parse_filename(pdf_path.name)

        out_dir = PROCESSED_DIR / topic_folder
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{pdf_path.stem}.json"
        
        if out_path.exists():
            continue
            
        tasks_to_run.append({
            'pdf_path_str': str(pdf_path),
            'topic_info': topic_info,
            'file_info': file_info,
            'out_path_str': str(out_path),
            'source_file_name': f"{topic_folder}/{pdf_path.name}",
            'pdf_name': pdf_path.name
        })

    print(f"Totale PDF da processare: {len(tasks_to_run)}")
    if not tasks_to_run:
        print("Tutti i file sono già stati processati!")
        return

    print("---------------------------------------------------------")
    print("AVVIO ELABORAZIONE PARALLELA (DUAL GPU T4 x2)            ")
    print("---------------------------------------------------------")

    t_start_all = time.time()

    # Dividiamo i task in due gruppi uguali per le due GPU
    mid_index = len(tasks_to_run) // 2
    tasks_gpu0 = tasks_to_run[:mid_index]
    tasks_gpu1 = tasks_to_run[mid_index:]

    processes = []

    # Avviamo il Processo per la GPU 0
    if tasks_gpu0:
        p0 = mp.Process(target=worker_process, args=(tasks_gpu0, 0))
        processes.append(p0)
        p0.start()

    # Avviamo il Processo per la GPU 1
    if tasks_gpu1:
        p1 = mp.Process(target=worker_process, args=(tasks_gpu1, 1))
        processes.append(p1)
        p1.start()

    # Aspettiamo che entrambe le GPU abbiano finito
    for p in processes:
        p.join()

    t_end_all = time.time() - t_start_all
    print(f"\n{'='*60}")
    print(f"TUTTI I PROCESSI COMPLETATI in {t_end_all / 60:.1f} minuti")

    # Creazione Archivio ZIP
    print("\nCreazione archivio .zip dei risultati in corso...")
    shutil.make_archive("/kaggle/working/processed_results", 'zip', PROCESSED_DIR)
    print("✓ Finito! Ora puoi scaricare 'processed_results.zip' dal pannello output.")

if __name__ == "__main__":
    # Necessario per il multiprocessing in Python
    mp.set_start_method('spawn', force=True)
    main()