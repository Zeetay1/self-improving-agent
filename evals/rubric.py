"""Scoring rubric: four 1-5 dimensions and the weights for the internal
weighted average. Dimension scores are stored separately; the weighted average
is only used for ranking/thresholds.
"""

# The four scored dimensions, each on a 1-5 integer scale.
DIMENSIONS = ("hook_strength", "brand_alignment", "clarity", "conversion_intent")

# Weights used ONLY to compute an internal weighted average. They sum to 1.0.
WEIGHTS = {
    "hook_strength": 0.30,
    "brand_alignment": 0.25,
    "clarity": 0.25,
    "conversion_intent": 0.20,
}

# Human-readable descriptions, surfaced in the judge prompt and docs.
DIMENSION_DESCRIPTIONS = {
    "hook_strength": "Does the headline immediately grab attention?",
    "brand_alignment": "Does the copy reflect the brief tone and audience?",
    "clarity": "Is the message immediately understandable?",
    "conversion_intent": "Does it drive toward the stated goal?",
}

SCALE_MIN = 1
SCALE_MAX = 5


def weighted_average(scores: dict[str, float]) -> float:
    """Compute the internal weighted average from dimension scores.

    Missing dimensions are treated as 0 so a malformed judge response surfaces
    as a low score rather than silently passing.
    """
    total = 0.0
    for dim, weight in WEIGHTS.items():
        total += float(scores.get(dim, 0)) * weight
    return round(total, 4)


def clamp(value: float) -> int:
    """Clamp a raw score into the valid 1-5 integer range."""
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        v = SCALE_MIN
    return max(SCALE_MIN, min(SCALE_MAX, v))


def normalize_scores(raw: dict) -> dict[str, float]:
    """Validate/clamp the four dimensions and attach the weighted average."""
    scores: dict[str, float] = {}
    for dim in DIMENSIONS:
        scores[dim] = clamp(raw.get(dim))
    scores["weighted_average"] = weighted_average(scores)
    return scores
