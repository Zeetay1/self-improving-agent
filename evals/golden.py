"""Golden dataset manager.

The golden dataset is the system's regression baseline: outputs that scored
well enough (weighted average >= GOLDEN_THRESHOLD) are captured with their
brief, scores, and prompt version. The regression runner later re-scores each
entry against the active prompt and checks for drift.
"""

from typing import Any

from db.store import Store

# An output earns a golden slot only at or above this weighted average.
GOLDEN_THRESHOLD = 4.0


class GoldenDataset:
    def __init__(self, store: Store | None = None):
        self.store = store or Store()

    def qualifies(self, weighted_average: float) -> bool:
        return weighted_average >= GOLDEN_THRESHOLD

    def maybe_add(
        self,
        brief: dict[str, Any],
        variant_type: str,
        output: str,
        scores: dict[str, float],
        prompt_version: str,
    ) -> bool:
        """Add to the golden dataset if it qualifies and isn't already present.

        Returns True if a new golden entry was created.
        """
        if not self.qualifies(scores.get("weighted_average", 0.0)):
            return False
        if self.store.golden_exists(brief, variant_type, output):
            return False
        self.store.add_golden(brief, variant_type, output, scores, prompt_version)
        return True

    def all(self) -> list[dict[str, Any]]:
        return self.store.get_golden()

    def size(self) -> int:
        return len(self.store.get_golden())
