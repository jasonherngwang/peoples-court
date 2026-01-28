import json
import logging
import os
from typing import Optional

from .db import Database
from .models import Judge, Jury, Embedder
from .config import (
    DB_NAME,
    EMBED_MODEL_NAME,
    JURY_MODEL_ID,
    JURY_ADAPTER_PATH,
    JUDGE_MODEL_NAME,
    EMBEDDING_DIM,
    K_PRECEDENTS,
)

logger = logging.getLogger(__name__)


async def adjudicate(
    scenario: str,
    db_name: str = DB_NAME,
    embed_model_name: str = EMBED_MODEL_NAME,
    jury_model_id: str = JURY_MODEL_ID,
    jury_adapter_path: str = JURY_ADAPTER_PATH,
    judge_model_name: str = JUDGE_MODEL_NAME,
    embedding_dim: int = EMBEDDING_DIM,
    k_precedents: int = K_PRECEDENTS,
    api_key: Optional[str] = None,
):
    """
    Async generator that yields progress events and final adjudication results.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        yield {"event": "error", "data": "GEMINI_API_KEY not provided"}
        return

    db = Database(dbname=db_name)
    try:
        # 1. Initialize models
        yield {"event": "status", "data": "Initializing models..."}
        embedder = Embedder(model_id=embed_model_name)
        jury = Jury(model_id=jury_model_id, adapter_path=jury_adapter_path)

        # 2. Vector Search & Retrieval
        yield {"event": "status", "data": "The Clerk is searching for precedents..."}
        vector = embedder.encode(scenario, dim=embedding_dim)
        precedents, v_res, k_res, h_rank = db.retrieve_precedents(
            scenario_vector=vector,
            keyword_query=scenario,
            k_precedents=k_precedents,
        )

        # 3. Jury Polling
        yield {"event": "status", "data": "The Jury is polling..."}
        consensus = jury.predict(scenario)

        if not precedents:
            yield {
                "event": "error",
                "data": "No relevant precedents found",
                "consensus": consensus,
            }
            return

        # 4. Build Context for Judge
        context = "### CURRENT EVIDENCE PROVIDED BY THE PLAINTIFF:\n\n"
        context += scenario + "\n\n"
        context += "### PRE-DELIBERATION JURY POLLING:\n"
        for label, prob in consensus.items():
            context += f"- {label}: {prob * 100:.2f}%\n"
        context += "\n"
        context += "### RELEVANT CASE LAW (PRECEDENTS):\n\n"
        for i, p in enumerate(precedents, 1):
            context += f"CASE {i}: ID `{p['id']}` - Title: {p['title']}\n"
            context += f"Official Reddit Verdict: {p['verdict']}\n"
            context += f"Facts: {p['text'][:1000]}...\n"
            context += "Top Judgments from the Jury:\n"
            for c in p["comments"]:
                context += (
                    f"- {c['author']} (Score {c['score']}): {c['body'][:200]}...\n"
                )
            context += "\n---\n"

        # 5. Judge Deliberation (Streaming)
        yield {"event": "status", "data": "The Judge is deliberating..."}
        judge = Judge(api_key=api_key, model_id=judge_model_name)

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "verdict": {"type": "STRING", "enum": ["YTA", "NTA", "ESH", "NAH"]},
                "opening_statement": {"type": "STRING"},
                "facts": {"type": "STRING"},
                "precedents": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "case_id": {"type": "STRING"},
                            "comparison": {"type": "STRING"},
                        },
                        "required": ["case_id", "comparison"],
                    },
                },
                "deliberation": {"type": "STRING"},
            },
            "required": [
                "verdict",
                "opening_statement",
                "facts",
                "precedents",
                "deliberation",
            ],
        }

        # We yield a specific event for the Judge's result
        # Note: Since the core logic expects a single JSON block to enrich,
        # we still collect it, but we can stream tokens to the user meanwhile.
        full_judge_response = ""
        async for token in judge.adjudicate_stream(context, response_schema):
            full_judge_response += token
            yield {"event": "token", "data": token}

        # 6. Final Enrichment (Sent as a final summary event)
        try:
            result = json.loads(full_judge_response)
            db_map = {p["id"]: p for p in precedents}
            enriched_precedents = []
            for cite in result["precedents"]:
                cid = cite["case_id"]
                if cid in db_map:
                    data = db_map[cid].copy()
                    data["comparison"] = cite["comparison"]
                    enriched_precedents.append(data)
                else:
                    enriched_precedents.append(cite)

            result["precedents"] = enriched_precedents
            result["consensus"] = consensus
            result["diagnostics"] = {
                "vector": v_res,
                "keyword": k_res,
                "hybrid": h_rank,
            }

            yield {"event": "final_result", "data": result}
        except Exception as e:
            yield {
                "event": "error",
                "data": f"Failed to parse Judge response: {str(e)}",
            }

    finally:
        db.close()
