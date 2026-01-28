import psycopg
from . import config
from typing import List, Tuple, Dict, Any, Optional


class Database:
    """Handle all interactions with the PostgreSQL database, including hybrid search."""

    def __init__(self, dbname: str = "peoples_court"):
        """Initialize database connection parameters."""
        self.dbname = dbname
        self.conn: Optional[psycopg.Connection] = None

    def connect(self) -> psycopg.Connection:
        """Establish a connection to the database if one doesn't exist."""
        if not self.conn:
            self.conn = psycopg.connect(
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                host=config.DB_HOST,
                port=config.DB_PORT,
            )
        return self.conn

    def close(self) -> None:
        """Safely close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_cursor(self) -> psycopg.Cursor:
        """Return a cursor for the current connection."""
        return self.connect().cursor()

    @staticmethod
    def rrf_combine(
        vector_results: List[Tuple[str, float]],
        keyword_results: List[Tuple[str, float]],
        k: int = 60,
        top_rank_bonus: float = 0.01,
    ) -> List[Tuple[str, float]]:
        """
        Combine search results using Reciprocal Rank Fusion (RRF) with a top-rank bonus.

        Args:
            vector_results: List of (id, similarity) from vector search.
            keyword_results: List of (id, score) from keyword search.
            k: RRF penalty constant (default 60).
            top_rank_bonus: Bonus points for documents ranking #1 in either list.

        Returns:
            Sorted list of (id, rrf_score).
        """
        scores: Dict[str, float] = {}
        for rank, (sub_id, _) in enumerate(vector_results, start=1):
            boost = top_rank_bonus if rank == 1 else 0.0
            scores[sub_id] = scores.get(sub_id, 0.0) + (1.0 / (k + rank)) + boost
        for rank, (sub_id, _) in enumerate(keyword_results, start=1):
            boost = top_rank_bonus if rank == 1 else 0.0
            scores[sub_id] = scores.get(sub_id, 0.0) + (1.0 / (k + rank)) + boost
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def retrieve_precedents(
        self, scenario_vector: List[float], keyword_query: str, k_precedents: int = 3
    ) -> Tuple[List[Dict[str, Any]], List[Tuple], List[Tuple], List[Tuple]]:
        """
        Perform hybrid search (Vector + BM25) to find relevant cases.

        Args:
            scenario_vector: The embedding vector for the query.
            keyword_query: The raw query string for BM25 search.
            k_precedents: Number of top cases to return.

        Returns:
            A tuple containing:
            - precedents (List of Case dicts)
            - vector_results (Raw vector search results)
            - keyword_results (Raw keyword search results)
            - hybrid_rankings (Combined rankings)
        """
        with self.get_cursor() as cur:
            # 1. Vector Search
            cur.execute(
                """
                SELECT e.submission_id, 1 - (e.vector <=> %s::vector) as similarity
                FROM embeddings e
                JOIN submissions s ON e.submission_id = s.id
                WHERE s.verdict IN ('YTA', 'NTA', 'ESH', 'NAH')
                ORDER BY similarity DESC
                LIMIT 20
            """,
                (scenario_vector,),
            )
            vector_results = cur.fetchall()

            # 2. Keyword Search (BM25)
            # Sanitization logic moved here or kept simple
            clean_kw = keyword_query.split("\n")[0].strip()
            for char in [":", "(", ")", "[", "]", '"', "?", "*", "-", "/", "\\"]:
                clean_kw = clean_kw.replace(char, " ")

            cur.execute(
                """
                SELECT id, paradedb.score(submissions) as bm25_score
                FROM submissions
                WHERE submissions @@@ %s
                AND verdict IN ('YTA', 'NTA', 'ESH', 'NAH')
                ORDER BY bm25_score DESC
                LIMIT 20
            """,
                (f"title:({clean_kw})^2 OR selftext:({clean_kw})",),
            )
            keyword_results = cur.fetchall()

            # Hybrid Rank
            hybrid_rankings = self.rrf_combine(vector_results, keyword_results)
            top_ids = [item[0] for item in hybrid_rankings[:k_precedents]]

            if not top_ids:
                return [], vector_results, keyword_results, hybrid_rankings

            # Fetch Details
            cur.execute(
                "SELECT id, title, selftext, link_flair_text, score FROM submissions WHERE id = ANY(%s)",
                (top_ids,),
            )
            subs = {row[0]: row for row in cur.fetchall()}

            # Fetch Comments
            cur.execute(
                "SELECT submission_id, author, body, score FROM comments WHERE submission_id = ANY(%s) ORDER BY score DESC",
                (top_ids,),
            )
            comments: Dict[str, List[Dict[str, Any]]] = {}
            for sub_id, author, body, score in cur.fetchall():
                if sub_id not in comments:
                    comments[sub_id] = []
                if len(comments[sub_id]) < 3:
                    comments[sub_id].append(
                        {"author": author, "body": body, "score": score}
                    )

            precedents = []
            for sub_id in top_ids:
                if sub_id in subs:
                    s = subs[sub_id]
                    precedents.append(
                        {
                            "id": sub_id,
                            "title": s[1],
                            "text": s[2],
                            "verdict": s[3],
                            "score": s[4],
                            "relevance_score": next(
                                score for sid, score in hybrid_rankings if sid == sub_id
                            ),
                            "comments": comments.get(sub_id, []),
                        }
                    )
            return precedents, vector_results, keyword_results, hybrid_rankings
