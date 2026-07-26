"""Valutazione IR del retrieval (todo #1/#2) — Recall@k, MRR, nDCG + ablazione.

GOLD SET (silver standard, granularità DOCUMENTO)
  Le triplette di data/alignment_data.json con `source_chunk_file` valorizzato
  sono quelle la cui domanda è stata generata DA un chunk specifico (pipeline
  precedente al 23/07): il PDF d'origine è il documento rilevante. Le altre
  triplette non sono usabili come gold: la domanda nasce dal topic e il campo
  `sources` è l'output del retriever stesso — usarlo come verità misurerebbe
  l'auto-accordo del sistema, non la sua qualità.
  I valori assoluti vanno letti come limite inferiore (una domanda può avere
  risposta anche in file diversi da quello d'origine): conta il confronto
  fra configurazioni, non il numero in sé.

CONFIGURAZIONI (cumulative, stessa pool di livello con fallback per tutte)
  BM25                 baseline lessicale, sola query italiana
  BM25 + expansion     query ITA+EN concatenate: separa "il lessicale fallisce"
                       da "il lessicale fallisce per la lingua" (corpus in gran
                       parte inglese, query in italiano)
  solo bi-encoder      bge-m3 denso, sola query italiana, rank per distanza
  + re-ranker          top-k densi riordinati dal cross-encoder
  + query expansion    variante EN da traduttore FISSO (todo #15), unione, re-rank
  + bonus livello      pipeline di produzione (EXACT_LEVEL_BONUS sul livello esatto)

OUTPUT
  data/retrieval_eval.json           schema atteso da analysis.py (grafici 7-8)
  data/retrieval_eval_meta.json      provenienza gold, breakdown per livello
  data/retrieval_eval_details.jsonl  rank del documento gold per query × config
  data/query_translations.json       cache delle traduzioni (riusata fra i run)

USO
  python src/retrieval_eval.py                  run completa
  python src/retrieval_eval.py --limit 5        smoke test
  python src/retrieval_eval.py --reranker-device cpu
"""

import argparse
import json
import math
import re
import time
from collections import defaultdict
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder

try:
    from src.retrieval import LEVEL_FALLBACK, EXACT_LEVEL_BONUS
except ImportError:
    from retrieval import LEVEL_FALLBACK, EXACT_LEVEL_BONUS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHUNKS_DIR = DATA_DIR / "processed" / "chunks"
DB_PATH = DATA_DIR / "vector_db"
ALIGNMENT_PATH = DATA_DIR / "alignment_data.json"
TRANSLATIONS_PATH = DATA_DIR / "query_translations.json"
OUT_METRICS = DATA_DIR / "retrieval_eval.json"
OUT_META = DATA_DIR / "retrieval_eval_meta.json"
OUT_DETAILS = DATA_DIR / "retrieval_eval_details.jsonl"

KS = [1, 3, 5, 10, 20]
DEPTH = 20          # profondità della lista di documenti valutata
NDCG_CUT = 10
INITIAL_K = 20      # candidati densi per variante di query

CONFIGS = ["BM25", "BM25 + expansion", "solo bi-encoder", "+ re-ranker",
           "+ query expansion", "+ bonus livello"]


def norma_path(p: str) -> str:
    return p.replace("\\", "/").strip()


