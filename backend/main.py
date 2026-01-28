from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import logging
import sys
import json

# Ensure the src directory is in the path so we can import the peoples_court package
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from peoples_court.adjudicator import adjudicate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="People's Court API",
    description="Adjudicating social conflicts using AITA case law.",
    version="0.1.0",
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
    diagnostics: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health_check():
    """Verify that the API and environment are healthy."""
    return {"status": "healthy"}


@app.post("/adjudicate")
async def post_adjudicate(request: AdjudicateRequest):
    """
    Submits a scenario for adjudication.
    Returns the final result only (blocks until complete).
    """
    try:
        logger.info(
            f"Received non-streaming adjudication request: {request.scenario[:50]}..."
        )
        final_result = None
        # Consume the generator to get the final result
        async for event in adjudicate(
            scenario=request.scenario, k_precedents=request.k_precedents
        ):
            if event["event"] == "final_result":
                final_result = event["data"]
            elif event["event"] == "error":
                raise HTTPException(status_code=500, detail=event["data"])

        if not final_result:
            raise HTTPException(
                status_code=404,
                detail="Adjudication complete but no final result generated",
            )

        return final_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Adjudication failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/adjudicate/stream")
async def post_adjudicate_stream(request: AdjudicateRequest):
    """
    Submits a scenario and returns a Server-Sent Events (SSE) stream.
    Includes status updates and Judge tokens.
    """
    logger.info(f"Received streaming adjudication request: {request.scenario[:50]}...")

    async def event_generator():
        try:
            async for event in adjudicate(
                scenario=request.scenario, k_precedents=request.k_precedents
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
