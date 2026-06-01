"""Regression test suite.

Loads the golden dataset and runs the eval runner against the active prompt
version, asserting that no golden entry regresses more than 0.5 from its
baseline score.

Run with:  pytest tests/test_regression.py

Notes:
- Requires GROQ_API_KEY (the runner regenerates + re-judges via Groq). If it is
  not set, the test is skipped rather than failing spuriously.
- If the golden dataset is empty (fresh install, no runs yet), there is nothing
  to regress against and the test passes trivially.
"""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from evals.golden import GoldenDataset  # noqa: E402
from evals.runner import REGRESSION_TOLERANCE, format_report, run_golden_eval  # noqa: E402


@pytest.fixture(scope="module")
def golden() -> GoldenDataset:
    return GoldenDataset()


def test_no_golden_regressions(golden: GoldenDataset):
    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY not set; regression eval needs live model calls.")

    if golden.size() == 0:
        pytest.skip("Golden dataset is empty; nothing to regress against yet.")

    report = run_golden_eval(golden=golden)

    # Print a readable summary so failures are diagnosable in CI logs.
    print("\n" + format_report(report))

    assert report.passed, (
        f"{len(report.regressions)} golden entry(ies) regressed more than "
        f"{REGRESSION_TOLERANCE} against prompt '{report.prompt_version}'. "
        "Do not promote this prompt version."
    )
