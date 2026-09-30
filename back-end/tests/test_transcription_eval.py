"""Non-regression: each scenario's metrics must not drop below baseline.json - tolerance.

Slow (runs the transcription model on every scenario). Deselect with: pytest -m "not slow".
Updating baseline.json requires the user's explicit approval (docs/testing.md).
"""
import json
from pathlib import Path

import pytest

from scripts.eval import METRICS, SOUNDFONT_PATH, evaluate_scenario
from tests.scenarios import SCENARIOS

BASELINE_PATH = Path(__file__).resolve().parents[1] / "baseline.json"

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def baseline():
    assert BASELINE_PATH.exists(), f"{BASELINE_PATH.name} is missing: create it with scripts/eval.py --write (user approval)"
    return json.loads(BASELINE_PATH.read_text())


def test_baseline_matches_environment(baseline):
    assert baseline["soundfont"] == Path(SOUNDFONT_PATH).name, (
        "baseline.json was measured with another soundfont: comparison is invalid"
    )


def test_every_scenario_has_a_baseline(baseline):
    assert set(SCENARIOS) <= set(baseline["scenarios"]), (
        f"no baseline for: {sorted(set(SCENARIOS) - set(baseline['scenarios']))}"
    )


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_no_regression(name, baseline):
    assert name in baseline["scenarios"], f"no baseline for {name}"
    scores = evaluate_scenario(name, baseline["backend"])
    base = baseline["scenarios"][name]
    tolerance = baseline["tolerance"]
    drops = {m: (base[m], scores[m]) for m in METRICS if scores[m] < base[m] - tolerance}
    assert not drops, f"{name} regressed (baseline -> now): {drops}"
