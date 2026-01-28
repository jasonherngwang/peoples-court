import argparse
import logging
import os
import sys
from typing import List, Tuple
from peoples_court.db import Database
from peoples_court.models import Embedder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def embed(
    db_name: str,
    model_name: str,
    dim: int,
    batch_size: int,
):
    """
    Fetches submissions with valid verdicts that lack embeddings,
    encodes them using the specified model, and stores the vectors.
    """
    db = Database(dbname=db_name)
    try:
        embedder = Embedder(model_id=model_name)
    except Exception as e:
        logger.error(f"Failed to initialize embedder: {e}")
        return

    try:
        conn = db.connect()
        cur = conn.cursor()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return

    logger.info("Fetching submissions without embeddings...")
    try:
        cur.execute("""
            SELECT s.id, s.title, s.selftext 
            FROM submissions s
            LEFT JOIN embeddings e ON s.id = e.submission_id
            WHERE e.submission_id IS NULL
            AND s.verdict IN ('YTA', 'NTA', 'ESH', 'NAH')
        """)
        rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch submissions: {e}")
        db.close()
        return

    total_rows = len(rows)
    logger.info(f"Total to embed: {total_rows}")

    updates: List[Tuple] = []
    for i, (sub_id, title, text) in enumerate(rows):
        full_text = f"{title}\n\n{text}"
        try:
            vector = embedder.encode(full_text, dim=dim)
            updates.append((sub_id, vector))
        except Exception as e:
            logger.error(f"Failed to encode submission {sub_id}: {e}")
            continue

        if len(updates) >= batch_size:
            try:
                cur.executemany(
                    "INSERT INTO embeddings (submission_id, vector) VALUES (%s, %s)",
                    updates,
                )
                conn.commit()
                updates = []
                logger.info(f"  Embedded {i + 1}/{total_rows}...")
            except Exception as e:
                logger.error(f"Failed to insert batch: {e}")
                conn.rollback()
                updates = []

    if updates:
        try:
            cur.executemany(
                "INSERT INTO embeddings (submission_id, vector) VALUES (%s, %s)",
                updates,
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert final batch: {e}")
            conn.rollback()

    logger.info("Embedding process complete.")
    db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for Reddit AITA data."
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_NAME", "peoples_court"),
        help="PostgreSQL database name",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("EMBED_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5"),
        help="Embedding model name",
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=int(os.getenv("EMBEDDING_DIM", "256")),
        help="Embedding dimensions",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("BATCH_SIZE", "100")),
        help="Processing batch size",
    )

    args = parser.parse_args()

    embed(
        db_name=args.db,
        model_name=args.model,
        dim=args.dim,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
