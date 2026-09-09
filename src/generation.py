"""Generazione RAG con tracciamento delle risposte prima/dopo i guardrail."""
import hashlib
import json
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI
from src.retrieval import AdvancedRetriever
from src.alignment import ResponseGuardrails, REFUSAL_MESSAGE
from config import LLM_MODEL

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class RAGGenerator:
    def __init__(
        self, model_name=LLM_MODEL, *, guardrails_enabled=True,
        temperature=0.1, seed=42, initial_k=15, final_k=3,
        translation_model=LLM_MODEL,
        base_url="http://localhost:11434/v1", log_path=None,
        retriever=None, client=None,
    ):
        self.model_name = model_name
        self.translation_model = translation_model
        self.base_url = base_url
        self.guardrails_enabled = guardrails_enabled
        self.initial_k = initial_k
        self.final_k = final_k
        self.log_path = Path(log_path) if log_path is not None else None
        self.generation_config = {
            "temperature": temperature,
            "seed": seed,
            "frequency_penalty": 0.6,
            "presence_penalty": 0.5,
        }
        self.guardrails = ResponseGuardrails()
        # Il retriever viene caricato solo quando serve una ricerca.
        self._retriever = retriever
        self.client = client if client is not None else OpenAI(
            base_url=base_url, api_key="ollama", timeout=900.0,
        )

    @property
    def retriever(self):
        if self._retriever is None:
            self._retriever = AdvancedRetriever()
        return self._retriever

    @retriever.setter
    def retriever(self, value):
        self._retriever = value

    def _chat(self, messages):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **self.generation_config,
        )
        answer = response.choices[0].message.content
        if not answer or not answer.strip():
            raise RuntimeError("Il modello ha restituito una risposta vuota.")
        return answer.strip()

    def _get_system_instructions(self, user_level: str) -> str:
        instructions = {
            "A": "Spiega come se parlassi a un bambino di 6-10 anni. Usa analogie semplici, un tono molto dolce e termini elementari.",
            "B": "Spiega come se parlassi a uno studente delle medie. Sii chiaro, evita formule troppo complesse ma usa i nomi corretti dei concetti.",
            "C": "Spiega come se parlassi a uno studente delle superiori. Usa un linguaggio tecnico corretto e approfondisci i nessi logici.",
            "D": "Spiega a livello universitario. Sii rigoroso, cita dettagli fisici o matematici se presenti nel testo e usa un tono accademico."
        }
        return instructions.get(user_level, "Sii un tutor chiaro e preciso.")

    def build_prompt(self, query: str, docs: list, user_level: str):
        context_parts = []
        for i, doc in enumerate(docs, 1):
            context_parts.append(f"[Fonte {i} - {doc['title']}]:\n{doc['text']}")
        
        context_text = "\n\n".join(context_parts)
        level_style = self._get_system_instructions(user_level)

        system_prompt = (
            "Sei un assistente didattico scientifico. Il tuo compito è estrarre informazioni "
            "dai documenti forniti.\n\n"
            "⚠️ REGOLE ASSOLUTE E INVIOLABILI:\n"
            "1. Cerca la risposta SOLO all'interno del CONTESTO fornito.\n"
            "2. Se il CONTESTO non contiene la risposta esatta o non ne parla, DEVI rispondere "
            f"ESATTAMENTE con: '{REFUSAL_MESSAGE}' "
            "Non aggiungere altre spiegazioni, scuse o storielle.\n"
            "3. NON INVENTARE nulla. Non usare la tua conoscenza pregressa. Non creare "
            "analogie o metafore che non siano già scritte nel testo.\n\n"
            f"STILE DI RISPOSTA:\nSe (e SOLO SE) trovi la risposta nel contesto, esponila "
            f"seguendo questa regola di stile: {level_style}\n\n"
            "CONTESTO RECUPERATO:\n"
            f"{context_text}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

    def _translate_query(self, query: str) -> str:
        """Usa Qwen per tradurre la query nella lingua opposta (ITA <-> ENG)."""
        prompt = (
            "Sei un traduttore automatico di altissima precisione.\n"
            "Regole:\n"
            "- Se la frase fornita è in ITALIANO, traducila in INGLESE.\n"
            "- Se la frase fornita è in INGLESE, traducila in ITALIANO.\n"
            "- Rispondi ESCLUSIVAMENTE con la traduzione. Non aggiungere virgolette, "
            "non dire 'Ecco la traduzione:' e non aggiungere note.\n\n"
            f"Frase: {query}"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.translation_model,
                messages=[{"role": "user", "content": prompt}],
                **self.generation_config,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return query # Fallback in caso di errore


    def _guardrail_result(self, answer, messages, user_level, enabled):
        issues = self.guardrails.check(answer, user_level)
        result = {
            "enabled": enabled,
            "attempted": False,
            "changed": False,
            "issues_before": issues,
            "issues_after": list(issues),
            "retry_answer": None,
            "retry_issues": None,
            "retry_error": None,
            "final_answer": answer,
        }
        if not enabled or not issues:
            return result
        result["attempted"] = True
        retry_messages = messages + [
            {"role": "assistant", "content": answer},
            {"role": "user", "content":
             self.guardrails.corrective_instruction(issues, user_level)},
        ]
        try:
            candidate = self._chat(retry_messages)
            candidate_issues = self.guardrails.check(candidate, user_level)
            result["retry_answer"] = candidate
            result["retry_issues"] = candidate_issues
            if len(candidate_issues) < len(issues):
                result["final_answer"] = candidate
                result["issues_after"] = candidate_issues
                result["changed"] = candidate != answer
        except Exception as exc:
            result["retry_error"] = str(exc)
        return result

    def _apply_guardrails(self, answer, messages, user_level):
        """Interfaccia compatibile con il vecchio evaluation.py."""
        return self._guardrail_result(
            answer, messages, user_level, self.guardrails_enabled,
        )["final_answer"]

    def generate_record(
        self, query, user_level="B", *, docs=None, use_rag=True,
        guardrails_enabled=None,
    ):
        """Restituisce un record; se log_path è impostato lo accoda in JSONL.

        docs=None esegue retrieval; docs=[] usa un contesto vuoto.
        Passare gli stessi docs a tutti i modelli per un confronto controllato.
        Gli errori della generazione primaria vengono propagati.
        """
        if user_level not in ("A", "B", "C", "D"):
            raise ValueError("user_level deve essere A, B, C o D.")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("La domanda deve essere una stringa non vuota.")
        if not use_rag and docs is not None:
            raise ValueError("Non passare docs quando use_rag=False.")

        started = time.perf_counter()
        enabled = (self.guardrails_enabled if guardrails_enabled is None
                   else guardrails_enabled)
        queries = None
        if use_rag:
            if docs is None:
                queries = [query, self._translate_query(query)]
                docs = self.retriever.search(
                    queries, user_level=user_level,
                    initial_k=self.initial_k, final_k=self.final_k,
                )
                context_origin = "retrieval"
            else:
                context_origin = "provided"
            docs = deepcopy(docs)
            messages = self.build_prompt(query, docs, user_level)
        else:
            context_origin = "none"
            docs = []
            messages = [
                {"role": "system", "content": (
                    "Sei un assistente didattico intelligente.\n\n"
                    f"STILE DI RISPOSTA: {self._get_system_instructions(user_level)}\n\n"
                    "Rispondi alla domanda dell'utente usando la tua conoscenza generale."
                )},
                {"role": "user", "content": query},
            ]

        # Registra esplicitamente il rifiuto imposto dalla pipeline,
        # distinguendolo da una risposta prodotta dal modello.
        model_called = not (use_rag and not docs)
        raw_answer = self._chat(messages) if model_called else REFUSAL_MESSAGE
        guard = self._guardrail_result(raw_answer, messages, user_level, enabled)
        config = {
            "model": self.model_name,
            "base_url": self.base_url,
            "translation_model": self.translation_model,
            "generation": dict(self.generation_config),
            "initial_k": self.initial_k,
            "final_k": self.final_k,
            "use_rag": use_rag,
            "guardrails_enabled": enabled,
        }
        prompt_json = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        record = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "question": query,
            "level": user_level,
            "model": self.model_name,
            "config": config,
            "messages": messages,
            "prompt_hash": hashlib.sha256(prompt_json.encode("utf-8")).hexdigest(),
            "retrieved_docs": docs,
            "context_origin": context_origin,
            "retrieval_queries": queries,
            "model_called": model_called,
            "raw_answer": raw_answer,
            "final_answer": guard["final_answer"],
            "guardrails": guard,
            "elapsed_seconds": time.perf_counter() - started,
        }
        if self.log_path is not None:
            # Serializza prima di aprire il file: evita righe parziali
            # in caso di metadati non serializzabili.
            line = json.dumps(record, ensure_ascii=False, allow_nan=False)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
        return record

    def generate(self, query: str, user_level: str = "B"):
        """Mantiene il ritorno stringa usato da main.py e compare.py."""
        try:
            record = self.generate_record(query, user_level)
            answer = record["final_answer"]
            sources = sorted({
                f"- {doc['title']} ({doc.get('source', 'fonte non indicata')})"
                for doc in record["retrieved_docs"]
            })
            if sources:
                answer += "\n\n---\n**Fonti recuperate:**\n" + "\n".join(sources)
            return answer
        except Exception as exc:
            return f"Errore durante la generazione: {exc}"

    def generate_without_rag(self, query: str, user_level: str = "B"):
        """Mantiene il ritorno stringa e l'assenza di guardrail della baseline."""
        try:
            return self.generate_record(
                query, user_level, use_rag=False, guardrails_enabled=False,
            )["final_answer"]
        except Exception as exc:
            return f"Errore durante la generazione: {exc}"
