"""Groq client wrapper and JSON parsing helpers.

One chat() helper is shared by the generator and the judge so model config
lives in one place. No LangChain.
"""

import json
import os
import re
from typing import Any, Optional

from groq import Groq

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

_client: Optional[Groq] = None


def get_client() -> Groq:
    """Lazily construct a shared Groq client. Requires GROQ_API_KEY."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = Groq(api_key=api_key)
    return _client


def chat(
    prompt: str,
    temperature: float = 0.7,
    model: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Single-shot chat completion returning the raw assistant text."""
    client = get_client()
    resp = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort parse of a JSON object out of a model response.

    Models occasionally wrap JSON in prose or markdown fences despite
    instructions; we strip fences and fall back to the first {...} block.
    """
    text = text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to the first balanced-looking object.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse JSON from model output: {exc}\nRaw: {text}")
    raise ValueError(f"No JSON object found in model output.\nRaw: {text}")
