"""
Valutazione — Fase 6 del progetto.

Confronta qwen2.5:3b (baseline) e astrotutor-dpo (allineato) sullo stesso
pipeline RAG, su tre assi:
  - Gulpease: leggibilità della risposta rispetto al livello richiesto
  - Faithfulness (RAGAS): quanto la risposta è supportata dal contesto
    recuperato, valutata da un LLM giudice locale (JUDGE_MODEL via Ollama)
  - Tasso di rifiuto corretto sulle domande OOD (fuori dominio)

Il giudice gira in locale (non l'oracolo Groq) per due motivi: la quota
gratuita di Groq si esaurisce troppo in fretta per ~80 chiamate di verifica,
e un giudizio di faithfulness è un confronto relativo tra due modelli — non
serve la stessa potenza usata per generare le "chosen" di training.

Uso:  python src/evaluation.py
Output: data/eval_results.json (dettaglio per domanda) + riepilogo a video.
"""
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness

from src.generation import RAGGenerator
from src.alignment import ResponseGuardrails, OOD_QUESTIONS, REFUSAL_MESSAGE

MODELS = ["qwen2.5:3b", "astrotutor-dpo"]
JUDGE_MODEL = "qwen2.5:7b-instruct"
JUDGE_BASE_URL = "http://localhost:11434/v1"
EVAL_QUESTIONS_PATH = PROJECT_ROOT / "data" / "eval_questions.json"
RESULTS_PATH = PROJECT_ROOT / "data" / "eval_results.json"

LEVELS = ["A", "B", "C", "D"]


def generate_with_docs(rag: RAGGenerator, query: str, user_level: str):
    """Come RAGGenerator.generate(), ma restituisce anche i documenti
    recuperati e la risposta grezza (senza il blocco 'Fonti utilizzate'),
    necessari per il judge di faithfulness."""
    query_eng = rag._translate_query(query)
    docs = rag.retriever.search(
        [query, query_eng], user_level=user_level, initial_k=15, final_k=3
    )
    if not docs:
        return REFUSAL_MESSAGE, []

    messages = rag.build_prompt(query, docs, user_level)
    response = rag.client.chat.completions.create(
        model=rag.model_name,
        messages=messages,
        temperature=0.1,
        frequency_penalty=0.6,
        presence_penalty=0.5,
    )
    answer = response.choices[0].message.content
    answer = rag._apply_guardrails(answer, messages, user_level)
    return answer, docs


def evaluate_ood(rag: RAGGenerator) -> dict:
    """Tasso di rifiuto corretto sulle domande fuori dominio."""
    correct = 0
    details = []
    for q in OOD_QUESTIONS:
        answer, _docs = generate_with_docs(rag, q, "B")
        is_refusal = REFUSAL_MESSAGE in answer
        correct += int(is_refusal)
        details.append({"question": q, "refused": is_refusal, "answer": answer})
    return {
        "refusal_rate": correct / len(OOD_QUESTIONS),
        "correct": correct,
        "total": len(OOD_QUESTIONS),
        "details": details,
    }


def _progress_path(model_name: str) -> Path:
    safe_name = model_name.replace(":", "_").replace("/", "_")
    return PROJECT_ROOT / "data" / f"eval_progress_{safe_name}.jsonl"


def _load_progress(model_name: str) -> dict:
    """Risultati già calcolati per questo modello, indicizzati per domanda —
    permette di riprendere dopo un crash (es. rate-limit del judge) senza
    ripetere le chiamate già pagate/fatte."""
    path = _progress_path(model_name)
    done = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                done[r["question"]] = r
    return done


