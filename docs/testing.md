# Testing and non-regression

## Principles

1. **Deterministic code gets strict TDD. The ML model gets metric-based evaluation.** A model's output is probabilistic: a single "was note X detected" assertion is either flaky or so loose that it never fails. A score compared to a baseline catches gradual quality loss. See [ADR-0004](adr/0004-eval-driven-development.md).
2. **A test that cannot fail is worse than no test.** It gives false confidence to anyone changing the code, human or AI.
3. **Test each layer in its own units.** Transcription is scored in **seconds** on `RawNote`s. Notation is scored in **quarter lengths** on the final score notes.

## Test suites

| Suite | File(s) | Speed | Guards |
|---|---|---|---|
| Quantization and tempo | `tests/test_quantization.py`, `tests/test_processing.py` | < 5 s | note cleaning, tempo folding, `TempoMap` (steady, rubato, anchor), `choose_grids`, `quantize_notes` |
| Score | `tests/test_sheet_generator.py` | < 2 s | hand split, legato filling, voices, measures, ties, triplets, dotted rhythms, MusicXML export; PDF + `.ly` cleanup (needs LilyPond) |
| API | `tests/test_api.py` | < 1 s | extension check, path traversal, temp-file cleanup, schema, PDF response (model and LilyPond mocked) |
| Legacy helpers | `tests/test_processing_units.py` | < 1 s | old quantization helpers kept in `core/quantization.py` (not used by the pipeline anymore) |
| **Transcription eval** | `scripts/eval.py`, `tests/test_transcription_eval.py`, `tests/scenarios.py`, `baseline.json` | ~2 min | per-scenario metrics must not drop below the baseline |
| Legacy transcription | `tests/test_transcription.py` (marker `slow`) | ~20 s | old pass/fail tests. They contain forbidden patterns (below), and their scenarios were migrated to `scenarios.py` |

```bash
cd back-end
uv run pytest -m "not slow"                         # everything fast (seconds)
uv run python scripts/eval.py --compare baseline.json   # transcription + score metrics (~2 min)
uv run pytest -m slow                               # eval as tests + legacy suite
```

## Non-regression protocol

| You changed… | Run | Pass criterion |
|---|---|---|
| `core/quantization.py`, `core/sheet_generator.py`, tempo code | `pytest -m "not slow"` **and** `scripts/eval.py --compare baseline.json` | all green; no scenario below baseline − tolerance |
| `core/transcription/` or a model dependency | `scripts/eval.py --compare baseline.json` | same |
| `api/`, `models/schemas.py` | `pytest -m "not slow"`; for `schemas.py`, also check the front-end | all green |
| `tests/scenarios.py` (new scenario) | `scripts/eval.py --only <name>` | report its scores. **It has no baseline until the user approves adding it** |
| `front-end/` | `npm run lint && npm run build` | no errors |
| Dependencies | everything above | same as above |

Report results as **before → after**, e.g. "score 0.90 → 0.92, dur 0.80 → 0.85, no regression". The `verify-change` and `eval-transcription` skills automate this.

## The metrics

| Column | Layer | Definition |
|---|---|---|
| `onset` | transcription | `mir_eval` note F1: pitch correct, onset within ±50 ms |
| `on+off` | transcription | same, and the offset within 20 % of the duration (min 50 ms) |
| `score` | notation | F1 on (pitch, position in quarter lengths) of the final score notes against the ground truth, positions relative to the first note. A tempo read at ×2 or ×½ is accepted (rescaled); ×3/2 is not. |
| `dur` | notation | among the well-placed notes, the share that also have the exact duration |

How to read a change:
- `onset` moves: the model changed.
- `score` or `dur` moves with `onset` stable: notation changed.
- `bpm` wrong: tempo estimation.

## baseline.json

- Produced by `scripts/eval.py --write baseline.json`, plus a top-level `"tolerance"` field.
- It records the backend and the soundfont. A different soundfont invalidates the comparison (`test_baseline_matches_environment`).
- The tolerance is set above the measured run-to-run noise. Transkun + FluidSynth is deterministic on CPU: two identical runs gave a difference of 0, so `tolerance = 0.01`.
- **Only the user approves updating it.** An approved update goes in its own commit, with old → new mean scores in the message.

## Forbidden patterns

These make a test pass without the behaviour improving. Never introduce them. When you meet them (the legacy `test_transcription.py` has several), report them; do not copy them.

| Pattern | Example (legacy suite) | Why it's wrong |
|---|---|---|
| Skip on failure | `TestHandOffset.test_left_hand_delayed`: `except AssertionError: pytest.skip(...)` | A regression shows as "skipped", which looks harmless. |
| Tautology | `TestNoteDurations.test_mixed_block_has_varying_durations`: `assert len(durations) >= 1` | It can never fail. |
| Guard that passes when nothing is detected | `if block1 and block2:` before the assert | Zero detected notes makes the test green. |
| Loosening a threshold to get green | `found >= 6` → `found >= 4`, `time_tolerance=2.0` → `3.0` | It hides the regression the test was written to catch. |
| Tolerances wider than the thing measured | `time_tolerance=2.0` quarter lengths on notes 1.0 apart | Any neighbouring note matches. |
| Silently editing the baseline | overwriting `baseline.json` so a drop disappears | Only the user decides to accept a new baseline. |
| Tuning parameters on the eval scenarios, then reporting those scenarios as proof | raising `LEGATO_MAX_GAP_RATIO` until one scenario passes | That is overfitting: say so, or validate on a held-out scenario or a real recording. |

An **environment skip** is allowed, e.g. `skipif(no LilyPond)`. It must be reported as "not run", never as passing.

## Writing a scenario

`tests/scenarios.py` is pure data. Each scenario is a tempo plus `(midi_pitch, start_sec, end_sec, velocity)` tuples, built with `_beats(bpm, [(pitch, start_beat, duration_beats), ...])`. That helper shifts everything by one beat, so nothing starts at t=0.

- **One musical difficulty per scenario**, and the name says what is hard.
- Use beat fractions (`1/3`, `0.25`, `1.5`), never raw seconds.
- The `add-music-scenario` skill does this from a musical description.
- If the difficulty is purely rhythmic, also add a deterministic test in `test_sheet_generator.py` or `test_quantization.py` with the already-quantized notes. It isolates notation from the model.

## Limits of the synthetic corpus

FluidSynth audio with the small `TimGM6mb.sf2` is cleaner than a real piano, and its timbre makes Transkun cut note ends early. Synthetic results are therefore both optimistic (no room noise, perfect timing) and pessimistic (`on+off`). **Next step**: add 3–5 real recordings with ground-truth MIDI, e.g. a small MAESTRO subset (CC BY-NC-SA 4.0). See [roadmap](roadmap-transcription-quality.md).
