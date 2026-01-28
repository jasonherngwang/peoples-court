import argparse
import logging
import os
import sys
import re
from typing import List, Tuple
from collections import Counter
import psycopg
from psycopg.rows import dict_row

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

JUDGMENT_RE = re.compile(
    r"\b(YTA|NTA|ESH|NAH|INFO|YWBTA|YWNBTA|NOT THE A-HOLE|YOU'RE THE ASSHOLE)\b",
    re.IGNORECASE,
)
CANONICAL = {
    "YTA": "YTA",
    "NTA": "NTA",
    "ESH": "ESH",
    "NAH": "NAH",
    "INFO": "INFO",
    "YWBTA": "YTA",
    "YWNBTA": "NTA",
    "NOT THE A-HOLE": "NTA",
    "YOU'RE THE ASSHOLE": "YTA",
}
JUNK_FLAIRS = {
    "UPDATE",
    "Update",
    "Update ",
    "META",
    "META: Help!",
    "Open Forum",
    "Announcement",
    "Announcement ",
    "TL;DR",
    "Best of 2022",
    "Best of 2021",
    "Community Discussion",
    "COOL META",
    "NEWS",
    "POO Mode Activated 💩",
    "too close to call",
    "Fake",
    "Fake Story",
}
FLAIR_MAPPING = {
    "Not the A-hole": "NTA",
    "not the a-hole": "NTA",
    "Not the A-hole POO Mode": "NTA",
    "not the a-hole POO Mode": "NTA",
    "Not the A-hole (oof)": "NTA",
    "not the asshole": "NTA",
    "not the arsehole": "NTA",
    "not the a-hole-": "NTA",
    "Def. not a-hole": "NTA",
    "not the a-hole, run": "NTA",
    "not a-hole, run": "NTA",
    "nut the a-hole": "NTA",
    "Asshole": "YTA",
    "asshole": "YTA",
    "Asshole POO Mode": "YTA",
    "asshole POO Mode": "YTA",
    "justifiable asshole": "YTA",
    "justified asshole": "YTA",
    "Righteous Asshole": "YTA",
    "UnanimASSly the Asshole": "YTA",
    "asshole-ish": "YTA",
    "asshole-y": "YTA",
    "asshole baby": "YTA",
    "a little butthole": "YTA",
    "cheap asshole": "YTA",
    "YTA reddit": "YTA",
    "Everyone Sucks": "ESH",
    "everyone sucks": "ESH",
    "Everyone Sucks POO Mode": "ESH",
    "No A-holes here": "NAH",
    "no a--holes here": "NAH",
    "No A-holes here POO Mode": "NAH",
}
JUNK_TITLE_KEYWORDS = [
    "UPDATE:",
    "UPDATE -",
    "META:",
    "BEST OF",
    "AWARDS",
    "MONTHLY FORUM",
]


def extract_judgments(text: str) -> List[str]:
    """Extracts canonical AITA judgments from text, handling common variations."""
    clean_text = text.replace("Not the A-hole", "NTA").replace(
        "You're the A-hole", "YTA"
    )
    matches = JUDGMENT_RE.findall(clean_text)
    return [
        CANONICAL[m.upper().replace("İ", "I")]
        for m in matches
        if m.upper().replace("İ", "I") in CANONICAL
    ]


def label(db_name: str, batch_size: int):
    """
    Analyzes submissions and determines a verdict based on flair or top comments.
    Uses a weighted voting system for comments to ensure high-signal consensus.
    """
    logger.info("Connecting to database...")
    try:
        conn = psycopg.connect(dbname=db_name, row_factory=dict_row)
        cur = conn.cursor()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return

    try:
        cur.execute("SELECT id, title, link_flair_text FROM submissions")
        submissions = cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch submissions: {e}")
        cur.close()
        conn.close()
        return

    logger.info(f"Total submissions to analyze: {len(submissions)}")

    updated_count = 0
    updates: List[Tuple] = []

    for i, sub in enumerate(submissions):
        sub_id = sub["id"]
        title = (sub["title"] or "").upper()
        flair = sub["link_flair_text"]

        # Filter out junk posts
        if any(kw in title for kw in JUNK_TITLE_KEYWORDS) or flair in JUNK_FLAIRS:
            updates.append(("JUNK", sub_id))
        else:
            verdict = FLAIR_MAPPING.get(flair)
            if not verdict:
                # Fallback to top comment analysis
                try:
                    cur.execute(
                        "SELECT body, score FROM comments WHERE submission_id = %s AND is_submitter = FALSE ORDER BY score DESC LIMIT 3",
                        (sub_id,),
                    )
                    comments = cur.fetchall()
                except Exception as e:
                    logger.error(f"Failed to fetch comments for {sub_id}: {e}")
                    comments = []

                if comments:
                    votes = Counter()
                    for c in comments:
                        comment_judgments = extract_judgments(c["body"])
                        if comment_judgments:
                            # Weight by score, capped to prevent outliers from dominating
                            votes[comment_judgments[0]] += max(1, min(c["score"], 500))

                    if votes:
                        top_vote = votes.most_common(1)[0][0]
                        if top_vote in ["YTA", "NTA", "ESH", "NAH", "INFO"]:
                            verdict = top_vote

            updates.append((verdict or "UNKNOWN", sub_id))

        if len(updates) >= batch_size:
            try:
                cur.executemany(
                    "UPDATE submissions SET verdict = %s WHERE id = %s", updates
                )
                conn.commit()
                updated_count += len(updates)
                if updated_count % 10000 == 0 or updated_count == len(submissions):
                    logger.info(
                        f"  Processed {updated_count}/{len(submissions)} submissions..."
                    )
            except Exception as e:
                logger.error(f"Failed to update batch: {e}")
                conn.rollback()
            updates = []

    if updates:
        try:
            cur.executemany(
                "UPDATE submissions SET verdict = %s WHERE id = %s", updates
            )
            conn.commit()
            updated_count += len(updates)
        except Exception as e:
            logger.error(f"Failed to update final batch: {e}")
            conn.rollback()

    logger.info(f"Labeling complete. Processed {updated_count} submissions.")
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Label Reddit AITA submissions with verdicts."
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_NAME", "peoples_court"),
        help="PostgreSQL database name",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Database update batch size",
    )

    args = parser.parse_args()

    label(
        db_name=args.db,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
