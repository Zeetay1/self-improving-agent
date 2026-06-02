"""The main agent loop: retrieve -> generate -> evaluate -> store -> feedback.

This ties memory, generation, the eval judge, persistence, and the feedback
loop together. It is intentionally synchronous and dependency-injected so it
can be driven from the API, the CLI, or tests with the same code path.
"""

from typing import Any, Optional

from agent import prompts, tools
from agent.memory import Memory
from db.store import Store

# The three variants the agent always produces, in order.
VARIANT_TYPES = ("headline", "body", "cta")


class Agent:
    def __init__(
        self,
        store: Optional[Store] = None,
        memory: Optional[Memory] = None,
        temperature: float = 0.7,
    ):
        self.store = store or Store()
        self.memory = memory or Memory()
        self.temperature = temperature

    # --------------------------------------------------------------- generate
    def generate_variants(self, brief: dict[str, Any], few_shot_block: str, prompt_version: str) -> dict[str, str]:
        """Call the LLM once and parse out the three ad-copy variants."""
        prompt = prompts.render_generation_prompt(brief, few_shot_block, prompt_version)
        raw = tools.chat(prompt, temperature=self.temperature)
        parsed = tools.extract_json(raw)
        return {
            "headline": str(parsed.get("headline", "")).strip(),
            "body": str(parsed.get("body", "")).strip(),
            "cta": str(parsed.get("cta", "")).strip(),
        }

    # -------------------------------------------------------------------- run
    def run(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Execute the full loop for one brand brief and return outputs + scores."""
        # Imported here to keep module import order clean (evals/feedback import
        # nothing from core, but core depends on them at call time).
        from evals.judge import judge_output
        from feedback.loop import run_feedback

        prompt_version = prompts.ACTIVE_PROMPT_VERSION

        # 1. Retrieve top-3 most relevant high-scoring past outputs.
        retrieved = self.memory.retrieve(brief, k=3)

        # 2. Inject them as few-shot examples.
        few_shot_block = prompts.build_few_shot_block(retrieved)

        # 3. Generate the three variants.
        variants = self.generate_variants(brief, few_shot_block, prompt_version)

        # 4. Evaluate every variant immediately.
        # 5. Persist the run and each scored output.
        run_id = self.store.create_run(brief, prompt_version)

        scored_outputs: list[dict[str, Any]] = []
        for variant_type in VARIANT_TYPES:
            content = variants[variant_type]
            scores = judge_output(brief, variant_type, content)
            self.store.add_output(run_id, variant_type, content, scores, prompt_version)
            scored_outputs.append(
                {
                    "variant_type": variant_type,
                    "content": content,
                    "scores": scores,
                }
            )

        # 6 + 7. Feedback loop: promote good outputs to golden + memory,
        # flag poor ones for review.
        feedback_summary = run_feedback(
            store=self.store,
            memory=self.memory,
            brief=brief,
            run_id=run_id,
            scored_outputs=scored_outputs,
            prompt_version=prompt_version,
        )

        return {
            "run_id": run_id,
            "brief": brief,
            "prompt_version": prompt_version,
            "retrieved_examples": len(retrieved),
            # Surfaced to the frontend so it can show the loop is self-improving.
            "retrieved_count": len(retrieved),
            "outputs": scored_outputs,
            "feedback": feedback_summary,
        }
