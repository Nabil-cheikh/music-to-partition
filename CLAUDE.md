# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music-to-partition converts piano audio (.wav, .mp3, .aac, .m4a) into a two-staff piano score PDF.
Pipeline: upload → **Transkun** (audio → notes in seconds) → tempo selection → adaptive quantization → hands / voices → music21 → LilyPond → PDF.
Stack: React 19 + Vite + Tailwind 4 front-end, FastAPI back-end (Python 3.12, uv).

Current focus: transcription quality on complex pieces (per-note durations, chords, offset hands). Progress is measured by `scripts/eval.py` against `back-end/baseline.json` (score 0.905, dur 0.821 on 2026-09-27). See [docs/roadmap-transcription-quality.md](docs/roadmap-transcription-quality.md).

## Read before touching

| If you change… | Read first |
|---|---|
| `back-end/core/transcription/` (backends, `RawNote`) | [docs/architecture.md#transcription-layer](docs/architecture.md#transcription-layer), [ADR-0005](docs/adr/0005-transkun-replaces-pop2piano.md), [docs/transcription-backends.md](docs/transcription-backends.md), then the `try-transcription-backend` skill to switch models |
| `back-end/core/processing.py` (tempo), `back-end/core/quantization.py` | [docs/architecture.md#notation-layer](docs/architecture.md#notation-layer), [ADR-0006](docs/adr/0006-notation-tempo-grid-voices.md) |
| `back-end/core/sheet_generator.py` | [docs/architecture.md#score-coresheet_generatorpy](docs/architecture.md#score-coresheet_generatorpy), [ADR-0006](docs/adr/0006-notation-tempo-grid-voices.md), [ADR-0002](docs/adr/0002-music21-lilypond-for-rendering.md) |
| `back-end/models/schemas.py` (API contract, units!) | [docs/architecture.md#data-contract-notesegment--recognizenotesresponse](docs/architecture.md#data-contract-notesegment--recognizenotesresponse) |
| Anything in `back-end/tests/`, `back-end/scripts/eval.py`, `baseline.json` | [docs/testing.md](docs/testing.md), [ADR-0004](docs/adr/0004-eval-driven-development.md) |
| Dependencies (`pyproject.toml`, `uv.lock`, `package.json`) | [docs/libraries.md](docs/libraries.md) |

## Hard rules

1. **No fake green.** Never make a test pass by:
   - loosening a threshold or tolerance;
   - adding `pytest.skip`, `try/except AssertionError` or `if detected:` guards;
   - writing an assertion that cannot fail;
   - deleting a test.

   If an expectation is wrong, say so and let the user decide. The forbidden patterns, with examples, are in [docs/testing.md](docs/testing.md#forbidden-patterns).
2. **Never update `back-end/baseline.json`** unless the user explicitly asks, and never tune parameters on the eval scenarios and then present those scenarios as proof (overfitting: say so).
3. **Report before → after numbers** for any change touching transcription or notation.
4. **Keep transcription and notation separate.** Don't fix a model problem with notation hacks, or the reverse, without saying so.
5. **Architecture decisions get an ADR** (`write-adr` skill): swapping a library or model, changing the `NoteSegment` contract, changing the pipeline structure or the testing strategy.
6. **Keep docs true.** If you change something a doc describes, update that doc in the same change.

## Definition of Done

Run the `verify-change` skill. It picks the right checks from what changed. The manual equivalent:

| Changed | Command (run in the given folder) |
|---|---|
| Any back-end code | `uv run pytest -m "not slow"` in `back-end/` (seconds) |
| Transcription, tempo, quantization, sheet generation | also `uv run python scripts/eval.py --compare baseline.json` in `back-end/` (~2 min, exit 1 on regression), or the `eval-transcription` skill |
| Front-end | `npm run lint && npm run build` in `front-end/` |

## Commands

Back-end (from `back-end/`):
```bash
uv sync                                  # deps + dev group (pytest, pyfluidsynth, mir-eval, ...)
uv run uvicorn api.main:app --reload     # API on :8000 (Transkun loads on the first request)
uv run pytest -m "not slow"              # fast tests: quantization, sheet generator, API
uv run python scripts/eval.py --compare baseline.json   # transcription + score metrics
uv run pytest -m slow                    # eval as tests + legacy transcription tests
uv run pytest -k <name>                  # single test
TRANSCRIPTION_BACKEND=pop2piano ...      # old backend (needs: uv sync --group pop2piano)
```

Front-end (from `front-end/`):
```bash
npm install && npm run dev               # package-lock.json is committed
npm run lint && npm run build
```

## Platforms and system dependencies

- **macOS and Linux** are supported natively. `pyproject.toml` restricts uv to darwin/linux (the optional Pop2Piano group needs `essentia`, and Windows support of Transkun's `ncls` is unverified). **Windows**: use WSL2.
- **LilyPond** (required for PDFs): `brew install lilypond` / `sudo apt install lilypond` / `sudo dnf install lilypond`, or the portable Linux build without root. It is resolved via `LILYPOND_PATH`, then `PATH`. Without it, the PDF test is skipped: report that as "not run".
- **FluidSynth + soundfont** (tests only): `brew install fluid-synth` / `sudo apt install fluidsynth fluid-soundfont-gm`. Override the soundfont with `SOUNDFONT_PATH`.
- **ffmpeg**: recommended, needed to decode .aac/.m4a.
- Front-end config: `VITE_API_URL` in `front-end/.env` (default `http://localhost:8000`).

## Project skills (`.claude/skills/`)

| Skill | Use it when |
|---|---|
| `verify-change` | before saying any change is done |
| `add-music-scenario` | adding a test case from a musical description |
| `eval-transcription` | after touching transcription; "is it better?" |
| `try-transcription-backend` | comparing or switching the audio → MIDI model |
| `write-adr` | recording an architecture decision |
