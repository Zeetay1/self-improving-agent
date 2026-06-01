"""Feedback loop: runs after every agent generation.

Responsibilities:
1. Read the scores from the latest run.
2. Promote high-scoring outputs (weighted avg >= GOLDEN_THRESHOLD) into the
   golden dataset AND into ChromaDB memory so future runs can retrieve them.
3. Flag low-scoring outputs (weighted avg < FLAG_THRESHOLD) into the
   flagged_outputs table with a clear reason.

This is the closing arc of the self-improving loop: good outputs become future
few-shot fuel and regression baselines; bad ones get surfaced for review.
"""

from datetime import datetime, timezone
from typing import Any

from agent.memory import Memory
from db.store import Store
from evals.golden import GOLDEN_THRESHOLD, GoldenDataset

# Outputs scoring strictly below this are flagged for human review.
FLAG_THRESHOLD = 2.5
FLAG_REASON = "below quality threshold"


def run_feedback(
    store: Store,
    memory: Memory,
    brief: dict[str, Any],
    run_id: int,
    scored_outputs: list[dict[str, Any]],
    prompt_version: str,
) -> dict[str, Any]:
    """Process one run's outputs: promote the good, flag the bad.

    `scored_outputs` is a list of {variant_type, content, scores} dicts.
    Returns a summary describing what changed.
    """
    golden = GoldenDataset(store=store)
    now = datetime.now(timezone.utc).isoformat()

    promoted: list[str] = []
    flagged: list[str] = []

    for item in scored_outputs:
        variant_type = item["variant_type"]
        content = item["content"]
        scores = item["scores"]
        weighted = float(scores.get("weighted_average", 0.0))

        # 2. Promote high scorers to golden + memory.
        if weighted >= GOLDEN_THRESHOLD:
            added = golden.maybe_add(brief, variant_type, content, scores, prompt_version)
            memory.add(
                brief=brief,
                variant_type=variant_type,
                output=content,
                score=weighted,
                prompt_version=prompt_version,
                timestamp=now,
            )
            if added:
                promoted.append(variant_type)

        # 3. Flag low scorers for review.
        elif weighted < FLAG_THRESHOLD:
            store.add_flagged(
                brief=brief,
                variant_type=variant_type,
                output=content,
                weighted_average=weighted,
                reason=FLAG_REASON,
                run_id=run_id,
            )
            flagged.append(variant_type)

    return {
        "promoted_to_golden": promoted,
        "flagged_for_review": flagged,
        "golden_threshold": GOLDEN_THRESHOLD,
        "flag_threshold": FLAG_THRESHOLD,
    }
