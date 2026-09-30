# ADR-0004: evaluation-driven development for transcription, TDD for notation

- **Status**: accepted (implemented: `scripts/eval.py`, `tests/scenarios.py`, `baseline.json`)
- **Date**: 2026-09-27
- **Deciders**: project owner

## Context
The project moved to TDD on synthesized scenarios (`tests/test_transcription.py`) to improve detection of complex pieces. Transcription is a probabilistic model, so its tests had to be permissive to pass at all:
- `pytest.skip` on failure;
- `assert len(durations) >= 1`;
- `if block1 and block2:` guards;
- thresholds like 4/8 notes;
- a 2.0 quarter-length time tolerance.

As a result they **cannot detect a regression**: a change that drops accuracy from 8/8 to 6/8 stays green. When code is written mostly by an AI assistant, that is exactly the failure mode to prevent.

## Decision
- **Transcription** (audio → notes in seconds) is evaluated with `mir_eval` note-level metrics (onset F1, onset+offset F1) per scenario, compared to a committed `baseline.json`. A regression is a drop larger than a measured tolerance. Updating the baseline needs explicit user approval.
- **Notation** (notes → quantized score) is deterministic and gets strict TDD with exact inputs and exact expected outputs.
- The existing scenario definitions are kept as ground truth; only the assertions change. See [testing.md](../testing.md#test-suites).

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Keep pass/fail TDD, tighten thresholds | no new tooling | flaky; still binary; still mixes BPM and transcription errors |
| Snapshot/golden outputs of the model | catches any change | any model change breaks everything; says nothing about "better" or "worse" |
| Metrics + baseline (chosen) | shows improvement and regression, per scenario; lets backends be compared | needs `scripts/eval.py` (~1–1.5 d) and a tolerance measurement |

## Consequences
- New dev dependency: `mir_eval`.
- New files: `tests/scenarios.py`, `scripts/eval.py`, `baseline.json`.
- Transcription must expose raw notes in seconds before quantization (see [ADR-0003](0003-quarter-length-quantization.md)).
- Every transcription change reports a before/after table. The `eval-transcription` and `verify-change` skills enforce this.
- Until the script exists, `tests/test_transcription.py` stays the reference, with the rule "no test newly failing, no new skip".
