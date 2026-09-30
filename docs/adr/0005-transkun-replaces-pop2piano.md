# ADR-0005: Transkun V2 replaces Pop2Piano as the transcription backend

- **Status**: accepted
- **Date**: 2026-09-27
- **Deciders**: project owner
- **Supersedes**: [ADR-0001](0001-pop2piano-for-transcription.md)

## Context
ADR-0001 flagged Pop2Piano as a cover *generator*. On the synthesized scenarios, its raw output confirmed it:
- a single-note melody (14 × C4) came out as **42 notes** harmonized as C3-C4-G3 chords;
- every note lasted a fixed ~0.25 s;
- the first second was dropped.

The published comparison ([transcription-backends.md](../transcription-backends.md)) pointed to Transkun V2, then ByteDance, for faithful piano transcription.

## Decision
- Add a `TranscriptionBackend` interface (`core/transcription/`) returning `RawNote`s in seconds.
- Make **Transkun V2** the default backend (`transkun>=2.0.1`, checkpoint bundled in the wheel).
- Move Pop2Piano behind the same interface, in the optional uv group `pop2piano`.

## Measured results
11 scenarios, FluidSynth + `TimGM6mb.sf2`, CPU, same notation code for both backends (`scripts/eval.py`):

| Backend | onset F1 | on+off F1 | score | dur |
|---|---|---|---|---|
| Pop2Piano | 0.407 | 0.157 | 0.403 | 0.315 |
| **Transkun V2** | **0.985** | **0.705** | **0.905** | **0.821** |

The old app (Pop2Piano + old notation, commit `30416fa`) scored **score 0.407, dur 0.241** on the same scenarios.

Runtime: ~110 s for the 11 scenarios with Transkun, against ~16 s with Pop2Piano. Transkun is slower, but still fine for a request-per-upload API. It has not been measured on long real pieces.

## Alternatives considered
| Option | Why not (now) |
|---|---|
| ByteDance `piano_transcription_inference` | lower published scores (96.7 / 82.5 %), repo archived Dec 2025. Kept as fallback. |
| basic-pitch | onset+offset F1 10.5 % on MAESTRO, officially Python ≤ 3.11 |
| Keep Pop2Piano | unfaithful by design (numbers above) |

## Consequences
- Default dependencies dropped: `transformers`, `essentia`, `resampy`, the `pretty-midi==0.2.9` pin and the `setuptools<82` constraint. `essentia` was the reason for the macOS/Linux-only restriction. It is kept for now, because Windows support of Transkun's dependency `ncls` is unverified.
- Models load lazily on the first transcription, not at import.
- `on+off` stays around 0.7 on synthetic audio: Transkun cuts note ends early on this timbre. The notation layer partly compensates ([ADR-0006](0006-notation-tempo-grid-voices.md)).
- `baseline.json` was created from this measurement (tolerance 0.01; two runs gave identical numbers).
