"""FastAPI app for the hosted public demo.

Endpoints:
- GET  /health  -> liveness probe
- GET  /stats   -> live counts (runs, golden, flagged) for the frontend strip
- POST /run     -> full agent loop (rate limited), returns outputs + scores

Run locally:  uvicorn api.main:app --reload
"""

import os
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # pick up GROQ_API_KEY / CORS_ORIGINS from .env if present

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

from agent.core import Agent  # noqa: E402  (after load_dotenv on purpose)
from seed.loader import load_seed_if_empty  # noqa: E402

# one shared agent (and Store/Memory) per process
_agent: Agent | None = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


def _cors_origins() -> list[str]:
    """Origins from CORS_ORIGINS (comma-separated), always plus localhost:3000.

    If CORS_ORIGINS is unset, default to allow-all ("*").
    """
    raw = os.getenv("CORS_ORIGINS")
    if not raw:
        return ["*"]
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")
    return origins


# seed golden + memory on a fresh deployment so the first visitor isn't cold
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        agent = get_agent()
        seeded = load_seed_if_empty(agent.store, agent.memory)
        if seeded:
            print(f"[startup] Seeded {seeded} golden/memory example(s).")
    except Exception as exc:  # noqa: BLE001 - never block startup on seeding.
        print(f"[startup] Seed skipped: {exc}")
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Self-Improving Ad Copy Agent", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BrandBrief(BaseModel):
    brand: str = Field(..., examples=["FitFuel"])
    product: str = Field(..., examples=["High-protein meal replacement shake"])
    audience: str = Field(..., examples=["Busy professionals aged 25-40"])
    tone: str = Field(..., examples=["Energetic and no-nonsense"])
    goal: str = Field(..., examples=["Drive trial purchases"])


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "endpoint": "POST /run with a brand brief"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict[str, int]:
    """Live counts for the frontend stats strip."""
    store = get_agent().store
    return {
        "runs": store.count_runs(),
        "golden": store.count_golden(),
        "flagged": store.count_flagged(),
    }


@app.post("/run")
@limiter.limit("10/minute")
def run(request: Request, brief: BrandBrief) -> dict[str, Any]:
    """Trigger the full agent loop for a brand brief (rate limited per IP)."""
    try:
        agent = get_agent()
        return agent.run(brief.model_dump())
    except RuntimeError as exc:  # e.g. missing GROQ_API_KEY
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface generation/judge failures
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}") from exc
