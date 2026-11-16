"""Load runtime settings from .env (never commit .env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]
DAY6_STRATEGY = os.getenv("DAY6_STRATEGY", "B")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embeddinggemma")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MAX_COST_USD = float(os.getenv("MAX_COST_USD", "1.0"))
LLM_PRICE_IN_PER_M = float(os.getenv("LLM_PRICE_IN_PER_M", "0.20"))
LLM_PRICE_OUT_PER_M = float(os.getenv("LLM_PRICE_OUT_PER_M", "1.20"))
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "low")
COST_LEDGER = ROOT / "results" / "cost_ledger.jsonl"
