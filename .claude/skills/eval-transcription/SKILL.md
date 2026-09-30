---
name: eval-transcription
description: Measure transcription quality on the synthesized scenarios and compare to the previous state or baseline. Use after any change to core/processing.py, the transcription model or its parameters, audio loading, BPM detection, or transcription dependencies, and when the user asks "is it better?", "did it regress?", or wants scores.
---

# Evaluate transcription

Context: `docs/testing.md` and `docs/adr/0004-eval-driven-development.md`. Model inference is slow (minutes), so tell the user before starting.

## Run the evaluation

```bash
cd back-end
uv run python scripts/eval.py --compare baseline.json            # table + deltas, exit 1 on regression
uv run python scripts/eval.py --only <scenario> [<scenario> ...]  # quick subset while iterating
uv run python scripts/eval.py --backend pop2piano                 # another backend (if installed)
```

The table columns:

| Column | Layer | Meaning |
|---|---|---|
| `onset` | transcription | onset F1 (pitch correct, onset within ±50 ms) |
| `on+off` | transcription | onset+offset F1 |
| `score` | notation | pitch + position in quarter lengths exact after quantization |
| `dur` | notation | share of well-placed notes that also have the right duration |
| `bpm` | notation | detected tempo |

Report the table as-is, plus the list of regressions the script prints. Say which layer moved: a change in `onset` is the model, a change in `score` or `dur` with the same `onset` is notation.

The pytest equivalent is `uv run pytest tests/test_transcription_eval.py`: one test per scenario, which fails if any metric drops below `baseline.json - tolerance`.

`tests/test_transcription.py` holds the legacy pass/fail tests, kept until the user decides to remove them. Run it too if asked. It contains a skip-on-failure and a tautology (see `docs/testing.md` forbidden patterns), so list its skipped tests separately.

## Running it without hitting the tool timeout

A foreground shell command is killed after at most 10 minutes. Measured on 2026-09-27 (CPU, models cached): **`scripts/eval.py` with Transkun ≈ 2 min for 11 scenarios**; the legacy suite with Pop2Piano ≈ 21 s. **Run full evaluations in the background** (`run_in_background: true`), redirecting output to a log in the scratchpad or `/tmp`. Then wait for the completion notification and read the log. When a run completes, note its duration in the report, and update this paragraph if it changes a lot.

## Troubleshooting

**Golden rule: an environment failure is not a result.** If the run fails for any reason below, stop. Report "evaluation could not run: <cause>" with the exact error, and **never** conclude "no regression" or "tests pass". Fix only environment problems yourself (env vars, cache, background run). Ask the user before installing system packages (`sudo`), changing dependencies, or touching the Python pin.

| Symptom (exact text when known) | Cause | Diagnose | Fix |
|---|---|---|---|
| `ImportError: fluidsynth() was called but pyfluidsynth is not installed` | **Misleading.** Usually `pyfluidsynth` *is* installed, but the system library `libfluidsynth` is missing, so its import failed silently inside pretty_midi. | `uv run python -c "import fluidsynth"`, which shows the real error: `Couldn't find the FluidSynth library.` | Ask the user to install it: `sudo apt install libfluidsynth3` (Debian/Ubuntu), `sudo dnf install fluidsynth-libs` (Fedora), `brew install fluid-synth` (macOS). |
| `ModuleNotFoundError: fluidsynth` / `pytest` | dev group not installed | `uv run python -c "import fluidsynth, pytest"` | `uv sync` (the dev group is included by default) |
| Tests reported as **skipped** with `Aucune soundfont trouvée` | no soundfont found (rare: pretty_midi ships `TimGM6mb.sf2`) | `uv run python -c "from tests.conftest import SOUNDFONT_PATH; print(SOUNDFONT_PATH)"` | Set `SOUNDFONT_PATH=/path/to/file.sf2`, or ask the user to install `fluid-soundfont-gm`. Use the same one for before and after. |
| `ModuleNotFoundError: transformers` with `--backend pop2piano` | Pop2Piano dependencies are no longer installed (ADR-0005) | — | Pop2Piano is only needed to reproduce old numbers. Ask the user before re-adding its dependencies. |
| `FileNotFoundError` on `transkun/pretrained/2.0.pt` | broken transkun install (the checkpoint ships in the wheel) | `ls .venv/lib/python3.12/site-packages/transkun/pretrained` | `uv sync --reinstall-package transkun` |
| `test_baseline_matches_environment` fails | soundfont differs from the one baseline.json was measured with | `uv run python -c "from tests.conftest import SOUNDFONT_PATH; print(SOUNDFONT_PATH)"` | Use the same soundfont (`SOUNDFONT_PATH`). Never "fix" this by editing the baseline without user approval. |
| `RuntimeError: LilyPond introuvable…` | only affects notation / PDF, not the transcription eval | `which lilypond`, `echo $LILYPOND_PATH` | Ask the user to install LilyPond (see CLAUDE.md), or set `LILYPOND_PATH`. |
| `audioread.exceptions.NoBackendError` or decode errors on .aac/.m4a | no ffmpeg | `which ffmpeg` | Ask the user to install ffmpeg. Scenarios use WAV, so this only affects real audio files. |
| Process killed, `Killed`, or very slow with high RAM | out of memory (torch + model) | `free -h` | Close other heavy processes, or run a single class with `-k <Name>` and report partial coverage explicitly. |
| Command cut off by the 10-min tool timeout | foreground run | — | Re-run in the background (see above). Do not shorten the suite to fit. |
| `git stash pop` conflict while measuring the "before" state | working tree had other changes | `git stash list`, `git status` | Stop and tell the user. Never drop the stash. Next time, measure "before" only on a clean tree, or use a worktree: `git worktree add ../mtp-before HEAD`. |
| Results change between two runs of unchanged code | model / synthesis noise | run the same evaluation twice and diff the JSON outputs (`--write`) | Report the spread. The baseline's `tolerance` must stay above it; don't treat noise as a regression or an improvement. |

If the symptom is not in this table, report the full traceback and your diagnosis to the user. Once solved, add a row here in the same change.

## Rules

- **Never update `baseline.json`** (or loosen any threshold) to make results look good. If the user explicitly asks to accept new scores, update the baseline in a separate commit whose message states the old and new scores.
- Keep the same soundfont and environment for before and after. If `SOUNDFONT_PATH` differs between runs, say that the comparison is invalid.
- Report numbers, not impressions. "Chords improved" has to come with the scores.
