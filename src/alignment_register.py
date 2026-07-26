"""
Alignment — dataset DPO a variabile singola: SOLO il registro.

Perché esiste, in una riga: nelle triplette di `alignment.py` la `chosen` la
scrive l'oracolo (llama-3.3-70b) e la `rejected` il modello piccolo, quindi il
DPO puo' minimizzare la loss imparando "scrivi come il 70B" invece di "usa il
registro giusto per il livello". Qui le due risposte le genera lo STESSO
modello con lo STESSO contesto: l'unica differenza e' l'istruzione di livello.

    chosen   = modello piccolo, prompt di runtime con il livello CORRETTO
    rejected = modello piccolo, identico prompt ma con il livello INVERTITO
               (A,B -> D ; C,D -> A), la stessa regola gia' usata in alignment.py

Due conseguenze pratiche:
  - e' on-policy: gli errori nel lato `rejected` sono errori che il modello
    commette davvero, non errori inventati da un altro modello;
  - non serve il retrieval. I `prompt` gia' salvati in alignment_data.json
    contengono il contesto RAG, quindi lo script gira ovunque ci sia Ollama:
    niente ChromaDB (263 MB), niente embedder, niente re-ranker.

Le allucinazioni e il fuori-dominio restano fuori da questo dataset per scelta:
sono difetti diversi e vanno affrontati altrove (soglia del re-ranker per l'OOD,
qualita' del retrieval per le allucinazioni). Mescolarli e' cio' che rendeva il
segnale illeggibile.

Controllo qualita' senza giudice LLM: una coppia entra nel dataset solo se il
Gulpease si muove nella direzione attesa di almeno --min-gap punti. Il registro
e' l'unico asse del progetto misurabile in modo deterministico, quindi qui il
filtro costa zero chiamate.

Uso tipico (su Colab, prima del training):
    python src/alignment_register.py --model qwen2.5:3b
    python src/alignment_register.py --report        # solo statistiche

Output: data/alignment_register.json, stesso schema di alignment_data.json,
quindi il notebook di training lo carica senza modifiche.
"""

import argparse
import difflib
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Su Colab questo file puo' girare da solo, accanto al solo dataset: in quel
# caso src/alignment.py non c'e' e le due cose che servono (la frase di rifiuto
# e la formula del Gulpease) sono ridefinite qui sotto. Quando invece il
# repository c'e', si importano le originali e si verifica che non siano
# divergenti — cosi' la copia non puo' invecchiare in silenzio.
_REFUSAL_LOCALE = (
    "Mi dispiace, ma i documenti a mia disposizione non contengono "
    "questa informazione."
)


def _gulpease_locale(text: str) -> float:
    import re
    words = re.findall(r"[a-zA-Zà-úÀ-Ú]+", text)
    if not words:
        return 0.0
    letters = sum(len(w) for w in words)
    sentences = max(1, len(re.findall(r"[.!?]+", text)))
    return 89 + (300 * sentences - 10 * letters) / len(words)


try:
    from src.alignment import REFUSAL_MESSAGE, ResponseGuardrails
    gulpease = ResponseGuardrails.gulpease
    assert REFUSAL_MESSAGE == _REFUSAL_LOCALE, "REFUSAL_MESSAGE divergente da src/alignment.py"
    _prova = "Il buco nero e' molto grande. La stella cade dentro."
    assert abs(gulpease(_prova) - _gulpease_locale(_prova)) < 0.01, "gulpease divergente"
except ImportError:
    REFUSAL_MESSAGE = _REFUSAL_LOCALE
    gulpease = _gulpease_locale

SOURCE_PATH = PROJECT_ROOT / "data" / "alignment_data.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "alignment_register.json"

# Bande Gulpease attese per livello (le stesse usate in analysis.py e nei report)
BANDS = {"A": (55, 75), "B": (45, 65), "C": (35, 55), "D": (25, 45)}

# Stessa inversione di alignment.py: il contrasto e' massimo tra i due estremi.
INVERTED = {"A": "D", "B": "D", "C": "A", "D": "A"}

