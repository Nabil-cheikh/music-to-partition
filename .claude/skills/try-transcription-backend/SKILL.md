---
name: try-transcription-backend
description: Protocol to evaluate a replacement transcription model (e.g. Transkun, ByteDance piano_transcription_inference, basic-pitch) against the current one on the same scenarios, then record the decision in an ADR. Use when the user wants to try, compare or switch the audio-to-MIDI model.
---

# Try a transcription backend

Read first:
- `docs/transcription-backends.md` for the candidates, published scores and known risks;
- `docs/architecture.md#transcription-layer` for the `TranscriptionBackend` protocol and `RawNote`;
- `docs/adr/0005-transkun-replaces-pop2piano.md` (the current choice and how it was measured).

## Preconditions (in place since 2026-09-27)

- The evaluation is `scripts/eval.py` (`--backend <name>`), with `baseline.json` measured with Transkun.
- The backend interface is `core/transcription/`: `RawNote`, `TranscriptionBackend`, `get_backend`.

## Steps

1. **Work on a spike branch**: `git switch -c spike/<backend>`.
2. **Install into the dev group**: `uv add --group dev <package>`. It moves to main dependencies only if the backend is adopted.
   - Check Python 3.12 compatibility (the project pins `>=3.12,<3.13`) and Linux + macOS support.
   - If installation fails, stop and report the error. Do not change the Python pin without asking.
3. **Write the adapter**: `core/transcription/<backend>_backend.py` implements `transcribe(audio_path) -> list[RawNote]` in seconds, and gets a branch in `get_backend`. Follow `transkun_backend.py`: load the model in `__init__`, never at import.
   - Respect the model's sample rate (Transkun and ByteDance use their own loaders; ByteDance expects 16 kHz).
   - Do not change the notation layer in the same branch.
4. **Run the same evaluation** (`scripts/eval.py --backend transkun` and `--backend <candidate>`), with the same soundfont and machine. Also record:
   - inference time on the longest scenario;
   - install size delta (`du -sh .venv` before and after);
   - first-run downloads (checkpoint size and source).
5. **Report** one table: scenario × backend (onset F1, onset+offset F1), plus time and size.
6. **Record the decision** with the `write-adr` skill, as an ADR superseding ADR-0005 if adopted, or "rejected" with the numbers. Update `docs/transcription-backends.md` with the measured results.
7. **If adopted**:
   - move the dependency to main;
   - move the old backend's dependencies into an optional uv group, as was done for `pop2piano`;
   - reconsider the `[tool.uv] environments` restriction;
   - establish a new baseline **with user approval**;
   - update CLAUDE.md and `docs/libraries.md`.

## Rules

- Same scenarios, same metrics, same machine. Otherwise the comparison is invalid.
- Don't tune thresholds for one backend on the test scenarios and then report those same scenarios as the result. That overfits. If you tune, say so.
