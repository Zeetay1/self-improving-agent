"""CLI to trigger an agent run or a regression eval and print results nicely.

Usage:
    python scripts/run_eval.py run                # run the agent on the example brief
    python scripts/run_eval.py run --brief brief.json
    python scripts/run_eval.py regression         # run golden regression eval
    python scripts/run_eval.py status             # show golden / flagged counts

Uses Rich for clean terminal output.
"""

import argparse
import json
import os
import sys

# Make the project root importable when run as `python scripts/run_eval.py`.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402

console = Console()

EXAMPLE_BRIEF = {
    "brand": "FitFuel",
    "product": "High-protein meal replacement shake",
    "audience": "Busy professionals aged 25-40",
    "tone": "Energetic and no-nonsense",
    "goal": "Drive trial purchases",
}


def _load_brief(path: str | None) -> dict:
    if not path:
        return EXAMPLE_BRIEF
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_run(args: argparse.Namespace) -> int:
    from agent.core import Agent

    brief = _load_brief(args.brief)
    console.print(Panel.fit(json.dumps(brief, indent=2), title="Brand Brief", border_style="cyan"))

    with console.status("[bold green]Running agent loop (retrieve -> generate -> evaluate -> feedback)..."):
        agent = Agent()
        result = agent.run(brief)

    console.print(
        f"\n[bold]Run #{result['run_id']}[/bold]  "
        f"prompt=[magenta]{result['prompt_version']}[/magenta]  "
        f"retrieved few-shot examples=[yellow]{result['retrieved_examples']}[/yellow]\n"
    )

    table = Table(title="Generated Variants & Scores", show_lines=True)
    table.add_column("Variant", style="cyan", no_wrap=True)
    table.add_column("Copy", style="white", max_width=50)
    table.add_column("Hook", justify="right")
    table.add_column("Brand", justify="right")
    table.add_column("Clarity", justify="right")
    table.add_column("Conv", justify="right")
    table.add_column("Weighted", justify="right", style="bold")

    for o in result["outputs"]:
        s = o["scores"]
        table.add_row(
            o["variant_type"],
            o["content"],
            str(s["hook_strength"]),
            str(s["brand_alignment"]),
            str(s["clarity"]),
            str(s["conversion_intent"]),
            f"{s['weighted_average']:.2f}",
        )
    console.print(table)

    fb = result["feedback"]
    console.print(
        f"\n[green]Promoted to golden:[/green] {fb['promoted_to_golden'] or 'none'}   "
        f"[red]Flagged for review:[/red] {fb['flagged_for_review'] or 'none'}"
    )
    return 0


def cmd_regression(args: argparse.Namespace) -> int:
    from evals.runner import format_report, run_golden_eval

    with console.status("[bold green]Running golden regression eval..."):
        report = run_golden_eval()

    table = Table(title=f"Regression Eval - {report.prompt_version}", show_lines=True)
    table.add_column("#", justify="right")
    table.add_column("Variant", style="cyan")
    table.add_column("Baseline", justify="right")
    table.add_column("New", justify="right")
    table.add_column("Delta", justify="right")
    table.add_column("Status", justify="center")

    for i, r in enumerate(report.results, 1):
        status = "[red]REGRESSED[/red]" if r.regressed else "[green]ok[/green]"
        table.add_row(
            str(i), r.variant_type,
            f"{r.baseline_score:.2f}", f"{r.new_score:.2f}",
            f"{r.delta:+.2f}", status,
        )

    if report.count:
        console.print(table)
    console.print()
    if report.passed:
        console.print(Panel.fit("PASS - no entry regressed beyond tolerance.", border_style="green"))
    else:
        console.print(
            Panel.fit(
                f"FAIL - {len(report.regressions)} entry(ies) regressed. "
                "Do not promote this prompt version.",
                border_style="red",
            )
        )
    # Non-zero exit on failure so it can gate CI / a prompt swap.
    return 0 if report.passed else 1


def cmd_status(args: argparse.Namespace) -> int:
    from db.store import Store
    from evals.golden import GoldenDataset

    store = Store()
    golden = GoldenDataset(store=store)
    flagged = store.get_flagged()

    console.print(
        Panel.fit(
            f"Golden entries: [green]{golden.size()}[/green]\n"
            f"Flagged outputs: [red]{len(flagged)}[/red]",
            title="System Status",
            border_style="cyan",
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-improving ad copy agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the agent loop on a brief")
    p_run.add_argument("--brief", help="Path to a brief JSON file (defaults to FitFuel example)")
    p_run.set_defaults(func=cmd_run)

    p_reg = sub.add_parser("regression", help="Run the golden-dataset regression eval")
    p_reg.set_defaults(func=cmd_regression)

    p_status = sub.add_parser("status", help="Show golden / flagged counts")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
