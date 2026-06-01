"""FastAPI app exposing a single endpoint to trigger the full agent loop.

POST /run with a brand brief -> retrieve -> generate -> evaluate -> feedback,
returning the generated outputs and their scores.

Run with:  uvicorn api.main:app --reload
"""

from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()  # pick up GROQ_API_KEY from .env if present

from agent.core import Agent  # noqa: E402  (after load_dotenv on purpose)

app = FastAPI(title="Self-Improving Ad Copy Agent", version="1.0.0")

# A single shared agent (and therefore shared Store/Memory) for the process.
_agent: Agent | None = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


class BrandBrief(BaseModel):
    brand: str = Field(..., examples=["FitFuel"])
    product: str = Field(..., examples=["High-protein meal replacement shake"])
    audience: str = Field(..., examples=["Busy professionals aged 25-40"])
    tone: str = Field(..., examples=["Energetic and no-nonsense"])
    goal: str = Field(..., examples=["Drive trial purchases"])


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "endpoint": "POST /run with a brand brief"}


@app.post("/run")
def run(brief: BrandBrief) -> dict[str, Any]:
    """Trigger the full agent loop for a brand brief."""
    try:
        agent = get_agent()
        return agent.run(brief.model_dump())
    except RuntimeError as exc:  # e.g. missing GROQ_API_KEY
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface generation/judge failures
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}") from exc
