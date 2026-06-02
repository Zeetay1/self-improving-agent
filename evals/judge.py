"""LLM-as-judge scorer.

Same Groq model as the generator, but a strict, temperature-0 prompt. Returns
the four dimension scores plus a weighted average and a short rationale.
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
        # Nothing to score - treat as the floor.
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
