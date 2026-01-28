import argparse
import logging
import os
import sys
import json
import random
from typing import List, Dict
import psycopg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def gen_dataset(db_name: str, output_file: str, target_max: int):
    """
    Fetches submissions with valid verdicts, balances the classes up to target_max,
    and writes the resulting dataset to a JSONL file.
    """
    try:
        conn = psycopg.connect(dbname=db_name)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return

    cur = conn.cursor()

    logger.info("Fetching submissions...")
    try:
        cur.execute(
            "SELECT title, selftext, verdict FROM submissions WHERE verdict IN ('YTA', 'NTA', 'ESH', 'NAH') AND selftext NOT IN ('[removed]', '[deleted]', '', ' ')"
        )
        rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch submissions: {e}")
        cur.close()
        conn.close()
        return

    data_by_class: Dict[str, List[Dict]] = {"YTA": [], "NTA": [], "ESH": [], "NAH": []}
    for title, selftext, verdict in rows:
        data_by_class[verdict].append(
            {"text": f"{title}\n\n{selftext}", "label": verdict}
        )

    final_data: List[Dict] = []
    for label in ["YTA", "NTA", "ESH", "NAH"]:
        items = data_by_class[label]
        if len(items) > target_max:
            items = random.sample(items, target_max)
        final_data.extend(items)

    random.shuffle(final_data)

    logger.info(f"Writing {len(final_data)} samples to {output_file}...")
    try:
        with open(output_file, "w") as f:
            for entry in final_data:
                f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write output file: {e}")

    logger.info("Dataset generation complete.")
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate balanced training dataset from Reddit AITA data."
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_NAME", "peoples_court"),
        help="PostgreSQL database name",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("OUTPUT_FILE", "training_data.jsonl"),
        help="Output JSONL file path",
    )
    parser.add_argument(
        "--max-per-class",
        type=int,
        default=int(os.getenv("TARGET_MAX", "15000")),
        help="Maximum samples per verdict class",
    )

    args = parser.parse_args()

    gen_dataset(
        db_name=args.db,
        output_file=args.output,
        target_max=args.max_per_class,
    )


if __name__ == "__main__":
    main()
