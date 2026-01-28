import json
import heapq
import zstandard as zstd
import argparse
import logging
import os
import sys
from typing import Generator, Set, List, Tuple, Dict
import psycopg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BOT_AUTHORS: Set[str] = {
    "AutoModerator",
    "AITA-Bot",
    "JudgementBot",
    "AITA-Verdict-Bot",
    "[deleted]",
    "[removed]",
}

REMOVE_MARKERS: Set[str] = {"[removed]", "[deleted]", None, ""}


def stream_zst_lines(file_path: str) -> Generator[str, None, None]:
    """
    Streams decompressed lines from a .zst file without loading the entire file into memory.
    Uses a larger window size for high-compression Reddit archives and a 16MB buffer.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    try:
        with open(file_path, "rb") as f:
            dctx = zstd.ZstdDecompressor(max_window_size=2147483648)
            with dctx.stream_reader(f) as reader:
                previous_line = ""
                while True:
                    chunk = reader.read(2**24)  # 16MB chunks
                    if not chunk:
                        break

                    # Decoded with 'ignore' to handle potential corruption in partial chunks
                    decoded = previous_line + chunk.decode("utf-8", errors="ignore")
                    lines = decoded.split("\n")
                    previous_line = lines[-1]

                    for line in lines[:-1]:
                        if line:
                            yield line
    except Exception as e:
        logger.error(f"Error streaming {file_path}: {e}")


def get_existing_ids(cur: psycopg.Cursor) -> Set[str]:
    """Retrieves all existing submission IDs to prevent duplicate processing."""
    logger.info("Checking existing submissions in database...")
    try:
        cur.execute("SELECT id FROM submissions")
        return {row[0] for row in cur.fetchall()}
    except Exception as e:
        logger.error(f"Failed to fetch existing IDs: {e}")
        return set()


def ingest(
    submissions_path: str,
    comments_path: str,
    db_name: str,
    min_score: int,
    batch_size: int,
):
    """
    Two-pass ingestion process:
    1. Filter and insert submissions based on quality heuristics (score, non-empty, non-bot).
    2. Stream comments and use min-heaps to keep only the top 3 comments per submission,
       ensuring we only store high-signal data.
    """
    try:
        conn = psycopg.connect(dbname=db_name)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)

    cur = conn.cursor()
    existing_ids = get_existing_ids(cur)
    logger.info(f"Loaded {len(existing_ids)} existing submission IDs.")

    # Pass 1: Submissions
    logger.info(f"Starting Pass 1: Submissions from {submissions_path}")
    rows: List[Tuple] = []
    inserted_count = 0

    for line in stream_zst_lines(submissions_path):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        sub_id = data.get("id")
        if not sub_id or sub_id in existing_ids or data.get("score", 0) < min_score:
            continue

        # Quality filters: exclude removed/deleted/empty posts and non-self posts
        if data.get("selftext") in REMOVE_MARKERS or not data.get("is_self"):
            continue

        if data.get("author") in BOT_AUTHORS:
            continue

        existing_ids.add(sub_id)
        rows.append(
            (
                sub_id,
                data.get("author"),
                data.get("title"),
                data.get("selftext"),
                data.get("score"),
                data.get("upvote_ratio"),
                data.get("link_flair_text"),
                data.get("created_utc"),
                data.get("permalink"),
                None,  # Placeholder for processed state
            )
        )

        if len(rows) >= batch_size:
            cur.executemany(
                "INSERT INTO submissions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                rows,
            )
            conn.commit()
            inserted_count += len(rows)
            rows = []

    if rows:
        cur.executemany(
            "INSERT INTO submissions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
            rows,
        )
        conn.commit()
        inserted_count += len(rows)

    logger.info(f"Pass 1 Complete. Inserted {inserted_count} new submissions.")

    # Pass 2: Comments
    logger.info(f"Starting Pass 2: Comments from {comments_path}")
    # Stores min-heap of (score, comment_data) per link_id to keep top 3
    comment_heaps: Dict[str, List[Tuple]] = {}

    for line in stream_zst_lines(comments_path):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        link_id = data.get("link_id", "").replace("t3_", "")

        # Only process comments for submissions we actually ingested (and ignore bots/deleted)
        if link_id not in existing_ids or data.get("author") in BOT_AUTHORS:
            continue
        if data.get("body") in REMOVE_MARKERS:
            continue
        # Limit to top-level comments for cleaner "case" data
        if not str(data.get("parent_id", "")).startswith("t3_"):
            continue

        score = data.get("score", 0)
        heap = comment_heaps.setdefault(link_id, [])
        comment_data = (
            data["id"],
            link_id,
            data["author"],
            data["body"],
            score,
            data.get("is_submitter", False),
            data.get("parent_id"),
        )

        # maintain top 3 via min-heap
        if len(heap) < 3:
            heapq.heappush(heap, (score, comment_data))
        elif score > heap[0][0]:
            heapq.heapreplace(heap, (score, comment_data))

    logger.info("Truncating old comments and inserting top-filtered comments...")
    try:
        cur.execute("TRUNCATE TABLE comments")
        conn.commit()

        # Flatten heaps into list of rows
        comment_rows = [c for h in comment_heaps.values() for s, c in h]

        for i in range(0, len(comment_rows), batch_size):
            batch = comment_rows[i : i + batch_size]
            cur.executemany(
                "INSERT INTO comments VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                batch,
            )
            conn.commit()

        logger.info(f"Pass 2 Complete. Inserted {len(comment_rows)} comments.")
    except Exception as e:
        logger.error(f"Failed to insert comments: {e}")
        conn.rollback()

    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Reddit AITA data into PostgreSQL."
    )
    parser.add_argument(
        "--submissions",
        default=os.getenv("SUBMISSIONS_PATH"),
        help="Path to submissions .zst file",
    )
    parser.add_argument(
        "--comments",
        default=os.getenv("COMMENTS_PATH"),
        help="Path to comments .zst file",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_NAME", "peoples_court"),
        help="PostgreSQL database name",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum score for submissions",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Database batch insert size",
    )

    args = parser.parse_args()

    if not args.submissions or not args.comments:
        logger.error(
            "Missing required paths. Please provide --submissions and --comments arguments "
            "or set SUBMISSIONS_PATH and COMMENTS_PATH environment variables."
        )
        sys.exit(1)

    ingest(
        submissions_path=args.submissions,
        comments_path=args.comments,
        db_name=args.db,
        min_score=args.min_score,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
