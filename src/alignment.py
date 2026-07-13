"""
Alignment — Fase 4 (Dataset RAG-Aware) e Fase 5 (supporto DPO) del progetto.

Parte 1 — Data Collection (RLAIF):
    Genera le triplette {prompt, chosen, rejected} per il DPO e le accoda in
    data/alignment_data.json (formato JSON Lines, una tripletta per riga).
    - prompt   : gli stessi messaggi (system + user) che build_prompt() di
                 generation.py produce a runtime (domanda + contesto RAG + livello)
    - chosen   : risposta ideale generata da un LLM "Oracolo" più grande
                 (config: ORACLE_MODEL), fedele al contesto e adattata al livello
    - rejected : risposta sbagliata ma plausibile, generata dal modello piccolo
                 di produzione con tre strategie:
                   * wrong_register — registro invertito (accademico a un bambino,
                     infantile a un universitario)
                   * hallucination  — risposta a memoria, ignorando il contesto
                   * ood            — domanda fuori dominio: chosen = rifiuto
                     standard, rejected = risposta sicura e inventata

    Uso:  python src/alignment.py --target 400
    Lo script è idempotente: le triplette già presenti nel file vengono
    saltate e si può interrompere/riprendere in qualsiasi momento.

Parte 2 — Guardrails a runtime:
    ResponseGuardrails valuta la risposta generata (indice Gulpease, gergo
    tecnico, formule, lunghezza) rispetto al livello utente e produce
    l'istruzione correttiva per un'eventuale rigenerazione. È usata da
    generation.py dopo ogni risposta.

Il training DPO vero e proprio gira su Colab A100 (QLoRA + TRL):
vedi src/alignment_dpo_colab.ipynb.
"""

import argparse
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

# Eseguibile sia come `python src/alignment.py` sia come modulo
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config import LLM_MODEL, ORACLE_BASE_URL, ORACLE_API_KEY, ORACLE_MODEL
except ImportError:
    LLM_MODEL = "qwen2.5:3b"
    ORACLE_BASE_URL = "http://localhost:11434/v1"
    ORACLE_API_KEY = "ollama"
    ORACLE_MODEL = "qwen3:8b"

CHUNKS_DIR = PROJECT_ROOT / "data" / "processed" / "chunks"
DATA_PATH = PROJECT_ROOT / "data" / "alignment_data.json"

# Stessa stringa imposta dal system prompt di generation.py: il modello
# allineato deve impararla come comportamento nativo sui casi OOD.
REFUSAL_MESSAGE = (
    "Mi dispiace, ma i documenti a mia disposizione non contengono "
    "questa informazione."
)

# Sotto questa lunghezza un chunk non basta a generare una buona domanda
MIN_SOURCE_CHUNK_CHARS = 400

STRATEGY_WEIGHTS = {
    "wrong_register": 0.4,
    "hallucination": 0.4,
    "ood": 0.2,
}

AUDIENCE = {
    "A": "un bambino curioso di 8 anni",
    "B": "uno studente delle scuole medie",
    "C": "uno studente delle scuole superiori",
    "D": "uno studente universitario di fisica",
}

# Domande fuori dominio: il comportamento corretto è il rifiuto standard.
OOD_QUESTIONS = [
    "Qual è la ricetta originale della carbonara?",
    "Chi ha vinto i mondiali di calcio del 2006?",
    "Come si coltivano i pomodori sul balcone?",
    "Quali sono i sintomi dell'influenza stagionale?",
    "Chi era Giulio Cesare e come è morto?",
    "Come funziona il motore a scoppio di un'automobile?",
    "Qual è la capitale dell'Australia?",
    "Come si prepara il pane in casa?",
    "Quali esercizi servono per allenare gli addominali?",
    "Chi ha dipinto la Gioconda e in che anno?",
    "Come si scrive un curriculum efficace?",
    "Qual è la differenza tra un mutuo fisso e uno variabile?",
    "Come si addestra un cucciolo di cane?",
    "Quali sono le regole del gioco degli scacchi?",
    "Che strumenti servono per imparare a suonare la chitarra?",
    "Come funziona la fotosintesi clorofilliana?",
    "Quali documenti servono per rinnovare il passaporto?",
    "Come si toglie una macchia di vino dalla tovaglia?",
    "Qual è la trama dei Promessi Sposi?",
    "Come si programma un sito web in HTML?",
]


def strip_thinking(text: str) -> str:
    """Rimuove i blocchi <think>...</think> dei modelli con reasoning (es. qwen3)."""
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# ═══════════════════════════════════════════════════════════════════
#  PARTE 2 — GUARDRAILS A RUNTIME
# ═══════════════════════════════════════════════════════════════════

