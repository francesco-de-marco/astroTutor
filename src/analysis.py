"""
AstroTutor — Analisi dei risultati e generazione dei grafici.

Legge i file già prodotti dalle altre fasi (valutazione, dataset di allineamento,
training) e produce i grafici del report in `report/figures/`. Non rigenera nulla
e non chiama nessun modello: è pura ri-lettura di dati esistenti.

Ogni grafico è indipendente: se i dati per uno mancano viene saltato con un
messaggio che dice cosa serve e in che formato, e gli altri vengono comunque
prodotti. Serve perché parte delle sorgenti (retrieval, latenza) non esiste
ancora e verrà dai todo #1/#2 e P0.

Uso:
    python src/analysis.py                # tutti i grafici possibili
    python src/analysis.py --only 1 2 7   # solo alcuni
    python src/analysis.py --list         # elenco e stato delle sorgenti

--------------------------------------------------------------------------------
SORGENTI DATI

Già disponibili:
  data/eval_progress_<modello>.jsonl   una riga per domanda: level, question,
                                       answer, gulpease, faithfulness, e (dalle
                                       run nuove) contexts e sources
  data/eval_results.json               riepilogo per modello + dettaglio OOD
  data/alignment_data.json             623 triplette DPO
  data/training_metrics.json           metriche per epoca del training DPO

Da produrre (todo #1/#2 e P0) — se mancano, i grafici 7/8/10 vengono saltati:

  data/retrieval_eval.json
    {
      "solo bi-encoder":   {"recall_at_k": {"1": 0.42, "3": 0.61, "5": 0.70,
                                            "10": 0.79, "20": 0.85},
                            "mrr": 0.51, "ndcg": 0.58, "n_queries": 623},
      "+ re-ranker":       {...},
      "+ query expansion": {...},
      "+ level bonus":     {...},
      "BM25":              {...}
    }

  data/latency.json
    {
      "traduzione": [1.8, 2.1, ...],   # secondi, una misura per domanda
      "retrieval":  [4.2, 3.9, ...],
      "generazione":[6.1, 7.4, ...]
    }
--------------------------------------------------------------------------------
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # nessuna finestra: scriviamo solo file
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = PROJECT_ROOT / "data"
FIGURES = PROJECT_ROOT / "report" / "figures"

LEVELS = ["A", "B", "C", "D"]

# I modelli nell'ordine in cui vanno mostrati, con etichetta leggibile e colore
# fisso: lo stesso modello deve avere lo stesso colore in tutti i grafici.
MODELS = [
    ("qwen2.5_3b",        "Baseline\nqwen2.5:3b",   "#9e9e9e"),
    ("astrotutor-dpo",    "DPO\n378 triplette",     "#e07b39"),
    ("astrotutor-dpo-v2", "DPO\n623 triplette",     "#2e7d32"),
]

# Bande di leggibilità attese per livello (indice Gulpease, 0-100: più alto =
# più leggibile). I minimi di A e B sono quelli realmente applicati dai
# guardrail (`ResponseGuardrails.MIN_GULPEASE`); i massimi e le bande di C e D
# sono una proposta di lettura, non un vincolo presente nel codice.
GULPEASE_BANDS = {
    "A": (55, 75),
    "B": (45, 65),
    "C": (35, 55),
    "D": (25, 45),
}

plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


# --------------------------------------------------------------------------- #
# Caricamento dati
# --------------------------------------------------------------------------- #
def load_progress() -> dict:
    """{nome_modello: [righe]} dai file di progresso della valutazione."""
    out = {}
    for key, _label, _color in MODELS:
        path = DATA / f"eval_progress_{key}.jsonl"
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            out[key] = [json.loads(line) for line in f if line.strip()]
    return out


def load_json(name: str):
    """Carica un JSON, o None se manca o non e' un JSON valido (alcuni file del
    progetto sono JSONL: per quelli c'e' load_jsonl)."""
    path = DATA / name
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def load_jsonl(name: str):
    path = DATA / name
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def by_level(rows: list, field: str) -> dict:
    """{livello: [valori non nulli]}"""
    out = {}
    for lv in LEVELS:
        out[lv] = [r[field] for r in rows
                   if r.get("level") == lv and r.get(field) is not None]
    return out


def save(fig, name: str):
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {path.relative_to(PROJECT_ROOT)}")


def skip(n: int, titolo: str, motivo: str):
    print(f"[{n}] SALTATO  {titolo}\n     {motivo}")


# --------------------------------------------------------------------------- #
# 1 — Faithfulness per livello
# --------------------------------------------------------------------------- #
def fig_faithfulness(progress):
    """Barre raggruppate: 4 livelli x N modelli, con barra d'errore.

    È il grafico principale del confronto. La barra d'errore è l'errore
    standard della media: con n=10 per livello serve a mostrare che le
    differenze piccole non sono distinguibili dal rumore.
    """
    if not progress:
        return skip(1, "Faithfulness per livello", "manca data/eval_progress_*.jsonl")

    presenti = [(k, lab, col) for k, lab, col in MODELS if k in progress]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    width = 0.8 / len(presenti)
    x = np.arange(len(LEVELS))

    for i, (key, label, color) in enumerate(presenti):
        vals = by_level(progress[key], "faithfulness")
        medie = [np.mean(vals[lv]) if vals[lv] else np.nan for lv in LEVELS]
        errs = [np.std(vals[lv], ddof=1) / np.sqrt(len(vals[lv]))
                if len(vals[lv]) > 1 else 0 for lv in LEVELS]
        pos = x + (i - (len(presenti) - 1) / 2) * width
        ax.bar(pos, medie, width * 0.9, yerr=errs, capsize=3,
               label=label.replace("\n", " "), color=color,
               error_kw={"lw": 1, "alpha": 0.6})
        for p, m in zip(pos, medie):
            if not np.isnan(m):
                ax.text(p, m + 0.02, f"{m:.2f}", ha="center", fontsize=7.5)

    n = len(by_level(progress[presenti[0][0]], "faithfulness")["A"])
    ax.set_xticks(x)
    ax.set_xticklabels([f"Livello {lv}" for lv in LEVELS])
    ax.set_ylabel("Faithfulness (RAGAS)")
    ax.set_ylim(0, 1.08)
    ax.set_title(f"Fedeltà al contesto recuperato, per livello di difficoltà "
                 f"(n={n} domande per livello)")
    ax.legend(frameon=False, ncol=len(presenti), loc="upper center",
              bbox_to_anchor=(0.5, -0.12))
    save(fig, "01_faithfulness_per_livello.png")


# --------------------------------------------------------------------------- #
# 2 — Tasso di rifiuto OOD
# --------------------------------------------------------------------------- #
def fig_ood(results):
    """Barre semplici: percentuale di domande fuori dominio correttamente
    rifiutate. È il risultato più netto della valutazione."""
    if not results:
        return skip(2, "Rifiuto OOD", "manca data/eval_results.json")

    # In eval_results.json le chiavi sono i nomi Ollama ("qwen2.5:3b"), mentre in
    # MODELS usiamo quelli dei file di progresso ("qwen2.5_3b"): normalizziamo.
    norm = {k.replace(":", "_"): v for k, v in results.items()}
    dati = [(lab, col, norm[k]["ood"]) for k, lab, col in MODELS
            if k in norm and "ood" in norm[k]]
    if not dati:
        return skip(2, "Rifiuto OOD", "nessun campo 'ood' in eval_results.json")

    fig, ax = plt.subplots(figsize=(6, 4.2))
    for i, (label, color, ood) in enumerate(dati):
        pct = ood["refusal_rate"] * 100
        ax.bar(i, pct, 0.55, color=color)
        ax.text(i, pct + 1.5, f"{pct:.0f}%\n{ood['correct']}/{ood['total']}",
                ha="center", fontsize=9)

    ax.set_xticks(range(len(dati)))
    ax.set_xticklabels([d[0] for d in dati])
    ax.set_ylabel("Domande fuori dominio rifiutate correttamente (%)")
    ax.set_ylim(0, 100)
    ax.axhline(50, ls=":", lw=1, color="#666")
    ax.text(len(dati) - 0.45, 51.5, "caso", fontsize=7.5, color="#666", ha="right")
    ax.set_title("Capacità di rifiutare domande fuori dominio")
    save(fig, "02_rifiuto_ood.png")


# --------------------------------------------------------------------------- #
# 3 — Gulpease: punti singoli e banda target
# --------------------------------------------------------------------------- #
def fig_gulpease(progress):
    """Un punto per risposta, non la media: è tutto il senso del todo #10.

    Una media di 57,97 a livello A è compatibile sia con un modello ben tarato
    (tutte le risposte intorno a 57) sia con uno sregolato (metà a 75, metà a
    40). Disegnando i punti singoli sopra la banda attesa, la differenza fra i
    due casi si vede a occhio.
    """
    if not progress:
        return skip(3, "Gulpease", "manca data/eval_progress_*.jsonl")

    presenti = [(k, lab, col) for k, lab, col in MODELS if k in progress]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    rng = np.random.default_rng(42)  # jitter riproducibile

    for j, lv in enumerate(LEVELS):
        lo, hi = GULPEASE_BANDS[lv]
        ax.add_patch(plt.Rectangle((j - 0.42, lo), 0.84, hi - lo,
                                   color="#4a90d9", alpha=0.10, zorder=0))
        ax.plot([j - 0.42, j + 0.42], [lo, lo], color="#4a90d9", lw=1, alpha=0.5)
        ax.plot([j - 0.42, j + 0.42], [hi, hi], color="#4a90d9", lw=1, alpha=0.5)

    width = 0.8 / len(presenti)
    for i, (key, label, color) in enumerate(presenti):
        vals = by_level(progress[key], "gulpease")
        for j, lv in enumerate(LEVELS):
            if not vals[lv]:
                continue
            centro = j + (i - (len(presenti) - 1) / 2) * width
            xs = centro + rng.uniform(-width * 0.28, width * 0.28, len(vals[lv]))
            ax.scatter(xs, vals[lv], s=16, color=color, alpha=0.75,
                       edgecolors="none",
                       label=label.replace("\n", " ") if j == 0 else None)
            ax.plot([centro - width * 0.35, centro + width * 0.35],
                    [np.mean(vals[lv])] * 2, color=color, lw=2)

    ax.set_xticks(range(len(LEVELS)))
    ax.set_xticklabels([f"Livello {lv}\nbanda {GULPEASE_BANDS[lv][0]}-{GULPEASE_BANDS[lv][1]}"
                        for lv in LEVELS])
    ax.set_ylabel("Indice Gulpease (più alto = più leggibile)")
    ax.set_title("Leggibilità: ogni punto è una risposta, la linea è la media\n"
                 "(in azzurro la banda attesa per il livello)")
    ax.legend(frameon=False, ncol=len(presenti), loc="upper center",
              bbox_to_anchor=(0.5, -0.16))
    save(fig, "03_gulpease_aderenza_banda.png")


# --------------------------------------------------------------------------- #
# 4 — Distribuzione della faithfulness
# --------------------------------------------------------------------------- #
def fig_faithfulness_box(progress):
    """Boxplot per modello e livello: mostra la dispersione che la media
    nasconde, e quanto sono fragili le conclusioni con n=10."""
    if not progress:
        return skip(4, "Distribuzione faithfulness", "manca data/eval_progress_*.jsonl")

    presenti = [(k, lab, col) for k, lab, col in MODELS if k in progress]
    fig, axes = plt.subplots(1, len(LEVELS), figsize=(11, 3.8), sharey=True)

    for ax, lv in zip(axes, LEVELS):
        dati, colori = [], []
        for key, _label, color in presenti:
            vals = by_level(progress[key], "faithfulness")[lv]
            dati.append(vals if vals else [np.nan])
            colori.append(color)
        bp = ax.boxplot(dati, patch_artist=True, widths=0.6,
                        medianprops={"color": "black", "lw": 1.4},
                        flierprops={"marker": "o", "ms": 3, "alpha": 0.5})
        for patch, color in zip(bp["boxes"], colori):
            patch.set_facecolor(color)
            patch.set_alpha(0.65)
            patch.set_edgecolor("none")
        ax.set_xticks(range(1, len(presenti) + 1))
        ax.set_xticklabels(["base", "378", "623"][:len(presenti)], fontsize=8)
        ax.set_title(f"Livello {lv}", fontsize=10)

    axes[0].set_ylabel("Faithfulness")
    axes[0].set_ylim(-0.05, 1.05)
    fig.suptitle("Distribuzione della fedeltà per livello — la media da sola "
                 "nasconde la dispersione", y=1.02)
    save(fig, "04_faithfulness_distribuzione.png")


# --------------------------------------------------------------------------- #
# 5 — Bias di lunghezza nel dataset DPO
# --------------------------------------------------------------------------- #
def fig_length_bias(alignment):
    """Istogramma sovrapposto chosen vs rejected.

    Documenta il caveat principale sul risultato del training: il DPO calcola i
    reward come SOMMA dei log-prob dei token, quindi una risposta più lunga ha
    un punteggio sistematicamente più basso a parità di qualità. Se le rejected
    sono sistematicamente più lunghe, il modello ha una scorciatoia per
    distinguerle che non ha niente a che vedere con la qualità didattica.
    """
    if not alignment:
        return skip(5, "Bias di lunghezza", "manca data/alignment_data.json")

    def chars(msgs):
        return sum(len(m["content"]) for m in msgs)

    chosen = np.array([chars(r["chosen"]) for r in alignment])
    rejected = np.array([chars(r["rejected"]) for r in alignment])
    piu_lunga = float((rejected > chosen).mean() * 100)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    bins = np.linspace(0, max(chosen.max(), rejected.max()), 45)
    ax1.hist(chosen, bins=bins, alpha=0.6, label=f"chosen (mediana {np.median(chosen):.0f})",
             color="#2e7d32")
    ax1.hist(rejected, bins=bins, alpha=0.6, label=f"rejected (mediana {np.median(rejected):.0f})",
             color="#c62828")
    ax1.set_xlabel("Lunghezza della risposta (caratteri)")
    ax1.set_ylabel("Numero di triplette")
    ax1.legend(frameon=False, fontsize=9)
    ax1.set_title("Distribuzione delle lunghezze")

    lim = max(chosen.max(), rejected.max()) * 1.02
    ax2.scatter(chosen, rejected, s=8, alpha=0.35, color="#37474f", edgecolors="none")
    ax2.plot([0, lim], [0, lim], ls="--", lw=1, color="#c62828")
    ax2.set_xlim(0, lim)
    ax2.set_ylim(0, lim)
    ax2.set_xlabel("chosen (caratteri)")
    ax2.set_ylabel("rejected (caratteri)")
    ax2.set_title(f"Sopra la diagonale: rejected più lunga\n"
                  f"{piu_lunga:.0f}% delle {len(alignment)} triplette")

    fig.suptitle("Bias di lunghezza del dataset di allineamento", y=1.02)
    save(fig, "05_bias_lunghezza_dataset.png")
    print(f"     rejected più lunga nel {piu_lunga:.1f}% dei casi "
          f"({len(alignment)} triplette)")


# --------------------------------------------------------------------------- #
# 6 — Curve del training DPO
# --------------------------------------------------------------------------- #
def fig_training(metrics):
    """Loss e reward per epoca.

    Il pannello di destra è quello interessante: mostra che il modello ha
    imparato quasi solo abbassando il reward delle rejected, mentre quello
    delle chosen resta piatto. È il comportamento tipico della DPO e va letto
    insieme al grafico 5.
    """
    if not metrics:
        return skip(6, "Curve di training DPO",
                    "manca data/training_metrics.json — trascrivi le metriche per "
                    "epoca dal log di Colab (vedi docstring)")

    ep = [m["epoch"] for m in metrics]
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 3.8))

    ax1.plot(ep, [m["train_loss"] for m in metrics], "o-", label="training", color="#1565c0")
    if all("eval_loss" in m for m in metrics):
        ax1.plot(ep, [m["eval_loss"] for m in metrics], "s--", label="validation",
                 color="#ef6c00")
    ax1.axhline(np.log(2), ls=":", lw=1, color="#888")
    ax1.text(ep[0], np.log(2) + 0.012, "ln 2 = valore all'inizializzazione",
             fontsize=7.5, color="#666")
    ax1.set_xlabel("Epoca"); ax1.set_ylabel("Loss DPO")
    ax1.set_xticks(ep); ax1.legend(frameon=False, fontsize=9)
    ax1.set_title("Loss")

    ax2.plot(ep, [m["rewards_chosen"] for m in metrics], "o-", label="chosen",
             color="#2e7d32")
    ax2.plot(ep, [m["rewards_rejected"] for m in metrics], "s-", label="rejected",
             color="#c62828")
    ax2.axhline(0, lw=0.8, color="#888")
    ax2.set_xlabel("Epoca"); ax2.set_ylabel("Reward implicito")
    ax2.set_xticks(ep); ax2.legend(frameon=False, fontsize=9)
    ax2.set_title("Il modello schiaccia le rejected,\nnon promuove le chosen", fontsize=10)

    ax3.plot(ep, [m["rewards_margins"] for m in metrics], "o-", color="#6a1b9a")
    ax3b = ax3.twinx()
    ax3b.plot(ep, [m["rewards_accuracies"] for m in metrics], "s--", color="#00838f")
    ax3b.set_ylim(0, 1.05)
    ax3b.set_ylabel("Accuracy", color="#00838f")
    ax3b.grid(False)
    ax3.set_xlabel("Epoca"); ax3.set_ylabel("Margine", color="#6a1b9a")
    ax3.set_xticks(ep)
    ax3.set_title("Margine (viola) e accuracy (ciano)", fontsize=10)

    fig.suptitle("Training DPO — 623 triplette, 2 epoche", y=1.03)
    save(fig, "06_training_dpo.png")


# --------------------------------------------------------------------------- #
# 7 — Recall@k per configurazione di retrieval
# --------------------------------------------------------------------------- #
def fig_recall_at_k(retr):
    """Una curva per configurazione. È il grafico che risponde al requisito
    del corso (Lezione 4) e giustifica re-ranker, query expansion e bonus di
    livello con numeri invece che con argomentazioni."""
    if not retr:
        return skip(7, "Recall@k",
                    "manca data/retrieval_eval.json — lo produce il todo #1/#2 "
                    "(vedi lo schema nella docstring)")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for nome, d in retr.items():
        ks = sorted(int(k) for k in d["recall_at_k"])
        ax.plot(ks, [d["recall_at_k"][str(k)] for k in ks], "o-", label=nome, lw=1.8)

    n = next(iter(retr.values())).get("n_queries", "?")
    ax.set_xlabel("k (documenti recuperati)")
    ax.set_ylabel("Recall@k")
    ax.set_ylim(0, 1.02)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"Recall@k per configurazione del retrieval (n={n} query)\n"
                 "gold set silver-standard: i valori assoluti sono un limite inferiore",
                 fontsize=10)
    save(fig, "07_recall_at_k.png")


# --------------------------------------------------------------------------- #
# 8 — MRR e nDCG per configurazione
# --------------------------------------------------------------------------- #
def fig_mrr_ndcg(retr):
    """Barre affiancate: quanto guadagna ogni componente aggiunto."""
    if not retr:
        return skip(8, "MRR / nDCG",
                    "manca data/retrieval_eval.json — lo produce il todo #1/#2")

    nomi = list(retr)
    x = np.arange(len(nomi))
    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    ax.bar(x - 0.2, [retr[n]["mrr"] for n in nomi], 0.38, label="MRR", color="#5c6bc0")
    ax.bar(x + 0.2, [retr[n]["ndcg"] for n in nomi], 0.38, label="nDCG", color="#26a69a")
    for i, n in enumerate(nomi):
        ax.text(i - 0.2, retr[n]["mrr"] + 0.01, f"{retr[n]['mrr']:.2f}",
                ha="center", fontsize=7.5)
        ax.text(i + 0.2, retr[n]["ndcg"] + 0.01, f"{retr[n]['ndcg']:.2f}",
                ha="center", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(nomi, rotation=15, ha="right", fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False)
    ax.set_title("Qualità del ranking per configurazione")
    save(fig, "08_mrr_ndcg.png")


# --------------------------------------------------------------------------- #
# 9 — Score del re-ranker: in dominio vs fuori dominio
# --------------------------------------------------------------------------- #
def fig_score_distribution(progress, results):
    """Serve a calibrare la soglia di rifiuto (todo #9).

    Il rifiuto OOD oggi è un giudizio del modello; con una soglia sullo score
    del re-ranker diventa una garanzia di sistema. Il grafico mostra se le due
    distribuzioni sono separabili e dove cade il confine.

    Richiede il campo `sources` nei file di progresso, presente solo dalle run
    fatte dopo la modifica a evaluation.py.
    """
    in_dom = [s["score"] for rows in progress.values() for r in rows
              for s in r.get("sources", [])]
    if not in_dom:
        return skip(9, "Distribuzione degli score",
                    "i file di progresso non hanno il campo 'sources' (aggiunto "
                    "a evaluation.py dopo la run del 25/07): serve una run nuova")

    ood = []
    for m in (results or {}).values():
        for d in m.get("ood", {}).get("details", []):
            ood.extend(s["score"] for s in d.get("sources", []))

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bins = np.linspace(min(in_dom + (ood or in_dom)), max(in_dom + (ood or in_dom)), 40)
    ax.hist(in_dom, bins=bins, alpha=0.6, color="#2e7d32", label=f"in dominio (n={len(in_dom)})")
    if ood:
        ax.hist(ood, bins=bins, alpha=0.6, color="#c62828", label=f"fuori dominio (n={len(ood)})")
    else:
        print("     nota: nessuno score OOD salvato, mostro solo l'in-dominio")
    ax.axvline(-5.0, ls="--", lw=1.5, color="#333")
    ax.text(-5.0, ax.get_ylim()[1] * 0.92, " soglia attuale (-5.0)\n inerte in generation.py:132",
            fontsize=8)
    ax.set_xlabel("Score del re-ranker (logit di pertinenza)")
    ax.set_ylabel("Numero di chunk")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("Dove separare le domande a cui il corpus può rispondere")
    save(fig, "09_score_reranker_ood.png")


# --------------------------------------------------------------------------- #
# 10 — Latenza per stadio
# --------------------------------------------------------------------------- #
def fig_latency(lat):
    """Barre in pila: dove se ne va davvero il tempo di una query.

    Serve a evitare di ottimizzare lo stadio sbagliato — l'errore che lo
    speculative decoding avrebbe fatto commettere.
    """
    if not lat:
        return skip(10, "Latenza per stadio",
                    "manca data/latency.json — lo produce il todo P0 "
                    "(strumentazione con perf_counter)")

    stadi = list(lat)
    medie = [float(np.mean(lat[s])) for s in stadi]
    tot = sum(medie)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    colori = ["#5c6bc0", "#26a69a", "#ef6c00", "#8d6e63", "#ab47bc"]

    base = 0
    for s, m, c in zip(stadi, medie, colori):
        ax1.bar(0, m, 0.5, bottom=base, color=c, label=f"{s} — {m:.1f}s ({m/tot*100:.0f}%)")
        if m / tot > 0.06:
            ax1.text(0, base + m / 2, f"{m:.1f}s", ha="center", va="center",
                     color="white", fontsize=9)
        base += m
    ax1.set_xticks([])
    ax1.set_ylabel("Secondi per query")
    ax1.set_title(f"Composizione della latenza (totale {tot:.1f}s)")
    ax1.legend(frameon=False, fontsize=8.5, loc="upper right")

    ax2.boxplot([lat[s] for s in stadi], labels=stadi, patch_artist=True,
                medianprops={"color": "black"})
    ax2.set_ylabel("Secondi")
    ax2.set_title("Variabilità per stadio")
    ax2.tick_params(axis="x", rotation=15)

    save(fig, "10_latenza_per_stadio.png")


# --------------------------------------------------------------------------- #
# Tabella riassuntiva in Markdown
# --------------------------------------------------------------------------- #
def tabella_riassuntiva(progress, results):
    """Scrive report/figures/tabella_risultati.md, pronta da incollare nel report."""
    if not progress:
        return skip(0, "Tabella riassuntiva", "manca data/eval_progress_*.jsonl")

    presenti = [(k, lab.replace("\n", " "), c) for k, lab, c in MODELS if k in progress]
    righe = ["# Risultati della valutazione", "",
             "## Faithfulness media per livello", "",
             "| Livello | " + " | ".join(l for _, l, _ in presenti) + " |",
             "|---" * (len(presenti) + 1) + "|"]

    for lv in LEVELS:
        cel = []
        for key, _l, _c in presenti:
            v = by_level(progress[key], "faithfulness")[lv]
            cel.append(f"{np.mean(v):.3f} (n={len(v)})" if v else "n/d")
        righe.append(f"| {lv} | " + " | ".join(cel) + " |")

    cel = []
    for key, _l, _c in presenti:
        v = [r["faithfulness"] for r in progress[key] if r.get("faithfulness") is not None]
        cel.append(f"**{np.mean(v):.3f}**" if v else "n/d")
    righe += [f"| **Media** | " + " | ".join(cel) + " |", ""]

    righe += ["## Gulpease medio per livello", "",
              "| Livello | Banda attesa | " + " | ".join(l for _, l, _ in presenti) + " |",
              "|---" * (len(presenti) + 2) + "|"]
    for lv in LEVELS:
        cel = []
        for key, _l, _c in presenti:
            v = by_level(progress[key], "gulpease")[lv]
            if v:
                lo, hi = GULPEASE_BANDS[lv]
                dentro = sum(lo <= x <= hi for x in v) / len(v) * 100
                cel.append(f"{np.mean(v):.1f} — {dentro:.0f}% in banda")
            else:
                cel.append("n/d")
        lo, hi = GULPEASE_BANDS[lv]
        righe.append(f"| {lv} | {lo}-{hi} | " + " | ".join(cel) + " |")
    righe.append("")

    if results:
        righe += ["## Rifiuto fuori dominio", "",
                  "| Modello | Rifiuti corretti | Tasso |", "|---|---|---|"]
        for nome, d in results.items():
            if "ood" in d:
                o = d["ood"]
                righe.append(f"| {nome} | {o['correct']}/{o['total']} | "
                             f"{o['refusal_rate']*100:.0f}% |")
        righe.append("")

    righe += ["> Nota: con n=10 domande per livello, differenze di faithfulness "
              "inferiori a ~0,10 non sono distinguibili dal rumore campionario.", ""]

    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / "tabella_risultati.md"
    path.write_text("\n".join(righe), encoding="utf-8")
    print(f"   -> {path.relative_to(PROJECT_ROOT)}")


# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Grafici e metriche di AstroTutor")
    parser.add_argument("--only", type=int, nargs="+", metavar="N",
                        help="genera solo i grafici indicati (1-10)")
    parser.add_argument("--list", action="store_true",
                        help="mostra lo stato delle sorgenti dati ed esce")
    args = parser.parse_args()

    progress = load_progress()
    results = load_json("eval_results.json")
    # alignment_data.json è in realtà JSONL (una tripletta per riga)
    alignment = load_json("alignment_data.json") or load_jsonl("alignment_data.json")

    # training_metrics.json avvolge le metriche in {_nota, _run, metrics}
    training = load_json("training_metrics.json")
    if isinstance(training, dict):
        training = training.get("metrics")
    retr = load_json("retrieval_eval.json")
    lat = load_json("latency.json")

    if args.list:
        print("Sorgenti dati:")
        for nome, ok in [
            ("eval_progress_*.jsonl", bool(progress)),
            ("eval_results.json", results is not None),
            ("alignment_data.json", alignment is not None),
            ("training_metrics.json", training is not None),
            ("retrieval_eval.json  (todo #1/#2)", retr is not None),
            ("latency.json         (todo P0)", lat is not None),
        ]:
            print(f"  {'presente' if ok else 'MANCANTE'}  {nome}")
        if progress:
            print("\nModelli trovati:", ", ".join(progress))
        return

    grafici = {
        1: ("Faithfulness per livello", lambda: fig_faithfulness(progress)),
        2: ("Rifiuto OOD", lambda: fig_ood(results)),
        3: ("Gulpease e banda target", lambda: fig_gulpease(progress)),
        4: ("Distribuzione faithfulness", lambda: fig_faithfulness_box(progress)),
        5: ("Bias di lunghezza", lambda: fig_length_bias(alignment)),
        6: ("Training DPO", lambda: fig_training(training)),
        7: ("Recall@k", lambda: fig_recall_at_k(retr)),
        8: ("MRR / nDCG", lambda: fig_mrr_ndcg(retr)),
        9: ("Score re-ranker", lambda: fig_score_distribution(progress, results)),
        10: ("Latenza per stadio", lambda: fig_latency(lat)),
    }

    scelti = args.only or sorted(grafici)
    fatti = 0
    for n in scelti:
        if n not in grafici:
            print(f"[{n}] numero non valido")
            continue
        titolo, fn = grafici[n]
        print(f"[{n}] {titolo}")
        try:
            prima = len(list(FIGURES.glob("*.png"))) if FIGURES.exists() else 0
            fn()
            dopo = len(list(FIGURES.glob("*.png"))) if FIGURES.exists() else 0
            fatti += dopo > prima
        except Exception as e:
            print(f"     ERRORE: {type(e).__name__}: {e}")

    if not args.only:
        print("\n[tabella] Riepilogo in Markdown")
        try:
            tabella_riassuntiva(progress, results)
        except Exception as e:
            print(f"     ERRORE: {type(e).__name__}: {e}")

    print(f"\n{fatti} grafici scritti in {FIGURES.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
