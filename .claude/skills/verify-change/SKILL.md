---
name: verify-change
description: Definition of Done for this repo. Use before declaring any code change finished, before committing, or when the user asks to "check", "verify", or "make sure nothing broke". Detects which areas changed and runs the matching test suites, lint and build, then reports before → after results.
---

# Verify a change

Read `docs/testing.md#non-regression-protocol` if it is not already in context.

## 1. Find what changed

```bash
git status --short
git diff --name-only HEAD
```

Map each path to an area:

| Path | Area |
|---|---|
| `back-end/core/transcription/` | transcription |
| `back-end/core/processing.py` (tempo estimation, orchestration) | notation + transcription eval |
| `back-end/core/quantization.py`, `back-end/core/sheet_generator.py` | notation (+ transcription eval, since the `score`/`dur` metrics depend on them) |
| `back-end/api/`, `back-end/models/` | api (+ front-end contract if `schemas.py`) |
| `back-end/tests/scenarios.py`, `back-end/scripts/eval.py` | transcription eval (a new scenario has no baseline yet: say so) |
| `back-end/pyproject.toml`, `back-end/uv.lock` | everything back-end |
| `front-end/` | front-end |
| `docs/`, `CLAUDE.md`, `.claude/` only | docs: check that the links and cited names exist, no test run needed |

## 2. Run the matching checks

From `back-end/`:
- fast suites (seconds, always run for any back-end change): `uv run pytest -m "not slow" -q`
  This covers `test_quantization.py`, `test_processing.py`, `test_sheet_generator.py`, `test_api.py` and `test_processing_units.py`.
- the PDF test needs LilyPond. Without it, `TestGeneratePianoSheet` is **skipped**: report it as "not run", never as passing.
- transcription eval: use the `eval-transcription` skill (`scripts/eval.py --compare baseline.json`, ~2 min, run it in the background).

From `front-end/`: `npm run lint && npm run build`

## 3. Compare with the previous state

For the transcription eval, `baseline.json` *is* the previous state.

For the other suites, if one fails and you don't know whether it failed before your change, check the unchanged code in a separate worktree. This leaves the working tree untouched:

```bash
git worktree add --detach ../mtp-before HEAD
# run the same suite from ../mtp-before/back-end
git worktree remove ../mtp-before
```

## 4. Report

Give one line per area, with the before → after counts, e.g.:
- `fast suites: 65/65 → 66/66 ✅ (1 new test)`
- `transcription eval: score 0.87 → 0.90, no regression vs baseline ✅`

## Rules

- Do not call the change done if any check newly fails. Fix it, or explain why to the user and let them decide.
- Never make a check pass by weakening it. See "Forbidden patterns" in `docs/testing.md`.
- If a check could not run (e.g. LilyPond or a soundfont is missing), say so. Do not report it as passing. For environment failures (FluidSynth, model download, timeout, out of memory, stash conflicts), follow the **Troubleshooting** table in `.claude/skills/eval-transcription/SKILL.md`. It also applies to the unit and notation suites.
