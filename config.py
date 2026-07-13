import os

# Modello LLM per la generazione (utilizzato da generation.py, main.py, compare.py)
# Possibili opzioni per testare modelli meno potenti:
# - "qwen2.5:0.5b" (molto leggero, 500M parametri)
# - "qwen2.5:1.5b" (leggero, 1.5B parametri, raccomandato)
# - "qwen2.5:3b" (modello predefinito, 3B parametri)
# - "astrotutor-dpo" (qwen2.5:3b allineato con DPO, dopo `ollama create astrotutor-dpo`)
LLM_MODEL = "qwen2.5:3b"

# ─── Alignment (DPO / RLAIF) — usato da src/alignment.py ─────────────────
# L'oracolo genera le risposte "chosen" delle triplette DPO: deve essere un
# modello nettamente più grande di quello di produzione (8B+ locale o API).
# Default: Ollama locale. Per usare un'API esterna OpenAI-compatibile basta
# impostare le variabili d'ambiente, senza toccare il codice.
ORACLE_BASE_URL = os.environ.get("ORACLE_BASE_URL", "https://api.groq.com/openai/v1")
ORACLE_API_KEY = os.environ.get("ORACLE_API_KEY", "API_KEY")
ORACLE_MODEL = os.environ.get("ORACLE_MODEL", "llama-3.3-70b-versatile")