class ResponseGuardrails:
    """
    Controlli post-generazione sul tono/registro della risposta rispetto
    al livello utente. Non blocca mai la risposta: segnala i problemi e
    fornisce l'istruzione correttiva per una singola rigenerazione.
    """

    # Indice Gulpease minimo (100 = massima leggibilità). Le soglie sono
    # volutamente prudenti: un testo scientifico non arriva ai valori
    # della prosa per l'infanzia.
    MIN_GULPEASE = {"A": 55, "B": 45}
    # Un bambino non regge risposte-fiume
    MAX_WORDS = {"A": 250, "B": 400}
    # Gergo accademico che non deve comparire in una risposta di livello A
    JARGON_A = [
        "tensore", "tensori", "tensoriale",
        "lagrangiana", "hamiltoniana",
        "covariante", "controvariante",
        "equazione differenziale", "equazioni differenziali",
        "derivata parziale", "integrale di",
        "spazio di hilbert", "operatore quantistico",
        "metrica di schwarzschild", "metrica di kerr",
    ]
    LATEX_PATTERN = re.compile(r"\$[^$]+\$|\\(frac|int|partial|nabla|sum|sqrt)\b")

    @staticmethod
    def gulpease(text: str) -> float:
        """Indice di leggibilità Gulpease (tarato sull'italiano)."""
        words = re.findall(r"[a-zA-Zà-úÀ-Ú]+", text)
        if not words:
            return 0.0
        letters = sum(len(w) for w in words)
        sentences = max(1, len(re.findall(r"[.!?]+", text)))
        return 89 + (300 * sentences - 10 * letters) / len(words)

    def check(self, answer: str, user_level: str) -> list:
        """Restituisce la lista dei problemi trovati (vuota = risposta ok)."""
        issues = []
        text = (answer or "").strip()
        if not text:
            return ["risposta vuota"]
        # Il rifiuto standard è un comportamento corretto, mai da correggere
        if REFUSAL_MESSAGE in text:
            return []

        n_words = len(text.split())
        max_words = self.MAX_WORDS.get(user_level)
        if max_words and n_words > max_words:
            issues.append(
                f"risposta troppo lunga per il livello {user_level} "
                f"({n_words} parole, massimo {max_words})"
            )

        min_g = self.MIN_GULPEASE.get(user_level)
        if min_g:
            g = self.gulpease(text)
            if g < min_g:
                issues.append(
                    f"leggibilità troppo bassa per il livello {user_level} "
                    f"(Gulpease {g:.0f}, minimo {min_g}): frasi più corte e parole più semplici"
                )

        if user_level == "A":
            lower = text.lower()
            found = [j for j in self.JARGON_A if j in lower]
            if found:
                issues.append(
                    "termini accademici inadatti a un bambino: " + ", ".join(found)
                )
            if self.LATEX_PATTERN.search(text):
                issues.append("formule matematiche in una risposta per bambini")

        return issues

    def corrective_instruction(self, issues: list, user_level: str) -> str:
        """Istruzione da accodare alla conversazione per rigenerare la risposta."""
        problems = "; ".join(issues)
        return (
            f"La risposta precedente ha questi problemi: {problems}. "
            f"Riscrivila correggendoli tutti. Mantieni identici i fatti e le "
            f"informazioni tratte dal contesto, cambia solo la forma. "
            f"Ricorda lo stile richiesto per il livello {user_level}."
        )


# ═══════════════════════════════════════════════════════════════════
#  PARTE 1 — DATA COLLECTION PER DPO (RLAIF)
# ═══════════════════════════════════════════════════════════════════

def load_chunk_pool() -> dict:
    """Carica tutti i chunk dai JSONL, raggruppati per livello di difficoltà."""
    pool = {"A": [], "B": [], "C": [], "D": []}
    for jsonl_path in CHUNKS_DIR.rglob("*.jsonl"):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                level = chunk.get("metadata", {}).get("difficulty_level")
                content = chunk.get("content", "")
                if level in pool and len(content) >= MIN_SOURCE_CHUNK_CHARS:
                    pool[level].append(chunk)
    return pool


