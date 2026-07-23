import os
from dotenv import load_dotenv

load_dotenv()

# Modello LLM per la generazione (utilizzato da generation.py, main.py, compare.py)
# - "qwen2.5:3b" (modello predefinito, 3B parametri)
# - "astrotutor-dpo" (qwen2.5:3b allineato con DPO, dopo `ollama create astrotutor-dpo`)
LLM_MODEL = "qwen2.5:3b"

# Alignment (DPO / RLAIF) — usato da src/alignment.py
# L'oracolo genera le risposte "chosen" delle triplette DPO
ORACLE_BASE_URL = os.environ.get("ORACLE_BASE_URL", "https://api.groq.com/openai/v1")
ORACLE_API_KEY = os.environ.get("ORACLE_API_KEY")
ORACLE_MODEL = os.environ.get("ORACLE_MODEL", "llama-3.3-70b-versatile")

if ORACLE_API_KEY is None:
    raise ValueError(
        "ORACLE_API_KEY non impostata. Controlla il file .env nella root del progetto."
    )