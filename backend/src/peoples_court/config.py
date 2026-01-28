import os

# Database Settings
DB_NAME = os.getenv("DB_NAME", "peoples_court")

# Model IDs
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5")
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "gemini-2.5-flash")
JURY_MODEL_ID = os.getenv("JURY_MODEL_ID", "answerdotai/ModernBERT-large")
JURY_ADAPTER_PATH = os.getenv("JURY_ADAPTER_PATH", "./models/aita-classifier")

# Adjudication Parameters
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "256"))
K_PRECEDENTS = int(os.getenv("K_PRECEDENTS", "3"))
