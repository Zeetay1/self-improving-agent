"""The main agent loop: retrieve -> generate -> evaluate -> store -> feedback.

Synchronous and dependency-injected so the API, CLI, and tests share one path.
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

    def run(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Execute the full loop for one brand brief and return outputs + scores."""
        # imported here to avoid an import cycle (core <-> evals/feedback)
        from evals.judge import judge_output
        from feedback.loop import run_feedback

        prompt_version = prompts.ACTIVE_PROMPT_VERSION

        retrieved = self.memory.retrieve(brief, k=3)
        few_shot_block = prompts.build_few_shot_block(retrieved)
        variants = self.generate_variants(brief, few_shot_block, prompt_version)

        # judge each variant and persist the run
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

        # promote winners to golden + memory, flag the weak ones
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
            "retrieved_count": len(retrieved),  # what the frontend reads
            "outputs": scored_outputs,
            "feedback": feedback_summary,
        }
