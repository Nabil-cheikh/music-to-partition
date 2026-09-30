# Roadmap: transcription quality

Goal: complex piano pieces (per-note durations, chords, hands with offset timing) produce a correct score, with **measurable** progress and no silent regressions.

Current state, from `baseline.json` (2026-09-27): **onset 0.985 · on+off 0.705 · score 0.905 · dur 0.821**, against score 0.407 / dur 0.241 for the old app.

## Done (2026-09-27)

| Step | Where | Result |
|---|---|---|
| Metric-based evaluation, scenario corpus, baseline | `scripts/eval.py`, `tests/scenarios.py`, `baseline.json`, `tests/test_transcription_eval.py` | 11 scenarios; regressions exit non-zero; deterministic (0.0 run-to-run) |
| Transcription and notation split behind `TranscriptionBackend` | `core/transcription/` | backends swappable, models loaded lazily |
| Backend switch to Transkun V2 | [ADR-0005](adr/0005-transkun-replaces-pop2piano.md) | onset 0.407 → 0.985 |
| Tempo selection (two trackers + grid fit) | `estimate_tempo`, `choose_bpm` | score 0.757 → 0.905 |
| Adaptive grid (sixteenths / triplets), long-note end snapping | `core/quantization.py` | dur 0.795 → 0.821 |
| Voices, per-note durations, explicit measures, ties | `core/sheet_generator.py` | chords with different durations are written correctly |
| Continuity hand split, legato gap filling, ghost-note cleaning | `core/sheet_generator.py`, `core/quantization.py` | TDD-covered |
| Notation and API tests | `tests/test_quantization.py`, `tests/test_sheet_generator.py`, `tests/test_processing.py`, `tests/test_api.py` | 65 fast tests |

## Open problems (from the baseline)

| Scenario | score / dur | Cause | Idea (verify with the eval, don't tune on it) |
|---|---|---|---|
| `triplets_over_quarters` | 0.125 / 0.000 | tempo read as 135 instead of 90: triplet eighths are equivalent to eighths at ×3/2 | use the left hand's regular pulse; prefer the tempo where the lowest voice is on beats |
| `wide_chords_both_hands` | 0.933 / 0.500 | chord ends cut early by the model; the gap is too large for the legato rule | check on real recordings first: this may be a soundfont artifact |
| `hand_offset`, `scale_with_accompaniment` | 0.968–1.0 / 0.875–1.0 | one missed or extra note | — |
| all | on+off ≈ 0.7 | Transkun offsets short on the TimGM6mb timbre | try another soundfont (FluidR3_GM) as a second corpus |

## Next steps

1. **Real recordings**: add 3–5 short real piano recordings with ground-truth MIDI, e.g. a MAESTRO subset (CC BY-NC-SA 4.0), as a second corpus in the eval. This is the only way to know whether the synthetic-audio compromises (legato threshold, offsets) hold on real pianos.
2. **Triplet / tempo ambiguity**: see the table above.
3. **Downbeat and time signature**: pickups currently start measure 1, and 4/4 is hard-coded.
4. **Key signature**: music21 `analyze('key')` on the final notes, then respell accidentals.
5. **MusicXML download** in the API (already tested in `test_sheet_generator.py`), so users can fix scores in MuseScore.
6. **Pedal**: Transkun detects it (with an alternative checkpoint); it could be rendered as pedal marks.

## Out of scope for now

- Multi-instrument input (MT3 / YourMT3+).
- A GPU server: measure long real pieces first.
