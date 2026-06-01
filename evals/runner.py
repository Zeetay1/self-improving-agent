"""Eval runner: runs the golden dataset against any prompt config and checks
for regressions.

For each golden entry we regenerate copy for the same brief + variant using the
prompt version under test, re-judge it, and compare the new weighted score to
the entry's stored baseline. If any entry drops by more than REGRESSION_TOLERANCE
(0.5), the run is marked failed.

This is what guards a prompt-version swap (see agent/prompts.py) and what the
pytest regression suite drives.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from agent import prompts, tools
from evals.golden import GoldenDataset
from evals.judge import judge_output

# A golden entry may not drop more than this from its baseline before we fail.
REGRESSION_TOLERANCE = 0.5


@dataclass
class EntryResult:
    brief: dict[str, Any]
    variant_type: str
    baseline_score: float
    new_score: float
    new_output: str
    regressed: bool

    @property
    def delta(self) -> float:
        return round(self.new_score - self.baseline_score, 4)


@dataclass
class EvalReport:
    prompt_version: str
    results: list[EntryResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(r.regressed for r in self.results)

    @property
    def regressions(self) -> list[EntryResult]:
        return [r for r in self.results if r.regressed]

    @property
    def count(self) -> int:
        return len(self.results)


def _generate_variant(brief: dict[str, Any], variant_type: str, prompt_version: str) -> str:
    """Regenerate a single variant for a brief using a given prompt version.

    Few-shot examples are intentionally omitted so the regression isolates the
    prompt itself rather than whatever happens to be in memory.
    """
    prompt = prompts.render_generation_prompt(brief, few_shot_block="", version=prompt_version)
    raw = tools.chat(prompt, temperature=0.7)
    parsed = tools.extract_json(raw)
    return str(parsed.get(variant_type, "")).strip()


def run_golden_eval(
    prompt_version: Optional[str] = None,
    golden: Optional[GoldenDataset] = None,
) -> EvalReport:
    """Run every golden entry against `prompt_version` (defaults to active)."""
    prompt_version = prompt_version or prompts.ACTIVE_PROMPT_VERSION
    golden = golden or GoldenDataset()

    report = EvalReport(prompt_version=prompt_version)

    for entry in golden.all():
        brief = entry["brief"]
        variant_type = entry["variant_type"]
        baseline = float(entry["weighted_average"])

        new_output = _generate_variant(brief, variant_type, prompt_version)
        new_scores = judge_output(brief, variant_type, new_output)
        new_score = float(new_scores["weighted_average"])

        regressed = (baseline - new_score) > REGRESSION_TOLERANCE
        report.results.append(
            EntryResult(
                brief=brief,
                variant_type=variant_type,
                baseline_score=baseline,
                new_score=new_score,
                new_output=new_output,
                regressed=regressed,
            )
        )

    return report


def format_report(report: EvalReport) -> str:
    """Plain-text summary of a regression run (used as a fallback to Rich)."""
    lines = [
        f"Regression eval for prompt version: {report.prompt_version}",
        f"Entries checked: {report.count}",
        f"Tolerance: drop > {REGRESSION_TOLERANCE} fails",
        "",
    ]
    if report.count == 0:
        lines.append("No golden entries yet — nothing to check. (PASS)")
        return "\n".join(lines)

    for i, r in enumerate(report.results, 1):
        status = "REGRESSED" if r.regressed else "ok"
        lines.append(
            f"  [{i}] {r.variant_type:8s} baseline={r.baseline_score:.2f} "
            f"new={r.new_score:.2f} delta={r.delta:+.2f}  {status}"
        )

    lines.append("")
    if report.passed:
        lines.append("RESULT: PASS — no entry regressed beyond tolerance.")
    else:
        lines.append(
            f"RESULT: FAIL — {len(report.regressions)} entry(ies) regressed beyond "
            f"{REGRESSION_TOLERANCE}. Do not promote this prompt version."
        )
    return "\n".join(lines)
