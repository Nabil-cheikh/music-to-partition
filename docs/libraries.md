# Libraries

Versions are the ones resolved in `back-end/uv.lock` and `front-end/package-lock.json` as of 2026-09-27. Before upgrading anything in this list, read its entry and run the checks in [testing.md](testing.md#non-regression-protocol). For anything touching transcription or tempo, that includes `scripts/eval.py --compare baseline.json`.

## Back-end: transcription

### `transkun` (2.0.1) + `torch` (2.11)
- **Why**: Transkun V2 piano transcription, the default backend. See [ADR-0005](adr/0005-transkun-replaces-pop2piano.md).
- **Gotchas**:
  - The checkpoint (`transkun/pretrained/2.0.pt`, 56 MB) and its conf **ship inside the wheel**, so there is no download at runtime.
  - We load the model ourselves in `core/transcription/transkun_backend.py`, via `importlib.resources`. Its CLI (`transkun.transcribe.main`) uses the deprecated `pkg_resources`; don't call it.
  - Input is 44.1 kHz (`model.fs`), shaped `(samples, channels)`. We pass mono `(N, 1)`.
  - Output notes with `pitch <= 0` are pedal events (control changes). We drop them.
  - Its own dependencies pull `mir-eval`, `pretty-midi`, `pydub`, `soxr`, `ncls`, `tensorboard` and `seaborn`: heavy but harmless. Windows support of `ncls` is unverified.
- The model is loaded on the first transcription (lazy `get_backend`), so the first API call is slower.

### Optional group `pop2piano`: `transformers`, `essentia`, `resampy`
- **Why**: only for the old Pop2Piano backend (`TRANSCRIPTION_BACKEND=pop2piano`) and for reproducing old numbers. Install with `uv sync --group pop2piano`.
- **Gotchas**:
  - `essentia` has no Windows wheels.
  - The model (~450 MB) downloads from Hugging Face on first use.
  - The Hugging Face docs pin `pretty-midi==0.2.9`; we no longer do. If Pop2Piano breaks with pretty-midi 0.2.11, pin it inside that group only.

### `librosa` (0.11)
- **Why**: audio loading and resampling, beat tracking (audio and onset-envelope), MIDI ↔ note names.
- **Gotchas**:
  - `beat_track` returns `tempo` as a **1-element ndarray**. Use `np.atleast_1d(tempo)[0]` (see `_track`).
  - Tempo estimates are often off by ×2, ×½, ×⅔ or ×3/2. `choose_bpm` exists because of this.
  - `ffmpeg` is needed to decode .aac/.m4a.

## Back-end: notation and rendering

### `music21` (9.9)
- **Why**: the score object model (parts, measures, voices, chords, ties, tuplets) and delegation to LilyPond.
- **Gotchas**:
  - Measures are built by hand in `build_part` instead of `makeMeasures()`, because we need voices and exact barline splitting.
  - Durations must be "writable" (`_WRITABLE`): complex quarter lengths like 1.25 are split and tied by `_split_duration`.
  - `score.write('lily.pdf', fp=X)` writes the LilyPond source to `X` (no extension), runs `lilypond` via `os.system` with unquoted paths, and returns `X.pdf`. We delete `X`.
  - The LilyPond path is stored in music21's per-user `UserSettings` file; `_configure_lilypond` overwrites it on every call.

### LilyPond (system binary)
- **Why**: engraving to PDF. It is resolved via `LILYPOND_PATH`, then `PATH`.
- Without it, the API's `/generate-sheet/` fails with a clear `RuntimeError`, and `TestGeneratePianoSheet` is skipped.
- A portable Linux build ([lilypond-2.24.4-linux-x86_64.tar.gz](https://gitlab.com/lilypond/lilypond/-/releases)) works without root: extract it and point `LILYPOND_PATH` at `bin/lilypond`.

## Back-end: API

### `fastapi` (0.135), `uvicorn`, `python-multipart`
- Endpoints are sync `def` on purpose, so inference runs in the threadpool instead of blocking the event loop.
- `python-multipart` is needed for `UploadFile`.

## Back-end: dev / tests (`[dependency-groups] dev`)

| Package | Why |
|---|---|
| `pytest` (9) | `pythonpath = ["."]`; marker `slow` for tests that run the model |
| `httpx` | required by FastAPI's `TestClient` (`tests/test_api.py`) |
| `pyfluidsynth` + system `libfluidsynth` | `PrettyMIDI.fluidsynth()` synthesizes scenarios to WAV |
| `pretty-midi` (0.2.11) | builds ground-truth MIDI (`make_piano_midi`). 0.2.11 no longer needs `pkg_resources`, so the old `setuptools<82` constraint was removed |
| `scipy` | WAV writing in `tests/conftest.py` |
| `mir-eval` (0.8) | transcription metrics in `scripts/eval.py` |

Soundfont: `SOUNDFONT_PATH`, then common Linux paths, then pretty_midi's bundled `TimGM6mb.sf2`. `baseline.json` records the soundfont it was measured with, and a different soundfont invalidates the comparison.

## Front-end

| Package | Version | Notes |
|---|---|---|
| React / react-dom | 19.2 | |
| Vite | 8 (declared in `devDependencies`) | |
| Tailwind CSS | 4 | via `@tailwindcss/vite`; no `tailwind.config.js`, no PostCSS config |
| ESLint | 9 (flat config) | `eslint.config.js` |

The API URL comes from `import.meta.env.VITE_API_URL`, defaulting to `http://localhost:8000` (`GenerationSection.jsx`). API errors show the backend's `detail` message.
