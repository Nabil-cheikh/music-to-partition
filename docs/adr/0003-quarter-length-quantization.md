# ADR-0003: quantize to quarter lengths with a single global tempo

- **Status**: superseded by [ADR-0006](0006-notation-tempo-grid-voices.md)
- **Date**: written 2026-09-27, retroactively
- **Deciders**: project owner

## Context
Transcription models output onsets and offsets in seconds. A score needs positions and durations in beats.

## Decision
In `core/processing.py`:
1. Estimate one BPM and the first-beat offset with `librosa.beat.beat_track`.
2. Convert seconds to quarter lengths: `(t - offset) * bpm / 60`.
3. Snap start times to a 0.5 grid (`_quantize_time`) and durations to `VALID_DURATIONS` = 4, 3, 2, 1.5, 1, 0.5, 0.25 (`_quantize_to_nearest`).
4. Drop notes shorter than `MIN_QUARTER_LENGTH`, and deduplicate (time, pitch) pairs by keeping the highest velocity.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Tempo map from all beat times (piecewise conversion) | handles rubato and tempo drift | more code, beat tracking errors propagate |
| Adaptive grid (choose 8th / 16th / triplet per beat by least error) | represents triplets and 16ths | needs careful tests to avoid over-fragmentation |
| music21 `quantize()` | built in | same fixed-grid limits |
| PM2S (neural beat tracking from MIDI) | state of the art for performance MIDI → score | research code, old pins (Python 3.8 / torch 1.12) |

## Consequences
- Simple and deterministic, so it is easy to unit test (`tests/test_processing_units.py`).
- A BPM error of ×2 or ×0.5 shifts every note. There are no triplets or 16th positions, and rubato breaks the grid.
- Quantization sat inside `recognize_notes_structured`, mixed with transcription. [ADR-0006](0006-notation-tempo-grid-voices.md) moved it into a separate notation layer.