async def evaluate_grounded(rag: RAGGenerator, questions: list, faithfulness, model_name: str) -> list:
    """Gulpease + faithfulness su tutte le domande con contesto disponibile.
    Salva ogni risultato subito su disco (JSONL, append+flush): un crash a
    metà (es. quota del judge esaurita) non fa perdere il lavoro già fatto,
    e un rilancio riprende da dove si era interrotto."""
    done = _load_progress(model_name)
    results = list(done.values())
    if done:
        print(f"  Ripresa: {len(done)} risultati già presenti, li salto")

    progress_path = _progress_path(model_name)
    with open(progress_path, "a", encoding="utf-8") as progress_out:
        for item in questions:
            level = item["level"]
            question = item["question"]
            if question in done:
                continue

            answer, docs = generate_with_docs(rag, question, level)
            gulpease = ResponseGuardrails.gulpease(answer)

            if docs:
                contexts = [d["text"] for d in docs]
                score = await faithfulness.ascore(
                    user_input=question, response=answer, retrieved_contexts=contexts
                )
                faithfulness_score = score.value
            else:
                faithfulness_score = None

            result = {
                "level": level,
                "question": question,
                "answer": answer,
                "gulpease": gulpease,
                "faithfulness": faithfulness_score,
            }
            results.append(result)
            progress_out.write(json.dumps(result, ensure_ascii=False) + "\n")
            progress_out.flush()

            print(f"  [{level}] gulpease={gulpease:.1f} "
                  f"faithfulness={faithfulness_score if faithfulness_score is None else round(faithfulness_score, 2)} "
                  f"— {question[:60]}")
    return results


def summarize(model_name: str, grounded_results: list, ood_result: dict) -> dict:
    summary = {"model": model_name, "per_level": {}, "ood_refusal_rate": ood_result["refusal_rate"]}
    for level in LEVELS:
        level_items = [r for r in grounded_results if r["level"] == level]
        gulpease_vals = [r["gulpease"] for r in level_items]
        faith_vals = [r["faithfulness"] for r in level_items if r["faithfulness"] is not None]
        summary["per_level"][level] = {
            "n": len(level_items),
            "gulpease_mean": sum(gulpease_vals) / len(gulpease_vals) if gulpease_vals else None,
            "faithfulness_mean": sum(faith_vals) / len(faith_vals) if faith_vals else None,
        }
    return summary


def print_summary_table(summaries: list):
    print("\n" + "=" * 70)
    print("RIEPILOGO VALUTAZIONE")
    print("=" * 70)
    for s in summaries:
        print(f"\nModello: {s['model']}")
        print(f"  Tasso di rifiuto OOD corretto: {s['ood_refusal_rate']*100:.1f}%")
        print(f"  {'Livello':<8}{'N':<5}{'Gulpease medio':<18}{'Faithfulness medio':<20}")
        for level in LEVELS:
            d = s["per_level"][level]
            g = f"{d['gulpease_mean']:.1f}" if d["gulpease_mean"] is not None else "n/d"
            f = f"{d['faithfulness_mean']:.2f}" if d["faithfulness_mean"] is not None else "n/d"
            print(f"  {level:<8}{d['n']:<5}{g:<18}{f:<20}")


async def main():
    with open(EVAL_QUESTIONS_PATH, encoding="utf-8") as f:
        questions = json.load(f)

    # timeout generoso: il giudice locale (7B, in parte su CPU) può metterci
    # oltre un minuto a chiamata, soprattutto in concorrenza con altri
    # processi Ollama in esecuzione
    judge_client = AsyncOpenAI(base_url=JUDGE_BASE_URL, api_key="ollama", timeout=300.0)
    # max_tokens generoso: il passaggio di verifica di faithfulness elenca un
    # verdetto per ogni affermazione della risposta rispetto al contesto — con
    # risposte lunghe o più fonti recuperate il default troncava l'output
    # strutturato (IncompleteOutputException).
    judge_llm = llm_factory(
        JUDGE_MODEL, provider="openai", client=judge_client, max_tokens=8192
    )
    faithfulness = Faithfulness(llm=judge_llm)

    all_summaries = []
    all_details = {}

    for model_name in MODELS:
        print(f"\n{'#'*70}\nValutazione modello: {model_name}\n{'#'*70}")
        rag = RAGGenerator(model_name=model_name)

        print("\n-- Domande con contesto (Gulpease + faithfulness) --")
        grounded_results = await evaluate_grounded(rag, questions, faithfulness, model_name)

        print("\n-- Domande OOD (tasso di rifiuto) --")
        ood_result = evaluate_ood(rag)
        print(f"  Rifiuti corretti: {ood_result['correct']}/{ood_result['total']}")

        summary = summarize(model_name, grounded_results, ood_result)
        all_summaries.append(summary)
        all_details[model_name] = {
            "grounded": grounded_results,
            "ood": ood_result,
            "summary": summary,
        }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    print(f"\nDettaglio completo salvato in: {RESULTS_PATH}")

    print_summary_table(all_summaries)


if __name__ == "__main__":
    asyncio.run(main())
