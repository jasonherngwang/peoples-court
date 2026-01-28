import argparse
import logging
import os
import sys
import time
from peoples_court.db import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run_benchmark(
    db_name: str,
    keyword_query: str,
    limit: int = 5,
):
    """
    Performance benchmark for hybrid search (Vector + BM25).

    Args:
        db_name: PostgreSQL database name.
        keyword_query: Query string for keyword search benchmarking.
        limit: Number of results to fetch per search.
    """
    db = Database(dbname=db_name)
    logger.info("--- Performance Benchmark ---")

    try:
        with db.get_cursor() as cur:
            # Fetch a sample vector for testing parity
            cur.execute("SELECT vector FROM embeddings LIMIT 1")
            row = cur.fetchone()
            sample_vector = row[0] if row else None

            if not sample_vector:
                logger.warning("No vectors found in DB. Vector benchmark skipped.")
            else:
                # 1. Vector Search Benchmark
                logger.info(f"1. Benchmarking Vector Search (Top {limit})...")
                start = time.time()
                cur.execute(
                    """
                    SELECT submission_id, 1 - (vector <=> %s::vector) as similarity 
                    FROM embeddings 
                    ORDER BY similarity DESC 
                    LIMIT %s
                    """,
                    (sample_vector, limit),
                )
                results = cur.fetchall()
                duration = time.time() - start
                logger.info(f"   Time taken: {duration:.4f}s")
                for sub_id, sim in results:
                    logger.info(f"   - Match: {sub_id} (Sim: {sim:.4f})")

            # 2. Keyword Search Benchmark
            logger.info(f"\n2. Benchmarking Keyword Search ('{keyword_query}')...")
            start = time.time()
            # Note: ParadeDB bm25 search
            cur.execute(
                """
                SELECT id, paradedb.score(submissions) as bm25_score
                FROM submissions
                WHERE submissions @@@ %s
                ORDER BY bm25_score DESC
                LIMIT %s
                """,
                (f"title:({keyword_query}) OR selftext:({keyword_query})", limit),
            )
            results = cur.fetchall()
            duration = time.time() - start
            logger.info(f"   Time taken: {duration:.4f}s")
            for sub_id, score in results:
                logger.info(f"   - Match: {sub_id} (Score: {score:.2f})")

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark vector and keyword search performance."
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_NAME", "peoples_court"),
        help="PostgreSQL database name",
    )
    parser.add_argument(
        "--query",
        default="sourdough",
        help="Keyword query for BM25 benchmark",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of results to benchmark",
    )

    args = parser.parse_args()
    run_benchmark(db_name=args.db, keyword_query=args.query, limit=args.limit)


if __name__ == "__main__":
    main()