# ── Gold set ───────────────────────────────────────────────────────
def load_gold(limit=None):
    gold, seen = [], set()
    with open(ALIGNMENT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            src = d.get("source_chunk_file")
            if not src or d["strategy"] == "ood":
                continue
            key = (d["question"], d["user_level"])
            if key in seen:
                continue
            seen.add(key)
            gold.append({
                "question": d["question"],
                "level": d["user_level"],
                "gold_file": norma_path(src),
            })
    if limit:
        gold = gold[:limit]
    return gold


# ── Corpus e BM25 ──────────────────────────────────────────────────
def tokenize(text: str) -> list:
    return re.findall(r"\w+", text.lower())


def load_chunks():
    """Stessi .jsonl indicizzati da indexing.py: testo + source_file + livello."""
    chunks = []
    for fp in sorted(CHUNKS_DIR.rglob("*.jsonl")):
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                m = c["metadata"]
                chunks.append({
                    "text": c["content"],
                    "source_file": norma_path(m.get("source_file", "")),
                    "level": m.get("difficulty_level"),
                })
    return chunks


class BM25:
    """Okapi BM25 minimale su indice invertito, senza dipendenze esterne.
    L'IDF è calcolato sull'intero corpus anche quando la pool è ristretta
    dal filtro di livello: approssimazione dichiarata, identica per tutte
    le query, quindi ininfluente sul confronto fra configurazioni."""

    def __init__(self, docs_tokens, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.doc_len = [len(t) for t in docs_tokens]
        self.avgdl = sum(self.doc_len) / max(len(self.doc_len), 1)
        self.postings = defaultdict(list)   # term -> [(doc_id, tf)]
        for i, toks in enumerate(docs_tokens):
            tf = defaultdict(int)
            for t in toks:
                tf[t] += 1
            for t, n in tf.items():
                self.postings[t].append((i, n))
        self.n_docs = len(docs_tokens)
        self.idf = {
            t: math.log(1 + (self.n_docs - len(p) + 0.5) / (len(p) + 0.5))
            for t, p in self.postings.items()
        }

    def search(self, query: str, allowed: set, k: int) -> list:
        """Restituisce [(doc_id, score)] limitato ai doc_id in `allowed`."""
        scores = defaultdict(float)
        for t in tokenize(query):
            if t not in self.postings:
                continue
            idf = self.idf[t]
            for doc_id, tf in self.postings[t]:
                if doc_id not in allowed:
                    continue
                dl = self.doc_len[doc_id]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                scores[doc_id] += idf * tf * (self.k1 + 1) / denom
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:k]


# ── Traduzioni (todo #15: traduttore FISSO, non il modello valutato) ─
def load_translations():
    if TRANSLATIONS_PATH.exists():
        return json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    return {}


def build_translations(questions, model):
    """Genera (una sola volta) la variante EN di ogni domanda con un modello
    fisso via Ollama e la salva in cache. Ritorna None se Ollama non risponde:
    in quel caso le due configurazioni con expansion vengono saltate."""
    cache = load_translations()
    missing = [q for q in questions if q not in cache]
    if not missing:
        return cache

    try:
        from openai import OpenAI
        client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        # stesso prompt di generation.py:_translate_query, ma modello fisso
        # e temperature=0.0 per una cache deterministica
        for i, q in enumerate(missing, 1):
            prompt = (
                "Sei un traduttore automatico di altissima precisione.\n"
                "Regole:\n"
                "- Se la frase fornita è in ITALIANO, traducila in INGLESE.\n"
                "- Se la frase fornita è in INGLESE, traducila in ITALIANO.\n"
                "- Rispondi ESCLUSIVAMENTE con la traduzione. Non aggiungere "
                "virgolette, non dire 'Ecco la traduzione:' e non aggiungere "
                "note.\n\n"
                f"Frase: {q}"
            )
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            cache[q] = resp.choices[0].message.content.strip()
            if i % 10 == 0 or i == len(missing):
                print(f"  traduzioni: {i}/{len(missing)}")
                TRANSLATIONS_PATH.write_text(
                    json.dumps(cache, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    except Exception as e:
        print(f"  ATTENZIONE: traduzione non disponibile ({e}).")
        print("  Le configurazioni con query expansion verranno saltate.")
        return None

    TRANSLATIONS_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache


# ── Metriche (a livello di DOCUMENTO) ──────────────────────────────
def doc_ranking(ranked_chunks) -> list:
    """Collassa una lista ordinata di chunk nella lista ordinata dei
    documenti distinti (prima occorrenza)."""
    out, seen = [], set()
    for src in ranked_chunks:
        if src not in seen:
            seen.add(src)
            out.append(src)
    return out


def gold_rank(doc_list, gold_file):
    for i, src in enumerate(doc_list[:DEPTH], 1):
        if src == gold_file:
            return i
    return None


def aggregate(ranks):
    n = len(ranks)
    rec = {str(k): sum(1 for r in ranks if r and r <= k) / n for k in KS}
    mrr = sum(1 / r for r in ranks if r) / n
    ndcg = sum(1 / math.log2(1 + r) for r in ranks if r and r <= NDCG_CUT) / n
    return {"recall_at_k": rec, "mrr": round(mrr, 4),
            "ndcg": round(ndcg, 4), "n_queries": n}


# ── Run ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=None,
                    help="valuta solo le prime N query (smoke test)")
    ap.add_argument("--translator-model", default="qwen2.5:3b",
                    help="modello Ollama FISSO per la variante EN (todo #15)")
    ap.add_argument("--reranker-device", default=None,
                    choices=["cuda", "cpu"],
                    help="default: cuda se disponibile, altrimenti cpu")
    args = ap.parse_args()

    gold = load_gold(args.limit)
    per_liv = defaultdict(int)
    for g in gold:
        per_liv[g["level"]] += 1
    print(f"Gold set: {len(gold)} query "
          f"(A {per_liv['A']} / B {per_liv['B']} / C {per_liv['C']} / D {per_liv['D']})")

    print("Carico i chunk...")
    chunks = load_chunks()
    file_presenti = {c["source_file"] for c in chunks}
    orfane = [g for g in gold if g["gold_file"] not in file_presenti]
    if orfane:
        print(f"  ATTENZIONE: {len(orfane)} query hanno un gold non piu' nel "
              "corpus (fonte rimossa nella pulizia duplicati): escluse.")
        gold = [g for g in gold if g["gold_file"] in file_presenti]

    print(f"Costruisco BM25 su {len(chunks)} chunk...")
    bm25 = BM25([tokenize(c["text"]) for c in chunks])
    ids_per_livello = defaultdict(set)
    for i, c in enumerate(chunks):
        ids_per_livello[c["level"]].add(i)

    translations = build_translations(
        [g["question"] for g in gold], args.translator_model)

    if args.reranker_device is None:
        try:
            import torch
            args.reranker_device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            args.reranker_device = "cpu"
    print(f"Carico bge-m3 (cpu, 1-2 query corte) e re-ranker "
          f"({args.reranker_device})...")
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-m3", device="cpu")
    collection = chromadb.PersistentClient(path=str(DB_PATH)).get_collection(
        name="rag_knowledge_base", embedding_function=ef)
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3",
                            device=args.reranker_device)

    ranks = {c: [] for c in CONFIGS}
    ranks_per_liv = {c: defaultdict(list) for c in CONFIGS}
    details = open(OUT_DETAILS, "w", encoding="utf-8")
    t0 = time.time()

    for qi, g in enumerate(gold, 1):
        q, level, gold_file = g["question"], g["level"], g["gold_file"]
        accepted = LEVEL_FALLBACK[level]
        pool = set().union(*(ids_per_livello[l] for l in accepted))
        row = {"question": q, "level": level, "gold_file": gold_file}

        # BM25 (sola query italiana, stessa pool di livello)
        bm_docs = doc_ranking(
            [chunks[i]["source_file"] for i, _ in bm25.search(q, pool, 200)])
        row["BM25"] = gold_rank(bm_docs, gold_file)

        # denso, sola query ITA: candidati condivisi da "solo bi-encoder"
        # e "+ re-ranker"
        where = {"difficulty_level": {"$in": accepted}}
        res = collection.query(query_texts=[q], n_results=INITIAL_K,
                               where=where,
                               include=["metadatas", "documents", "distances"])
        cand_ita = [
            {"text": t, "source": norma_path(m.get("source_file", "")),
             "level": m.get("difficulty_level"), "dist": d}
            for t, m, d in zip(res["documents"][0], res["metadatas"][0],
                               res["distances"][0])
        ]
        row["solo bi-encoder"] = gold_rank(
            doc_ranking([c["source"] for c in cand_ita]), gold_file)

        sc_ita = reranker.predict([[q, c["text"]] for c in cand_ita])
        rr = sorted(zip(cand_ita, sc_ita), key=lambda x: x[1], reverse=True)
        row["+ re-ranker"] = gold_rank(
            doc_ranking([c["source"] for c, _ in rr]), gold_file)

        # con expansion: unione ITA+EN, punteggi del re-ranker calcolati una
        # volta e riusati per la variante con bonus di livello
        if translations is not None:
            row["BM25 + expansion"] = gold_rank(doc_ranking(
                [chunks[i]["source_file"] for i, _ in
                 bm25.search(q + " " + translations[q], pool, 200)]),
                gold_file)
            res2 = collection.query(
                query_texts=[q, translations[q]], n_results=INITIAL_K,
                where=where, include=["metadatas", "documents"])
            uniti, visti = list(cand_ita), {c["text"] for c in cand_ita}
            for docs, metas in zip(res2["documents"], res2["metadatas"]):
                for t, m in zip(docs, metas):
                    if t not in visti:
                        visti.add(t)
                        uniti.append({
                            "text": t,
                            "source": norma_path(m.get("source_file", "")),
                            "level": m.get("difficulty_level")})
            nuovi = uniti[len(cand_ita):]
            sc_nuovi = (reranker.predict([[q, c["text"]] for c in nuovi])
                        if nuovi else [])
            sc_uniti = list(sc_ita) + list(sc_nuovi)

            exp = sorted(zip(uniti, sc_uniti), key=lambda x: x[1], reverse=True)
            row["+ query expansion"] = gold_rank(
                doc_ranking([c["source"] for c, _ in exp]), gold_file)

            bon = sorted(
                zip(uniti, sc_uniti),
                key=lambda x: x[1] + (EXACT_LEVEL_BONUS
                                      if x[0]["level"] == level else 0.0),
                reverse=True)
            row["+ bonus livello"] = gold_rank(
                doc_ranking([c["source"] for c, _ in bon]), gold_file)

        for c in CONFIGS:
            if c in row:
                ranks[c].append(row[c])
                ranks_per_liv[c][level].append(row[c])
        details.write(json.dumps(row, ensure_ascii=False) + "\n")

        if qi % 10 == 0 or qi == len(gold):
            print(f"  {qi}/{len(gold)}  ({time.time() - t0:.0f}s)")

    details.close()

    metrics = {c: aggregate(r) for c, r in ranks.items() if r}
    OUT_METRICS.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")

    meta = {
        "_nota": ("Gold set silver-standard a granularita' di DOCUMENTO: "
                  "triplette di alignment_data.json con source_chunk_file "
                  "(domanda generata da un chunk di quel file). Le triplette "
                  "topic-based sono escluse perche' il loro campo sources e' "
                  "l'output del retriever stesso (circolare)."),
        "data": time.strftime("%Y-%m-%d %H:%M"),
        "n_query": len(gold),
        "query_per_livello": dict(per_liv),
        "query_escluse_gold_rimosso": len(orfane),
        "traduttore": (args.translator_model if translations is not None
                       else "NON DISPONIBILE (expansion saltata)"),
        "reranker_device": args.reranker_device,
        "initial_k": INITIAL_K, "profondita": DEPTH, "ndcg_cut": NDCG_CUT,
        "recall_at_3_per_livello": {
            c: {l: round(sum(1 for r in rs if r and r <= 3) / len(rs), 3)
                for l, rs in sorted(ranks_per_liv[c].items())}
            for c in CONFIGS if ranks[c]},
    }
    OUT_META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{'Configurazione':<20} {'R@1':>6} {'R@3':>6} {'R@5':>6} "
          f"{'R@10':>6} {'R@20':>6} {'MRR':>6} {'nDCG':>6}")
    for c, m in metrics.items():
        r = m["recall_at_k"]
        print(f"{c:<20} {r['1']:>6.3f} {r['3']:>6.3f} {r['5']:>6.3f} "
              f"{r['10']:>6.3f} {r['20']:>6.3f} {m['mrr']:>6.3f} "
              f"{m['ndcg']:>6.3f}")
    print(f"\nScritti: {OUT_METRICS.name}, {OUT_META.name}, {OUT_DETAILS.name}")


if __name__ == "__main__":
    main()
