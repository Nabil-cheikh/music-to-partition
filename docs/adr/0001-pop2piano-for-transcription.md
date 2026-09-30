# ADR-0001: Pop2Piano as the transcription model

- **Status**: superseded by [ADR-0005](0005-transkun-replaces-pop2piano.md)
- **Date**: written 2026-09-27, retroactively for commit `e400030`
- **Deciders**: project owner

## Context
The first version used Spotify basic-pitch. It performed poorly on complex pieces: basic-pitch is instrument-agnostic, and its published piano onset+offset F1 on MAESTRO is 10.5 %. Pop2Piano was adopted on an AI assistant's suggestion, loaded through `transformers`.

Pop2Piano is a **piano cover generator**: a T5 model trained on {pop song, YouTube piano cover} pairs, producing an *arrangement* conditioned on a "composer" token. It was never evaluated as a transcription model and it does not try to reproduce the input notes.

## Decision
Use `Pop2PianoForConditionalGeneration` (`sweetcocoa/pop2piano`, `composer="composer1"`) to turn audio into MIDI in `core/processing.py`.

## Alternatives considered
See [transcription-backends.md](../transcription-backends.md) for the full comparison.

| Option | Pros | Cons |
|---|---|---|
| basic-pitch | tiny, fast | weak on piano (onset+offset F1 10.5 %), officially Python ≤ 3.11 |
| Transkun V2 | best published piano scores (98.4 / 93.1 %), MIT, pip, checkpoint bundled | Python 3.12 compatibility unverified |
| ByteDance piano_transcription | strong (96.7 / 82.5 %), pedal detection, MIT | repo archived Dec 2025 |

## Consequences
- Heavy dependencies: `transformers`, `torch`, `essentia` (no Windows wheels, hence the macOS/Linux-only uv environments), `pretty-midi==0.2.9` (which needs `setuptools<82`).
- The model loads at import, so startup is slow.
- **Transcription is unfaithful by design on solo-piano input.** This likely explains part of the failing chord and duration scenarios.
- **Review trigger**: once `scripts/eval.py` exists, benchmark Transkun V2 (then ByteDance) on the same scenarios. If a candidate is clearly better on onset+offset F1, write ADR-000X superseding this one, and keep Pop2Piano only if a "pop song → arrangement" feature is wanted.
