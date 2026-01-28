import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the backend folder
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    # print(f"DEBUG: Loaded .env from {env_path}")
else:
    # Also try the root in case we are running a different way
    root_env = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(dotenv_path=root_env)
    # print(f"DEBUG: .env not found at {env_path}, tried {root_env}")

# Database Settings
DB_NAME = os.getenv("DB_NAME", "peoples_court")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

# print(f"DEBUG: Connecting to {DB_HOST} as {DB_USER}")
# Model IDs
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5")
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "gemini-2.5-flash")
JURY_MODEL_ID = os.getenv("JURY_MODEL_ID", "answerdotai/ModernBERT-large")
JURY_ADAPTER_PATH = os.getenv("JURY_ADAPTER_PATH", "./models/aita-classifier")

# Adjudication Parameters
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "256"))
K_PRECEDENTS = int(os.getenv("K_PRECEDENTS", "3"))
