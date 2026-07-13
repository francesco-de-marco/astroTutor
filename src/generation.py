import os
from pathlib import Path
from src.retrieval import AdvancedRetriever
from src.alignment import ResponseGuardrails, REFUSAL_MESSAGE
from openai import OpenAI
try:
    from config import LLM_MODEL
except ImportError:
    LLM_MODEL = "qwen2.5:3b"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class RAGGenerator:
    def __init__(self, model_name=LLM_MODEL):
        print(f"Inizializzazione Generatore RAG con modello locale: {model_name}...")
        self.retriever = AdvancedRetriever()
        
        # Configurazione Client per Ollama (porta standard 11434)
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama", # Ignorata da Ollama, ma richiesta dalla libreria
        )
        self.model_name = model_name
        self.guardrails = ResponseGuardrails()

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
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, # Temperatura 0 per avere zero creatività e massima precisione
                frequency_penalty=0.6,  # Previene i loop ma permette le formule.
                presence_penalty=0.5    # Lo spinge a usare vocaboli nuovi nelle spiegazioni.
            )
            return response.choices[0].message.content.strip()
        except:
            return query # Fallback in caso di errore

    def _apply_guardrails(self, answer: str, messages: list, user_level: str) -> str:
        """
        Controlla tono/registro della risposta rispetto al livello utente.
        Se i guardrail segnalano problemi, rigenera UNA volta con l'istruzione
        correttiva e tiene la versione con meno problemi. Mai bloccante.
        """
        issues = self.guardrails.check(answer, user_level)
        if not issues:
            return answer

        print(f"🛡️ Guardrails ({user_level}): {'; '.join(issues)} — rigenero...")
        retry_messages = messages + [
            {"role": "assistant", "content": answer},
            {"role": "user", "content": self.guardrails.corrective_instruction(issues, user_level)},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=retry_messages,
                temperature=0.1,
                frequency_penalty=0.6,
                presence_penalty=0.5,
            )
            new_answer = response.choices[0].message.content
        except Exception:
            return answer  # la rigenerazione è best-effort

        new_issues = self.guardrails.check(new_answer, user_level)
        if len(new_issues) < len(issues):
            return new_answer
        print("🛡️ Guardrails: la rigenerazione non ha migliorato, tengo l'originale.")
        return answer

    def generate(self, query: str, user_level: str = "B"):
        print(f"🔄 Generazione varianti di ricerca...")
        query_eng = self._translate_query(query)
        queries_to_search = [query, query_eng]

        print(f"🔍 Ricerca documenti per livello {user_level}...")
        results = self.retriever.search(queries_to_search, user_level=user_level, initial_k=15, final_k=3)
        
        if not results:
            return "Mi dispiace, non ho trovato informazioni utili nei miei documenti per rispondere."

        # Controllo di sicurezza sui punteggi del re-ranker
        if results[0]['score'] < -5.0:  # Soglia indicativa per punteggi logit estremamente bassi
             print("⚠️ Avviso: I documenti trovati hanno una bassa pertinenza.")

        messages = self.build_prompt(query, results, user_level)

        print(f"🧠 Generazione risposta con {self.model_name}...")
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1, 
                frequency_penalty=0.6,
                presence_penalty=0.5,
            )
            
            answer = response.choices[0].message.content
            answer = self._apply_guardrails(answer, messages, user_level)

            # Aggiunta fonti univoche
            fonti = set([f"- {r['title']} ({r['source']})" for r in results])
            sources_text = "\n\n---\n**Fonti utilizzate:**\n" + "\n".join(fonti)
            
            return answer + sources_text

        except Exception as e:
            return f"Errore durante la generazione: {str(e)}"

    def generate_without_rag(self, query: str, user_level: str = "B"):
        """
        Genera una risposta usando SOLO la conoscenza interna del modello (Baseline),
        senza fare retrieval dal database vettoriale.
        """
        level_style = self._get_system_instructions(user_level)

        system_prompt = (
            "Sei un assistente didattico intelligente.\n\n"
            f"STILE DI RISPOSTA: {level_style}\n\n"
            "Rispondi alla domanda dell'utente usando la tua conoscenza generale."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        print(f"🧠 Generazione risposta BASELINE (Senza RAG) con {self.model_name}...")
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1, 
                frequency_penalty=0.6,
                presence_penalty=0.5,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Errore durante la generazione: {str(e)}"