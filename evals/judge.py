"""LLM-as-judge scorer.

Uses the same Groq model as the generator (llama-3.3-70b-versatile) but with a
strict, low-temperature judging prompt. Returns the four dimension scores plus
a derived weighted average and a one-line rationale. It never collapses the
output into a single composite the way a naive scorer would.
"""

from typing import Any

from agent import prompts, tools
from evals import rubric

# Judging is deterministic-ish: low temperature for stable, repeatable scores.
JUDGE_TEMPERATURE = 0.0


def judge_output(brief: dict[str, Any], variant_type: str, output: str) -> dict[str, Any]:
    """Score a single ad-copy variant on the four rubric dimensions.

    Returns a dict containing each dimension (1-5), the weighted_average, and a
    rationale string. Robust to a malformed judge response: dimensions clamp to
    the valid range and default low.
    """
    if not output.strip():
        # Nothing to score — treat as the floor.
        scores = rubric.normalize_scores({})
        scores["rationale"] = "Empty output."
        return scores

    prompt = prompts.render_judge_prompt(brief, variant_type, output)
    raw = tools.chat(prompt, temperature=JUDGE_TEMPERATURE, max_tokens=512)

    try:
        parsed = tools.extract_json(raw)
    except ValueError:
        parsed = {}

    scores = rubric.normalize_scores(parsed)
    scores["rationale"] = str(parsed.get("rationale", "")).strip()
    return scores
