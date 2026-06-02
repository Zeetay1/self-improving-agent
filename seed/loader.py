"""Startup seed loader.

Loads a few pre-scored examples into golden + memory on first boot so a fresh
deployment isn't cold (zeroed stats, no retrieval). No-op if golden is non-empty.
"""

import json
import os
from datetime import datetime, timezone

from agent.memory import Memory
from db.store import Store

SEED_PATH = os.path.join(os.path.dirname(__file__), "golden_seed.json")


def load_seed_if_empty(store: Store, memory: Memory) -> int:
    """Load seed examples into golden + memory iff golden is currently empty.

    Returns the number of entries seeded (0 if it was already populated).
    """
    if store.count_golden() > 0:
        return 0

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)

    now = datetime.now(timezone.utc).isoformat()
    seeded = 0
    for entry in entries:
        brief = entry["brief"]
        variant_type = entry["variant_type"]
        output = entry["output"]
        scores = entry["scores"]
        prompt_version = entry.get("prompt_version", "GENERATION_PROMPT_V1")

        store.add_golden(brief, variant_type, output, scores, prompt_version)
        memory.add(
            brief=brief,
            variant_type=variant_type,
            output=output,
            score=float(scores["weighted_average"]),
            prompt_version=prompt_version,
            timestamp=now,
        )
        seeded += 1
    return seeded
