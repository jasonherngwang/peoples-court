import json
import logging
import os
from typing import Dict, Any, Optional

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


def adjudicate(
    scenario: str,
    db_name: str = DB_NAME,
    embed_model_name: str = EMBED_MODEL_NAME,
    jury_model_id: str = JURY_MODEL_ID,
    jury_adapter_path: str = JURY_ADAPTER_PATH,
    judge_model_name: str = JUDGE_MODEL_NAME,
    embedding_dim: int = EMBEDDING_DIM,
    k_precedents: int = K_PRECEDENTS,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Core judicial logic decoupled from CLI display.
    Returns a dictionary with adjudication results.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY must be provided or set in environment.")

    db = Database(dbname=db_name)
    try:
        # 1. Initialize models
        embedder = Embedder(model_id=embed_model_name)
        jury = Jury(model_id=jury_model_id, adapter_path=jury_adapter_path)

        # 2. Vector Search & Retrieval
        vector = embedder.encode(scenario, dim=embedding_dim)
        precedents, v_res, k_res, h_rank = db.retrieve_precedents(
            scenario_vector=vector,
            keyword_query=scenario,
            k_precedents=k_precedents,
        )

        # 3. Jury Polling
        consensus = jury.predict(scenario)

        if not precedents:
            return {
                "error": "No relevant precedents found",
                "consensus": consensus,
                "diagnostics": {"vector": v_res, "keyword": k_res, "hybrid": h_rank},
            }

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

        # 5. Judge Deliberation
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

        raw_result = judge.adjudicate(context, response_schema)
        result = json.loads(raw_result)

        # 6. Build enriched result
        # Map raw DB records to the citations chosen by the Judge
        db_map = {p["id"]: p for p in precedents}
        enriched_precedents = []
        for cite in result["precedents"]:
            cid = cite["case_id"]
            if cid in db_map:
                # Merge judge's comparison with raw DB data
                data = db_map[cid].copy()
                data["comparison"] = cite["comparison"]
                enriched_precedents.append(data)
            else:
                # Fallback if judge hallucinates a case ID (unlikely with schema)
                enriched_precedents.append(cite)

        result["precedents"] = enriched_precedents
        result["consensus"] = consensus
        result["diagnostics"] = {"vector": v_res, "keyword": k_res, "hybrid": h_rank}

        return result

    finally:
        db.close()