def load_existing_ids() -> set:
    """ID delle triplette già salvate (per idempotenza/resume)."""
    ids = set()
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ids.add(json.loads(line)["id"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return ids


class TripletFactory:
    """Costruisce le triplette DPO usando la pipeline RAG reale del progetto."""

    def __init__(self):
        # Import locale per evitare il ciclo generation.py -> alignment.py
        from src.generation import RAGGenerator

        print(f"Oracolo (chosen): {ORACLE_MODEL} @ {ORACLE_BASE_URL}")
        print(f"Modello piccolo (rejected): {LLM_MODEL}\n")

        self.rag = RAGGenerator(model_name=LLM_MODEL)
        self.oracle = OpenAI(
            base_url=ORACLE_BASE_URL, api_key=ORACLE_API_KEY, timeout=600.0
        )

    # ── Chiamate ai modelli ────────────────────────────────────────
    def _chat(self, client, model, messages, temperature=0.3, retries=3):
        last_error = None
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model=model, messages=messages, temperature=temperature
                )
                return strip_thinking(response.choices[0].message.content)
            except Exception as e:
                last_error = e
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Chiamata a {model} fallita dopo {retries} tentativi: {last_error}")

    def _ask_oracle(self, messages, temperature=0.3):
        time.sleep(2)
        return self._chat(self.oracle, ORACLE_MODEL, messages, temperature)

    def _ask_small(self, messages, temperature=0.4):
        return self._chat(self.rag.client, self.rag.model_name, messages, temperature)

    # ── Generazione dei componenti della tripletta ─────────────────
    def generate_question(self, chunk: dict, user_level: str) -> str:
        """L'oracolo genera una domanda in italiano a cui il chunk risponde."""
        prompt = (
            "Sei un generatore di domande per un tutor di astrofisica.\n"
            "Leggi il passaggio e scrivi UNA sola domanda in ITALIANO che:\n"
            "- abbia una risposta completa nel passaggio;\n"
            f"- sia formulata come la porrebbe {AUDIENCE[user_level]};\n"
            "- sia autonoma: NON citare 'il testo', 'il passaggio' o 'l'autore'.\n"
            "Rispondi SOLO con la domanda, senza premesse né virgolette.\n\n"
            f"PASSAGGIO:\n{chunk['content'][:1500]}"
        )
        question = self._ask_oracle(
            [{"role": "user", "content": prompt}], temperature=0.7
        )
        # Teniamo solo la prima riga non vuota: qualche modello aggiunge note
        for line in question.splitlines():
            line = line.strip().strip('"').strip()
            if line:
                return line
        return ""

    def generate_chosen(self, prompt_messages: list) -> str:
        """Risposta ideale: l'oracolo riceve ESATTAMENTE il prompt di runtime."""
        return self._ask_oracle(prompt_messages, temperature=0.3)

    def generate_rejected_wrong_register(self, question, docs, user_level) -> str:
        """Risposta fedele al contesto ma con registro invertito."""
        inverted_level = "D" if user_level in ("A", "B") else "A"
        inverted_style = self.rag._get_system_instructions(inverted_level)
        context = "\n\n".join(
            f"[Fonte {i} - {d['title']}]:\n{d['text']}" for i, d in enumerate(docs, 1)
        )
        system = (
            "Sei un assistente didattico. Rispondi alla domanda basandoti sul "
            f"contesto fornito.\n\nSTILE DI RISPOSTA: {inverted_style}\n\n"
            f"CONTESTO:\n{context}"
        )
        return self._ask_small(
            [{"role": "system", "content": system},
             {"role": "user", "content": question}],
            temperature=0.4,
        )

    def generate_rejected_hallucination(self, question, user_level) -> str:
        """Risposta a memoria, sicura e ricca di dettagli non verificati."""
        style = self.rag._get_system_instructions(user_level)
        system = (
            "Sei un divulgatore scientifico. Rispondi alla domanda in modo "
            "sicuro e dettagliato usando la tua conoscenza generale. Non dire "
            f"mai che ti mancano informazioni.\n\nSTILE: {style}"
        )
        return self._ask_small(
            [{"role": "system", "content": system},
             {"role": "user", "content": question}],
            temperature=0.9,
        )

    # ── Assemblaggio ───────────────────────────────────────────────
    def build_triplet(self, strategy: str, question: str, user_level: str,
                      triplet_id: str, source_chunk: dict = None):
        """Costruisce una tripletta completa; None se non supera i controlli."""
        query_eng = self.rag._translate_query(question)
        docs = self.rag.retriever.search(
            [question, query_eng], user_level=user_level, initial_k=15, final_k=3
        )
        if not docs and strategy != "ood":
            return None

        prompt_messages = self.rag.build_prompt(question, docs, user_level)

        if strategy == "ood":
            chosen = REFUSAL_MESSAGE
            rejected = self.generate_rejected_hallucination(question, user_level)
            if REFUSAL_MESSAGE in rejected:
                return None  # il piccolo ha rifiutato da solo: coppia inutile
        else:
            chosen = self.generate_chosen(prompt_messages)
            # Se l'oracolo giudica il contesto insufficiente la domanda è
            # scadente: meglio scartare che addestrare su una chosen debole.
            if not chosen or REFUSAL_MESSAGE in chosen or len(chosen) < 100:
                return None
            if strategy == "wrong_register":
                rejected = self.generate_rejected_wrong_register(
                    question, docs, user_level
                )
            else:
                rejected = self.generate_rejected_hallucination(question, user_level)

        rejected = (rejected or "").strip()
        if not rejected or rejected == chosen:
            return None

        return {
            "id": triplet_id,
            "strategy": strategy,
            "user_level": user_level,
            "question": question,
            "prompt": prompt_messages,
            "chosen": [{"role": "assistant", "content": chosen}],
            "rejected": [{"role": "assistant", "content": rejected}],
            "sources": [d["title"] for d in docs],
            "context_levels": [d["level"] for d in docs],
            "source_chunk_file": (
                source_chunk["metadata"].get("source_file") if source_chunk else None
            ),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def collect_data(target: int, seed: int):
    random.seed(seed)

    print(f"Caricamento pool di chunk da {CHUNKS_DIR} ...")
    pool = load_chunk_pool()
    for level, chunks in pool.items():
        print(f"  Livello {level}: {len(chunks)} chunk candidati")

    existing = load_existing_ids()
    print(f"\nTriplette già presenti in {DATA_PATH.name}: {len(existing)}")
    if len(existing) >= target:
        print("Obiettivo già raggiunto, niente da fare.")
        return

    factory = TripletFactory()

    levels = ["A", "B", "C", "D"]
    strategies = list(STRATEGY_WEIGHTS.keys())
    weights = list(STRATEGY_WEIGHTS.values())
    ood_cycle = OOD_QUESTIONS.copy()
    random.shuffle(ood_cycle)

    stats = {s: 0 for s in strategies}
    skipped = 0
    count = len(existing)
    t0 = time.time()

    # Le triplette vengono accodate una per riga: interrompere è sempre sicuro
    with open(DATA_PATH, "a", encoding="utf-8") as out:
        while count < target:
            strategy = random.choices(strategies, weights=weights, k=1)[0]
            user_level = random.choice(levels)
            source_chunk = None

            if strategy == "ood":
                if not ood_cycle:
                    ood_cycle = OOD_QUESTIONS.copy()
                    random.shuffle(ood_cycle)
                question = ood_cycle.pop()
                triplet_id = hashlib.md5(
                    f"ood|{question}|{user_level}".encode("utf-8")
                ).hexdigest()
            else:
                # Preferisci un chunk del livello esatto, altrimenti adiacente
                from src.retrieval import LEVEL_FALLBACK
                candidate_levels = [
                    lv for lv in LEVEL_FALLBACK[user_level] if pool[lv]
                ]
                if not candidate_levels:
                    continue
                chunk_level = candidate_levels[0] if (
                    random.random() < 0.7 or len(candidate_levels) == 1
                ) else random.choice(candidate_levels[1:])
                source_chunk = random.choice(pool[chunk_level])
                chunk_hash = hashlib.md5(
                    source_chunk["content"].encode("utf-8")
                ).hexdigest()
                triplet_id = hashlib.md5(
                    f"{strategy}|{chunk_hash}|{user_level}".encode("utf-8")
                ).hexdigest()

            if triplet_id in existing:
                continue

            try:
                if strategy == "ood":
                    triplet = factory.build_triplet(
                        strategy, question, user_level, triplet_id
                    )
                else:
                    question = factory.generate_question(source_chunk, user_level)
                    if not question or len(question) < 15:
                        skipped += 1
                        continue
                    triplet = factory.build_triplet(
                        strategy, question, user_level, triplet_id, source_chunk
                    )
            except RuntimeError as e:
                print(f"\n✗ ERRORE: {e}")
                print("Controlla che Ollama sia attivo e che i modelli siano scaricati:")
                print(f"  ollama pull {ORACLE_MODEL.split('@')[0]}")
                print(f"  ollama pull {LLM_MODEL}")
                break

            existing.add(triplet_id)  # non riprovare la stessa combinazione
            if triplet is None:
                skipped += 1
                continue

            out.write(json.dumps(triplet, ensure_ascii=False) + "\n")
            out.flush()
            count += 1
            stats[strategy] += 1
            elapsed = time.time() - t0
            print(
                f"[{count}/{target}] {strategy:<15} livello {user_level} "
                f"— \"{triplet['question'][:60]}...\" ({elapsed:.0f}s)"
            )

    print(f"\n{'='*60}")
    print(f"Triplette totali nel file: {count}")
    print(f"Generate in questa sessione: {sum(stats.values())} "
          f"({', '.join(f'{k}: {v}' for k, v in stats.items())})")
    print(f"Scartate dai controlli qualità: {skipped}")
    print(f"Output: {DATA_PATH}")
    print("\nProssimo passo: caricare il file su Colab e lanciare")
    print("src/alignment_dpo_colab.ipynb per il training DPO (QLoRA + TRL).")


# ─── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera le triplette DPO {prompt, chosen, rejected} via RLAIF."
    )
    parser.add_argument(
        "--target", type=int, default=400,
        help="Numero totale di triplette da avere nel file (default: 400)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Seed per il campionamento riproducibile (default: 42)",
    )
    args = parser.parse_args()
    collect_data(target=args.target, seed=args.seed)