# Copia letterale di RAGGenerator._get_system_instructions. Duplicata di
# proposito: importare generation.py trascinerebbe dentro AdvancedRetriever,
# quindi ChromaDB e i due encoder, che qui non servono. Il test all'avvio
# verifica che le due copie non siano andate a divergere.
LEVEL_STYLE = {
    "A": "Spiega come se parlassi a un bambino di 6-10 anni. Usa analogie semplici, un tono molto dolce e termini elementari.",
    "B": "Spiega come se parlassi a uno studente delle medie. Sii chiaro, evita formule troppo complesse ma usa i nomi corretti dei concetti.",
    "C": "Spiega come se parlassi a uno studente delle superiori. Usa un linguaggio tecnico corretto e approfondisci i nessi logici.",
    "D": "Spiega a livello universitario. Sii rigoroso, cita dettagli fisici o matematici se presenti nel testo e usa un tono accademico.",
}


# ── Costruzione del prompt invertito ──────────────────────────────────

def swap_level(prompt_messages: list, da: str, a: str) -> list:
    """Stesso prompt, con la sola riga di stile sostituita.

    Non ricostruiamo il prompt da zero perche' il contesto RAG e' gia' dentro
    il messaggio di sistema: riscriverlo richiederebbe di rifare il retrieval,
    e con esso l'indice e gli encoder. Sostituendo solo la stringa di stile si
    ha la garanzia — non l'auspicio — che le due varianti differiscano
    esclusivamente per il livello richiesto.
    """
    fuori = []
    sostituito = False
    for msg in prompt_messages:
        if msg["role"] == "system" and LEVEL_STYLE[da] in msg["content"]:
            fuori.append({
                "role": "system",
                "content": msg["content"].replace(LEVEL_STYLE[da], LEVEL_STYLE[a]),
            })
            sostituito = True
        else:
            fuori.append(dict(msg))
    return fuori if sostituito else None


def direzione_attesa(livello: str) -> int:
    """+1 se la chosen deve avere Gulpease piu' ALTO della rejected.

    A e B sono i livelli semplici: la risposta corretta e' piu' leggibile di
    quella scritta in accademichese. Per C e D vale l'opposto.
    """
    return +1 if livello in ("A", "B") else -1


# ── Controlli qualita' (nessuna chiamata a un giudice) ────────────────

def valuta_coppia(chosen: str, rejected: str, livello: str, args):
    """(None, None) se la coppia va tenuta, altrimenti (categoria, dettaglio).

    La categoria e' una stringa fissa cosi' il riepilogo finale si aggrega;
    il dettaglio (il numero che ha fatto scattare il filtro) resta sulla riga
    di log del singolo scarto, dove serve per capire se una soglia va allentata.
    """
    if not chosen or not rejected:
        return "risposta vuota", ""
    if len(chosen) < args.min_chars or len(rejected) < args.min_chars:
        return "risposta troppo corta", f"{min(len(chosen), len(rejected))} char"
    if REFUSAL_MESSAGE in chosen:
        return "chosen e' un rifiuto", ""
    if REFUSAL_MESSAGE in rejected:
        # Il modello ha rifiutato con lo stile invertito: non e' un errore di
        # registro, e' un altro comportamento. Fuori dal dataset del registro.
        return "rejected e' un rifiuto", ""
    somiglianza = difflib.SequenceMatcher(None, chosen, rejected).ratio()
    if somiglianza > args.max_similarity:
        return "risposte quasi identiche", f"{somiglianza:.2f}"

    gap = (gulpease(chosen) - gulpease(rejected)) * direzione_attesa(livello)
    if gap < args.min_gap:
        return "contrasto di registro insufficiente", f"gap {gap:+.1f}"

    if not args.no_length_gate:
        lc, lr = len(chosen), len(rejected)
        rapporto = max(lc, lr) / max(1, min(lc, lr))
        if rapporto > args.max_length_ratio:
            # Il DPO somma i log-prob sui token: se le chosen sono
            # sistematicamente piu' corte, "preferisci il testo breve" e' una
            # soluzione valida della loss e il registro non viene mai imparato.
            return "squilibrio di lunghezza", f"{rapporto:.2f}x"
    return None, None


