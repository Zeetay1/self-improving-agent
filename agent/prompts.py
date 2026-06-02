"""All prompts live here, versioned by string key.

ACTIVE_PROMPT_VERSION selects the live generation prompt; swapping it is guarded
by the regression check (evals/runner.py). Don't hardcode prompt text elsewhere.
"""

# Run the regression suite before promoting a new version.
ACTIVE_PROMPT_VERSION = "GENERATION_PROMPT_V1"


GENERATION_PROMPT_V1 = """You are a senior direct-to-consumer (DTC) ad copywriter.

You will be given a brand brief. Write three distinct pieces of ad copy:
1. A HEADLINE hook - one short line that immediately grabs attention.
2. A BODY copy - 2-3 sentences that build desire and reflect the brand tone.
3. A CTA - a single short call to action that drives the stated goal.

Rules:
- Match the brief's tone and speak directly to the described audience.
- Be specific and concrete. Avoid generic filler and clichés.
- Keep the headline punchy and the CTA action-oriented.
- Return ONLY valid JSON, no preamble, no markdown fences.

Return exactly this JSON shape:
{{
  "headline": "<headline hook>",
  "body": "<body copy>",
  "cta": "<call to action>"
}}

{few_shot_block}

Brand brief:
{brief}
"""

# A second version kept as a worked example of how to add and promote prompts.
# It nudges the model toward tighter, benefit-led copy. To use it, set
# ACTIVE_PROMPT_VERSION = "GENERATION_PROMPT_V2" and run the regression suite.
GENERATION_PROMPT_V2 = """You are an award-winning DTC performance copywriter who writes
copy that converts cold traffic.

You will be given a brand brief. Produce three pieces of ad copy:
1. HEADLINE - a scroll-stopping hook of at most 8 words.
2. BODY - 2-3 sentences leading with the strongest benefit, in the brand's voice.
3. CTA - an imperative call to action tied directly to the stated goal.

Rules:
- Lead with benefit, not feature. Speak to the exact audience in the brief.
- No clichés, no hype words ("revolutionary", "game-changer"), no emojis.
- Return ONLY valid JSON, no preamble, no markdown fences.

Return exactly this JSON shape:
{{
  "headline": "<headline hook>",
  "body": "<body copy>",
  "cta": "<call to action>"
}}

{few_shot_block}

Brand brief:
{brief}
"""


# Registry so other modules can resolve a version string to its template.
PROMPT_REGISTRY = {
    "GENERATION_PROMPT_V1": GENERATION_PROMPT_V1,
    "GENERATION_PROMPT_V2": GENERATION_PROMPT_V2,
}


FEW_SHOT_HEADER = "Past high-performing examples (learn from their style, do not copy verbatim):"


def build_few_shot_block(examples: list[dict]) -> str:
    """Render retrieved high-scoring examples into a prompt section.

    Each example is a dict with keys: brief (dict), variant_type, output, score.
    Returns an empty string when there are no examples so the prompt stays clean.
    """
    if not examples:
        return ""

    lines = [FEW_SHOT_HEADER, ""]
    for i, ex in enumerate(examples, 1):
        brief = ex.get("brief", {})
        product = brief.get("product", "") if isinstance(brief, dict) else ""
        lines.append(
            f"Example {i} ({ex.get('variant_type', 'output')}, "
            f"score {ex.get('score', 0):.2f}/5) for product '{product}':"
        )
        lines.append(f'  "{ex.get("output", "")}"')
        lines.append("")
    return "\n".join(lines).strip()


def get_generation_prompt(version: str) -> str:
    """Return the raw template for a version string, defaulting to the active one."""
    return PROMPT_REGISTRY.get(version, PROMPT_REGISTRY[ACTIVE_PROMPT_VERSION])


def render_generation_prompt(brief: dict, few_shot_block: str, version: str | None = None) -> str:
    """Fill a generation prompt template with the brief and few-shot examples."""
    import json

    version = version or ACTIVE_PROMPT_VERSION
    template = get_generation_prompt(version)
    return template.format(
        brief=json.dumps(brief, indent=2),
        few_shot_block=few_shot_block,
    )


# Judge prompt, versioned alongside the generation prompts.
JUDGE_PROMPT_VERSION = "JUDGE_PROMPT_V1"

JUDGE_PROMPT_V1 = """You are a strict, fair advertising copy evaluator.

Score the candidate ad copy on FOUR dimensions, each an integer from 1 to 5:
- hook_strength: does it immediately grab attention?
- brand_alignment: does it reflect the brief's tone and speak to the audience?
- clarity: is the message immediately understandable?
- conversion_intent: does it drive toward the stated goal?

Be discriminating. Reserve 5 for genuinely excellent copy and 1 for copy that
fails the dimension entirely. Do NOT return a single composite score.

Return ONLY valid JSON, no preamble, no markdown fences, exactly:
{{
  "hook_strength": <1-5>,
  "brand_alignment": <1-5>,
  "clarity": <1-5>,
  "conversion_intent": <1-5>,
  "rationale": "<one short sentence>"
}}

Brand brief:
{brief}

Candidate copy ({variant_type}):
"{output}"
"""

JUDGE_REGISTRY = {
    "JUDGE_PROMPT_V1": JUDGE_PROMPT_V1,
}


def render_judge_prompt(brief: dict, variant_type: str, output: str, version: str | None = None) -> str:
    import json

    version = version or JUDGE_PROMPT_VERSION
    template = JUDGE_REGISTRY.get(version, JUDGE_PROMPT_V1)
    return template.format(
        brief=json.dumps(brief, indent=2),
        variant_type=variant_type,
        output=output,
    )
