import os
from dotenv import load_dotenv
from pathlib import Path

backend_root = Path(__file__).parent.parent.parent
env_local = backend_root / ".env.local"
env_main = backend_root / ".env"

# Load .env first
if env_main.exists():
    load_dotenv(dotenv_path=env_main)

# Load .env.local second with override=True to prioritize local settings
if env_local.exists():
    load_dotenv(dotenv_path=env_local, override=True)

DB_NAME = os.getenv("DB_NAME", "peoples_court")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5")
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "gemini-2.5-flash-lite")
JURY_MODEL_ID = os.getenv("JURY_MODEL_ID", "answerdotai/ModernBERT-large")
JURY_ADAPTER_PATH = os.getenv("JURY_ADAPTER_PATH", "./models/aita-classifier")

# Adjudication Parameters
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "256"))
K_PRECEDENTS = int(os.getenv("K_PRECEDENTS", "3"))
