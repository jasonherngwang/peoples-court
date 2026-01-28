import os

# Database Settings
DB_NAME = os.getenv("DB_NAME", "peoples_court")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

# Model IDs
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5")
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "gemini-2.5-flash")
JURY_MODEL_ID = os.getenv("JURY_MODEL_ID", "answerdotai/ModernBERT-large")
JURY_ADAPTER_PATH = os.getenv("JURY_ADAPTER_PATH", "./models/aita-classifier")

# Adjudication Parameters
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "256"))
K_PRECEDENTS = int(os.getenv("K_PRECEDENTS", "3"))
