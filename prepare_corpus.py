# -*- coding: utf-8 -*-
"""
prepare_corpus.py — Ingestion del corpus con routing per tipo di documento
===========================================================================
Analizza ogni PDF in data/raw/TOPIC*/, lo classifica come BORN-DIGITAL o
SCANSIONE, e lo instrada al parser più adatto:

    born-digital  →  Docling      (estrazione nativa, veloce, header fedeli)
    scansione     →  GLM-OCR      (VLM, ottimo su scansioni/italiano/formule)

Output in data/processed/, con la stessa struttura a cartelle:
    <nome>.md          Markdown pronto per MarkdownHeaderTextSplitter
    <nome>.meta.json   metadati: topic, livelli, parser usato, statistiche
    manifest.json      riepilogo dell'intero corpus (nella radice di processed/)

Uso:
    python prepare_corpus.py --dry-run          # solo classificazione, nessun parsing
    python prepare_corpus.py                     # ingestion completa
    python prepare_corpus.py --only "TOPIC 7"    # filtra per cartella
    python prepare_corpus.py --force             # rigenera anche i .md esistenti

Requisiti:
    pip install pymupdf docling
    pip install glmocr            # solo se ci sono scansioni da processare
    # GLM-OCR via cloud: set ZHIPU_API_KEY=<chiave da open.bigmodel.cn>
    # oppure self-hosted: config.yaml con pipeline.maas.enabled=false (vedi README GLM-OCR)

Nota: questo script NON modifica i PDF originali né i file della pipeline
esistente; scrive solo in data/processed/.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    import fitz  # PyMuPDF — usato solo per la classificazione (leggero)
except ImportError:
    sys.exit("Manca PyMuPDF. Installa con: pip install pymupdf")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAZIONE CLASSIFICATORE
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_PAGES = 12          # pagine campionate per la classificazione
MIN_CHARS_PER_PAGE = 120   # sotto questa mediana di caratteri/pagina → scansione
MAX_GARBAGE_RATIO = 0.12   # oltre questa quota di caratteri "sporchi" → text layer inaffidabile

# Override manuali: se il classificatore sbaglia su un file specifico,
# aggiungi qui una parte del nome (case-insensitive).
FORCE_SCANNED: list[str] = []       # es. ["chiave segreta"]
FORCE_NATIVE:  list[str] = []       # es. ["Liwei_Hu_Tesi"]


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICAZIONE: born-digital vs scansione
# ─────────────────────────────────────────────────────────────────────────────
def classify_pdf(path: Path) -> dict:
    """
    Ritorna {"kind": "native"|"scanned", "reason": str, "pages": int, ...}

    Euristica:
    1. Campiona fino a SAMPLE_PAGES pagine distribuite nel documento.
    2. Se la mediana dei caratteri estratti per pagina è bassa → scansione
       (il testo "vero" non c'è: sono immagini di pagine).
    3. Se il testo c'è ma contiene troppi caratteri di controllo / replacement
       → text layer prodotto da un vecchio OCR di bassa qualità → trattalo
       come scansione (meglio rifare l'OCR con GLM-OCR che tenere il rumore).
    """
    name_low = path.name.lower()
    if any(k.lower() in name_low for k in FORCE_SCANNED):
        return {"kind": "scanned", "reason": "override manuale (FORCE_SCANNED)", "pages": None}
    if any(k.lower() in name_low for k in FORCE_NATIVE):
        return {"kind": "native", "reason": "override manuale (FORCE_NATIVE)", "pages": None}

    doc = fitz.open(path)
    n = doc.page_count
    step = max(1, n // SAMPLE_PAGES)
    idxs = list(range(0, n, step))[:SAMPLE_PAGES]

    chars_per_page, garbage_ratios = [], []
    for i in idxs:
        text = doc.load_page(i).get_text("text")
        clean = text.strip()
        chars_per_page.append(len(clean))
        if clean:
            garbage = sum(
                1 for c in clean
                if c == "\ufffd" or unicodedata.category(c).startswith("C") and c not in "\n\t\r"
            )
            garbage_ratios.append(garbage / len(clean))
    doc.close()

    chars_sorted = sorted(chars_per_page)
    median_chars = chars_sorted[len(chars_sorted) // 2] if chars_sorted else 0
    avg_garbage = sum(garbage_ratios) / len(garbage_ratios) if garbage_ratios else 0.0

    if median_chars < MIN_CHARS_PER_PAGE:
        kind, reason = "scanned", f"mediana {median_chars} caratteri/pagina (< {MIN_CHARS_PER_PAGE})"
    elif avg_garbage > MAX_GARBAGE_RATIO:
        kind, reason = "scanned", f"text layer sporco ({avg_garbage:.0%} caratteri anomali)"
    else:
        kind, reason = "native", f"mediana {median_chars} caratteri/pagina, testo pulito"

    return {"kind": kind, "reason": reason, "pages": n,
            "median_chars": median_chars, "garbage_ratio": round(avg_garbage, 4)}


# ─────────────────────────────────────────────────────────────────────────────
# METADATI dal percorso: topic dalla cartella, livelli dal prefisso del nome
# ─────────────────────────────────────────────────────────────────────────────
LEVEL_PREFIX_RE = re.compile(r"^([ABCD](?:\s*,\s*[ABCD])*)\s*-\s*")

def extract_metadata(pdf: Path, raw_root: Path) -> dict:
    topic = pdf.parent.name if pdf.parent != raw_root else "SENZA_TOPIC"
    m = LEVEL_PREFIX_RE.match(pdf.stem)
    levels = [x.strip() for x in m.group(1).split(",")] if m else []
    title = LEVEL_PREFIX_RE.sub("", pdf.stem).strip()
    return {"topic": topic, "levels": levels, "title": title, "source_pdf": pdf.name}


# ─────────────────────────────────────────────────────────────────────────────
# PARSER 1 — DOCLING (born-digital)
# ─────────────────────────────────────────────────────────────────────────────
_docling_converter = None

def parse_with_docling(pdf: Path) -> str:
    global _docling_converter
    if _docling_converter is None:
        from docling.document_converter import DocumentConverter
        _docling_converter = DocumentConverter()
    result = _docling_converter.convert(str(pdf))
    return result.document.export_to_markdown()


# ─────────────────────────────────────────────────────────────────────────────
# PARSER 2 — MINERU (nativi e/o scansioni, a scelta)
# ─────────────────────────────────────────────────────────────────────────────
def parse_with_mineru(pdf: Path, workdir: Path) -> str:
    """
    Invoca il CLI ufficiale `mineru` (stabile tra le versioni) e recupera il
    Markdown prodotto. MinerU rileva da solo se il PDF richiede OCR.
    Requisiti: pip install "mineru[all]"  (primo avvio: scarica i modelli)
    """
    if shutil.which("mineru") is None:
        raise ImportError("CLI 'mineru' non trovato — installa con: pip install \"mineru[all]\"")

    out_dir = workdir / pdf.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["mineru", "-p", str(pdf), "-o", str(out_dir)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"mineru exit {proc.returncode}: {proc.stderr.strip()[-300:]}")

    md_files = sorted(out_dir.rglob("*.md"))
    if not md_files:
        raise RuntimeError("MinerU non ha prodotto file .md (controlla output in " + str(out_dir) + ")")
    # in caso di più .md (varia con la versione), prendi il più grande
    best = max(md_files, key=lambda f: f.stat().st_size)
    return best.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# PARSER 3 — GLM-OCR (scansioni)
# ─────────────────────────────────────────────────────────────────────────────
def parse_with_glmocr(pdf: Path, workdir: Path) -> str:
    """
    Usa l'SDK ufficiale: parse() processa il PDF e save() esporta i risultati
    (incluso il Markdown) in una cartella; da lì recuperiamo il .md.
    Richiede ZHIPU_API_KEY (modalità cloud) o un config.yaml self-hosted.
    """
    from glmocr import parse  # import ritardato: serve solo se ci sono scansioni

    out_dir = workdir / pdf.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    result = parse(str(pdf))
    result.save(output_dir=str(out_dir))

    md_files = sorted(out_dir.rglob("*.md"))
    if md_files:
        parts = [f.read_text(encoding="utf-8") for f in md_files]
        return "\n\n".join(parts)

    # fallback: alcune versioni espongono il markdown come attributo
    for attr in ("markdown_result", "markdown", "md_result"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, str) and value.strip():
                return value
    raise RuntimeError("GLM-OCR non ha prodotto Markdown (controlla versione SDK/config)")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Ingestion corpus con routing Docling/GLM-OCR")
    ap.add_argument("--raw", default="data/raw", help="Cartella dei PDF (default: data/raw)")
    ap.add_argument("--dest", default="data/processed", help="Cartella output (default: data/processed)")
    ap.add_argument("--only", default=None, help="Processa solo cartelle il cui nome contiene questa stringa")
    ap.add_argument("--force", action="store_true", help="Rigenera anche i .md già esistenti")
    ap.add_argument("--dry-run", action="store_true", help="Solo classificazione e piano di routing, nessun parsing")
    ap.add_argument("--native-parser", choices=["docling", "mineru"], default="docling",
                    help="Parser per i PDF born-digital (default: docling)")
    ap.add_argument("--scan-parser", choices=["glmocr", "mineru"], default="glmocr",
                    help="Parser per le scansioni (default: glmocr)")
    args = ap.parse_args()

    raw_root, dest_root = Path(args.raw), Path(args.dest)
    if not raw_root.exists():
        sys.exit(f"Cartella non trovata: {raw_root.resolve()}")

    pdfs = sorted(raw_root.rglob("*.pdf"))
    if args.only:
        pdfs = [p for p in pdfs if args.only.lower() in p.parent.name.lower()]
    if not pdfs:
        sys.exit("Nessun PDF trovato con i filtri correnti.")

    print(f"\n{'═'*74}\n  INGESTION CORPUS — {len(pdfs)} PDF da {raw_root.resolve()}\n{'═'*74}\n")

    manifest, n_native, n_scanned = [], 0, 0
    done, skipped, failed = 0, 0, 0
    glmocr_workdir = dest_root / "_glmocr_tmp"

    # ── FASE 1: classificazione ──
    plan = []
    for pdf in pdfs:
        meta = extract_metadata(pdf, raw_root)
        try:
            cls = classify_pdf(pdf)
        except Exception as e:
            cls = {"kind": "native", "reason": f"classificazione fallita ({e}), default native", "pages": None}
        plan.append((pdf, meta, cls))
        if cls["kind"] == "native":
            n_native += 1
        else:
            n_scanned += 1
        tag = "NATIVO   → Docling" if cls["kind"] == "native" else "SCANSIONE→ GLM-OCR"
        lv = ",".join(meta["levels"]) or "?"
        print(f"  [{tag}] ({lv}) {meta['topic'][:22]:<22} {pdf.name[:60]}")
        print(f"            └─ {cls['reason']}")

    print(f"\n  Piano: {n_native} nativi (Docling) · {n_scanned} scansioni (GLM-OCR)")
    if args.dry_run:
        print("  Modalità --dry-run: nessun parsing eseguito.\n")
        return

    # ── FASE 2: parsing ──
    print(f"\n{'─'*74}\n  PARSING\n{'─'*74}")
    t0 = time.time()
    for pdf, meta, cls in plan:
        rel_dir = pdf.parent.relative_to(raw_root)
        out_dir = dest_root / rel_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / (pdf.stem + ".md")
        meta_path = out_dir / (pdf.stem + ".meta.json")

        if md_path.exists() and not args.force:
            print(f"  ↷ già presente: {md_path.name}")
            skipped += 1
            entry_status = "skipped"
        else:
            print(f"  ⚙ [{cls['kind']}] {pdf.name}")
            t_start = time.time()
            try:
                if cls["kind"] == "native":
                    if args.native_parser == "mineru":
                        md = parse_with_mineru(pdf, dest_root / "_mineru_tmp")
                        parser_used = "mineru"
                    else:
                        md = parse_with_docling(pdf)
                        parser_used = "docling"
                else:
                    if args.scan_parser == "mineru":
                        md = parse_with_mineru(pdf, dest_root / "_mineru_tmp")
                        parser_used = "mineru"
                    else:
                        md = parse_with_glmocr(pdf, glmocr_workdir)
                        parser_used = "glm-ocr"
                md_path.write_text(md, encoding="utf-8")
                n_headers = len(re.findall(r"^#{1,6}\s", md, flags=re.M))
                elapsed = time.time() - t_start
                print(f"    ✓ {len(md)//1000} kchar, {n_headers} header — {elapsed:.0f}s")
                meta_path.write_text(json.dumps({
                    **meta, "parser": parser_used, "classification": cls,
                    "chars": len(md), "headers": n_headers,
                    "processed_at": datetime.now().isoformat(timespec="seconds"),
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                done += 1
                entry_status = "ok"
            except ImportError as e:
                print(f"    ✗ dipendenza mancante: {e}")
                failed += 1
                entry_status = f"failed: {e}"
            except Exception as e:
                print(f"    ✗ errore: {type(e).__name__}: {e}")
                failed += 1
                entry_status = f"failed: {type(e).__name__}"

        manifest.append({**meta, "kind": cls["kind"], "status": entry_status,
                         "md": str(md_path.relative_to(dest_root))})

    dest_root.mkdir(parents=True, exist_ok=True)
    (dest_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'═'*74}\n  RIEPILOGO — {time.time()-t0:.0f}s totali")
    print(f"  ✓ processati: {done}   ↷ saltati: {skipped}   ✗ falliti: {failed}")
    print(f"  Manifest: {(dest_root / 'manifest.json').resolve()}\n")
    if failed and n_scanned:
        print("  Suggerimento: se i falliti sono scansioni, verifica che glmocr sia")
        print("  installato (pip install glmocr) e che ZHIPU_API_KEY sia impostata.\n")


if __name__ == "__main__":
    main()
