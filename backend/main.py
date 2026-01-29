from fastapi import FastAPI, HTTPException, Header, Depends
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import logging
import sys
import json

# Ensure the src directory is in the path so we can import the peoples_court package
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from peoples_court.adjudicator import adjudicate, retrieve_context
from peoples_court.models import Embedder, Jury
from peoples_court.config import EMBED_MODEL_NAME, JURY_MODEL_ID, JURY_ADAPTER_PATH

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")


async def verify_api_key(x_api_key: str = Header(None)):
    if not INTERNAL_API_KEY:
        logger.error("INTERNAL_API_KEY is not set in the environment")
        raise HTTPException(status_code=500, detail="Server security misconfiguration")

    if x_api_key != INTERNAL_API_KEY:
        logger.warning(f"Invalid API Key attempt: {x_api_key}")
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key


# Configure logging - silence verbose third-party libraries
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress verbose logs from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models on startup
    logger.info("Loading models...")
    app.state.embedder = Embedder(model_id=EMBED_MODEL_NAME)
    app.state.jury = Jury(model_id=JURY_MODEL_ID, adapter_path=JURY_ADAPTER_PATH)
    logger.info("Models loaded successfully.")
    yield
    # Clean up resources on shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="People's Court API",
    description="Adjudicating social conflicts using AITA case law.",
    version="0.1.0",
    lifespan=lifespan,
)


class AdjudicateRequest(BaseModel):
    scenario: str
    k_precedents: Optional[int] = 3


class AdjudicateResponse(BaseModel):
    verdict: str
    opening_statement: str
    facts: str
    precedents: List[Dict[str, Any]]
    deliberation: str
    consensus: Dict[str, float]


@app.get("/health")
async def health_check():
    """Verify that the API and environment are healthy."""
    return {"status": "healthy"}


@app.post("/context")
async def post_retrieve_context(request: AdjudicateRequest, _=Depends(verify_api_key)):
    """
    Retrieves the context (precedents and jury consensus) for a scenario.
    Does NOT call the Judge.
    """
    try:
        logger.info(f"Received context retrieval request: {request.scenario[:50]}...")
        context_data = await retrieve_context(
            scenario=request.scenario,
            k_precedents=request.k_precedents,
            embedder=app.state.embedder,
            jury=app.state.jury,
        )
        return context_data
    except Exception as e:
        logger.error(f"Context retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/adjudicate/stream")
async def post_adjudicate_stream(request: AdjudicateRequest, _=Depends(verify_api_key)):
    """
    Submits a scenario and returns a Server-Sent Events (SSE) stream.
    Includes status updates and Judge tokens.
    """
    logger.info(f"Received streaming adjudication request: {request.scenario[:50]}...")

    async def event_generator():
        try:
            async for event in adjudicate(
                scenario=request.scenario,
                k_precedents=request.k_precedents,
                embedder=app.state.embedder,
                jury=app.state.jury,
            ):
                # Standard SSE format: "data: <json>\n\n"
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Streaming failed: {str(e)}")
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
