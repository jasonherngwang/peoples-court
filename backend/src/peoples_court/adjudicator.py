import logging
from typing import Optional

from .db import Database
from .models import Jury, Embedder
from .config import (
    DB_NAME,
    EMBED_MODEL_NAME,
    JURY_MODEL_ID,
    JURY_ADAPTER_PATH,
    EMBEDDING_DIM,
    K_PRECEDENTS,
)

logger = logging.getLogger(__name__)


async def retrieve_context(
    scenario: str,
    db_name: str = DB_NAME,
    embed_model_name: str = EMBED_MODEL_NAME,
    jury_model_id: str = JURY_MODEL_ID,
    jury_adapter_path: str = JURY_ADAPTER_PATH,
    embedding_dim: int = EMBEDDING_DIM,
    k_precedents: int = K_PRECEDENTS,
    embedder: Optional[Embedder] = None,
    jury: Optional[Jury] = None,
):
    """
    Retrieves precedents and jury consensus for a given scenario.
    """
    db = Database(dbname=db_name)
    try:
        if not embedder:
            embedder = Embedder(model_id=embed_model_name)
        if not jury:
            jury = Jury(model_id=jury_model_id, adapter_path=jury_adapter_path)

        # 1. Vector Search & Retrieval
        vector = embedder.encode(scenario, dim=embedding_dim)
        precedents, v_res, k_res, h_rank = db.retrieve_precedents(
            scenario_vector=vector,
            keyword_query=scenario,
            k_precedents=k_precedents,
        )

        # 2. Jury Polling
        consensus = jury.predict(scenario)

        return {"precedents": precedents, "consensus": consensus, "scenario": scenario}
    finally:
        db.close()
