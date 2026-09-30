---
name: add-music-scenario
description: Turn a musical description (e.g. "right-hand triplets over left-hand half notes at 90 BPM", "held bass note under a moving melody") into a synthesized ground-truth test scenario for the transcription pipeline. Use when the user wants a new test case, wants to reproduce a piece the app gets wrong, or asks to cover a musical difficulty.
---

# Add a music scenario

Read `docs/testing.md#writing-a-transcription-scenario` first.

## 1. Pin down the music

Get these from the description, and ask the user only if something is ambiguous:
- **the difficulty** being tested (one per scenario);
- tempo (BPM);
- notes per hand: pitch, start, duration;
- velocity (default 100).

Name the scenario after the difficulty in snake_case, e.g. `held_bass_moving_melody`.

## 2. Write the ground truth

In `back-end/tests/scenarios.py`, add an entry to `SCENARIOS`:

```python
"held_bass_moving_melody": Scenario(
    "LH whole notes held under RH eighth-note melody",
    100, _beats(100, [(C3, 0, 4), (G2, 4, 4)] + [(p, i * 0.5, 0.5) for i, p in enumerate([E4, G4, ...])])),
```

- `_beats(bpm, [(pitch, start_beat, duration_beats), ...])` converts to seconds and shifts everything by one beat, so nothing starts at t=0.
- Use beat fractions (`1/3` for triplet eighths, `0.25` for sixteenths, `1.5` for a dotted quarter). Use the MIDI constants at the top of the file, and add missing ones there.
- Keep both hands' total lengths consistent, so no voice ends before the other without reason.

## 3. No baseline yet

The parametrized `tests/test_transcription_eval.py::test_no_regression[<name>]` will now **fail** with "no baseline for <name>". That is expected and honest. Tell the user and show the scenario's first scores. Adding it to `baseline.json` requires their approval: after approval, run `scripts/eval.py --write` and merge only that scenario's entry.

If the difficulty is rhythmic (durations, chords, voices, triplets), also add a deterministic test in `tests/test_sheet_generator.py` or `tests/test_quantization.py` with the already-quantized notes. It isolates notation bugs from model errors.

## 4. Check it

- From `back-end/`: `uv run python scripts/eval.py --only <name>`, about 10–20 s per scenario.
- Report the four metrics and the detected BPM. If a score is low, say which layer is at fault: `onset` low means the model; `score` or `dur` low with `onset` ≈ 1 means notation or tempo.
- Don't change notation parameters just to make the new scenario pass (overfitting; see docs/testing.md).
