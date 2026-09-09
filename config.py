import os
from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:3b")

ORACLE_BASE_URL = os.environ.get(
    "ORACLE_BASE_URL",
    "https://api.groq.com/openai/v1"
)

ORACLE_API_KEY = os.environ.get("ORACLE_API_KEY")

ORACLE_MODEL = os.environ.get(
    "ORACLE_MODEL",
    "llama-3.3-70b-versatile"
)


def require_oracle_key() -> str:
    """
    Restituisce la chiave Oracle solo quando è realmente necessaria.
    Gli import locali e la valutazione senza Oracle possono funzionare
    anche senza variabile d'ambiente.
    """
    if not ORACLE_API_KEY:
        raise RuntimeError(
            "ORACLE_API_KEY non impostata. "
            "Inseriscila nel file .env prima di generare dati Oracle."
        )
    return ORACLE_API_KEY