# ── Generazione ───────────────────────────────────────────────────────

def carica_ids(path: Path) -> set:
    ids = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if riga:
                    try:
                        ids.add(json.loads(riga)["id"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    return ids


def carica_sorgenti(limit: int | None) -> list:
    """Prompt di partenza: tutte le triplette esistenti tranne le OOD.

    Le OOD sono escluse per costruzione — il loro prompt nasce da un retrieval
    che non doveva trovare nulla, e il comportamento corretto li' e' il rifiuto,
    non un registro diverso.
    """
    righe = []
    with open(SOURCE_PATH, encoding="utf-8") as f:
        for riga in f:
            riga = riga.strip()
            if not riga:
                continue
            r = json.loads(riga)
            if r.get("strategy") == "ood":
                continue
            if r.get("user_level") not in LEVEL_STYLE or not r.get("prompt"):
                continue
            righe.append(r)
    # Deduplica sui prompt: hallucination e wrong_register possono condividere
    # la stessa domanda, e due coppie identiche peserebbero doppio nel training.
    viste, unici = set(), []
    for r in righe:
        chiave = hashlib.md5(
            json.dumps(r["prompt"], sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        if chiave not in viste:
            viste.add(chiave)
            unici.append(r)
    return unici[:limit] if limit else unici


def genera(args):
    client = OpenAI(base_url=args.base_url, api_key="ollama", timeout=args.timeout)

    sorgenti = carica_sorgenti(args.limit)
    gia_fatte = carica_ids(OUTPUT_PATH)
    print(f"Prompt disponibili (OOD esclusi, deduplicati): {len(sorgenti)}")
    print(f"Coppie gia' presenti in {OUTPUT_PATH.name}: {len(gia_fatte)}")
    print(f"Modello generatore: {args.model} — chosen e rejected vengono da qui\n")

    def chiama(messages):
        for tentativo in range(3):
            try:
                r = client.chat.completions.create(
                    model=args.model,
                    messages=messages,
                    temperature=args.temperature,
                    frequency_penalty=0.6,   # stessi parametri di generation.py:
                    presence_penalty=0.5,    # la chosen e' cio' che il sistema
                )                            # produrrebbe davvero a runtime
                return (r.choices[0].message.content or "").strip()
            except Exception as e:
                if tentativo == 2:
                    raise
                print(f"    ritento ({e.__class__.__name__})...")
                time.sleep(2 * (tentativo + 1))

    tenute, scarti = 0, {}
    t0 = time.time()
    with open(OUTPUT_PATH, "a", encoding="utf-8") as out:
        for i, riga in enumerate(sorgenti, 1):
            livello = riga["user_level"]
            invertito = INVERTED[livello]
            pair_id = hashlib.md5(
                f"register|{riga['id']}|{args.model}".encode()
            ).hexdigest()
            if pair_id in gia_fatte:
                continue

            prompt_invertito = swap_level(riga["prompt"], livello, invertito)
            if prompt_invertito is None:
                scarti["stile non trovato nel prompt"] = scarti.get("stile non trovato nel prompt", 0) + 1
                continue

            chosen = chiama(riga["prompt"])
            rejected = chiama(prompt_invertito)

            motivo, dettaglio = valuta_coppia(chosen, rejected, livello, args)
            if motivo:
                scarti[motivo] = scarti.get(motivo, 0) + 1
                print(f"[{i}/{len(sorgenti)}] {livello} scartata — {motivo} {dettaglio}")
                continue

            gc, gr = gulpease(chosen), gulpease(rejected)
            out.write(json.dumps({
                "id": pair_id,
                "strategy": "register",
                "user_level": livello,
                "inverted_level": invertito,
                "question": riga.get("question", ""),
                "prompt": riga["prompt"],
                "chosen": [{"role": "assistant", "content": chosen}],
                "rejected": [{"role": "assistant", "content": rejected}],
                "gulpease_chosen": round(gc, 1),
                "gulpease_rejected": round(gr, 1),
                "generator_model": args.model,
                "source_id": riga["id"],
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }, ensure_ascii=False) + "\n")
            out.flush()
            tenute += 1
            print(f"[{i}/{len(sorgenti)}] {livello}->{invertito}  "
                  f"gulp {gc:.0f} vs {gr:.0f}  "
                  f"len {len(chosen)}/{len(rejected)}  "
                  f"({time.time() - t0:.0f}s, tenute {tenute})")

    print(f"\n{'='*64}")
    print(f"Coppie tenute in questa sessione: {tenute}")
    if scarti:
        print("Scarti per motivo:")
        for k, v in sorted(scarti.items(), key=lambda x: -x[1]):
            print(f"  {v:4d}  {k}")
    print(f"Totale nel file: {len(carica_ids(OUTPUT_PATH))}")
    print(f"Output: {OUTPUT_PATH}")


# ── Report sul file prodotto ──────────────────────────────────────────

def report(path: Path):
    if not path.exists():
        print(f"{path} non esiste ancora.")
        return
    righe = [json.loads(r) for r in open(path, encoding="utf-8") if r.strip()]
    if not righe:
        print("File vuoto.")
        return
    print(f"Coppie totali: {len(righe)}\n")
    print(f"{'liv':4s}{'n':>5s}{'gulp chosen':>13s}{'gulp rej':>10s}{'gap':>7s}"
          f"{'in banda':>10s}{'len chosen':>12s}{'len rej':>9s}")
    for L in "ABCD":
        s = [r for r in righe if r["user_level"] == L]
        if not s:
            print(f"{L:4s}{0:>5d}   (nessuna coppia)")
            continue
        gc = sum(r["gulpease_chosen"] for r in s) / len(s)
        gr = sum(r["gulpease_rejected"] for r in s) / len(s)
        lo, hi = BANDS[L]
        banda = sum(lo <= r["gulpease_chosen"] <= hi for r in s)
        lc = sum(len(r["chosen"][0]["content"]) for r in s) / len(s)
        lr = sum(len(r["rejected"][0]["content"]) for r in s) / len(s)
        print(f"{L:4s}{len(s):>5d}{gc:>13.1f}{gr:>10.1f}"
              f"{(gc - gr) * direzione_attesa(L):>7.1f}"
              f"{banda / len(s) * 100:>9.0f}%{lc:>12.0f}{lr:>9.0f}")
    piu_lunghe = sum(
        len(r["chosen"][0]["content"]) > len(r["rejected"][0]["content"]) for r in righe
    )
    print(f"\nchosen piu' lunga della rejected: {piu_lunghe}/{len(righe)} "
          f"({piu_lunghe / len(righe) * 100:.0f}%) — a 50% il bias di lunghezza e' neutralizzato")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="qwen2.5:3b",
                   help="modello che genera ENTRAMBI i lati (default: qwen2.5:3b, "
                        "cioe' il modello da allineare: serve per essere on-policy)")
    p.add_argument("--base-url", default="http://localhost:11434/v1")
    p.add_argument("--temperature", type=float, default=0.1,
                   help="default 0.1, come generation.py a runtime")
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument("--limit", type=int, default=None,
                   help="usa solo i primi N prompt (utile per una prova da 10)")
    p.add_argument("--min-gap", type=float, default=5.0,
                   help="punti Gulpease minimi di contrasto nella direzione attesa")
    p.add_argument("--min-chars", type=int, default=200)
    p.add_argument("--max-similarity", type=float, default=0.9)
    p.add_argument("--max-length-ratio", type=float, default=1.6)
    p.add_argument("--no-length-gate", action="store_true",
                   help="disattiva il filtro sullo squilibrio di lunghezza")
    p.add_argument("--out", default=None, help="file di output alternativo")
    p.add_argument("--report", action="store_true",
                   help="stampa le statistiche del file esistente senza generare")
    args = p.parse_args()

    if args.out:
        OUTPUT_PATH = Path(args.out)
    if args.report:
        report(OUTPUT_PATH)
    else:
        genera(args)
        report(OUTPUT_PATH)
