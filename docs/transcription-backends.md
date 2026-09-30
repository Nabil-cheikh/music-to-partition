# Transcription backends: review and cost estimate

Review date: 2026-09-27. The sources are the authors' papers, READMEs and PyPI pages, linked at the bottom. **Decision: Transkun V2 is the default backend ([ADR-0005](adr/0005-transkun-replaces-pop2piano.md)).** Our own measurements are in [Measured results](#measured-results-on-our-scenarios).

## History

| Period | Backend | Why it changed |
|---|---|---|
| Until commit `e400030` | Spotify **basic-pitch** | Replaced after poor results on complex pieces |
| `e400030` → 2026-09-27 | **Pop2Piano** (via `transformers`) | Suggested by an AI assistant. It is *not* a transcription model (see below). The commit message says "mt3", but the code uses Pop2Piano. |
| Since 2026-09-27 | **Transkun V2** | Best published piano scores, confirmed on our scenarios (ADR-0005) |

## How to read the scores

The published numbers are note-level F1 on **MAESTRO**, real recordings from Yamaha Disklavier pianos, computed with `mir_eval`:
- **Onset F1**: correct pitch, and the onset within ±50 ms.
- **Onset+offset F1**: also requires the offset within 20 % of the note duration (min 50 ms). **This is what determines note durations on the score.** Our main complaint (wrong rhythms and durations) lives here.

## Comparison

| Backend | Task | Onset F1 | Onset+offset F1 | Size / runtime | License | Maintenance | Effect on this repo |
|---|---|---|---|---|---|---|---|
| **Pop2Piano** (current) | **Pop song → piano cover** (generation) | not published: not a transcription model | — | T5, 6+6 layers, torch + transformers + essentia | MIT | available in `transformers` | heaviest stack; essentia blocks native Windows |
| **basic-pitch** (previous) | Instrument-agnostic, polyphonic | **70.9 %** (paper, "Fno" on MAESTRO; the piano-specific Onsets & Frames baseline gets 95.2 %) | **10.5 %** (O&F: 36.4 % in the same table) | ~17 k parameters; TFLite / ONNX / CoreML; very light | Apache-2.0 | 0.4.0, Aug 2024; **officially Python 3.7–3.11** | conflicts with our `>=3.12,<3.13` pin |
| **ByteDance** `piano_transcription_inference` | Solo piano, with pedal | **96.72 %** | **82.47 %** (80.92 % with velocity); pedal onset F1 91.86 % | torch, CPU or CUDA, 16 kHz input, checkpoint downloaded from Zenodo on first run | MIT (package) / Apache-2.0 (repo) | **repo archived Dec 2025**; package 0.0.6 (Jan 2025) | light; removes essentia |
| **Transkun V2** (ISMIR 2024) | Solo piano | **98.4 %** | **93.1 %** (velocity F1 92.6 %) | torch; **checkpoint bundled** in the 50.8 MB wheel; CPU by default; CLI `transkun in.mp3 out.mid` and Python API | MIT | active; 2.0.1 (Sep 2024) | light; removes essentia |
| **MT3** / YourMT3+ | Multi-instrument | 88–97 % depending on variant | lower than piano-specific models | T5X / JAX, mainly run through Colab; heavy | Apache-2.0 | research code | heavy; only worth it for multi-instrument input |
| **aria-amt** (EleutherAI) | Solo piano, seq2seq | no metric in README | — | Python 3.11, clone + Hugging Face weights, GPU-oriented | Apache-2.0 | small project | not recommended now |

Comparability caveats:
- ByteDance reports on MAESTRO v2 and Transkun on v3. The splits are close but not identical.
- MAESTRO is clean, real, solo piano. On FluidSynth-synthesized audio (our tests) or on phone recordings, every model will score differently. **Only our own evaluation decides.**
- The ByteDance paper's error analysis cites octave errors (harmonics detected as notes) and very short false positives. The notation layer can filter these.

## Measured results on our scenarios

`scripts/eval.py`, 11 scenarios (`tests/scenarios.py`), FluidSynth + `TimGM6mb.sf2`, CPU, 2026-09-27. Metric definitions are in [testing.md](testing.md#the-metrics).

| Pipeline | onset | on+off | score | dur | runtime (11 scenarios) |
|---|---|---|---|---|---|
| Old app: Pop2Piano + old notation (commit `30416fa`) | — | — | 0.407 | 0.241 | — |
| Pop2Piano + new notation | 0.407 | 0.157 | 0.403 | 0.315 | ~16 s |
| **Transkun V2 + new notation** (baseline) | **0.985** | **0.705** | **0.905** | **0.821** | ~110 s |

What the numbers say:
- **Transkun's onsets are near perfect** on synthetic audio: onset F1 = 1.0 on 8 of 11 scenarios, ≥ 0.93 on the other 3.
- **Its offsets are short on this soundfont**: a 1 s note is detected as ~0.58 s. That explains `on+off` ≈ 0.7 against 0.93 published on real pianos.
- **Pop2Piano adds notes that are not in the audio**: 62 detected for 24 expected on `mixed_durations_same_pitch`.
- ByteDance and basic-pitch were not benchmarked: Transkun already clears the bar. ByteDance stays the fallback if Transkun breaks, e.g. on a future Python version.

## Recommendation (as reviewed before the benchmark)

1. **The app's scope is piano audio.** For that, use **Transkun V2 as the primary candidate and ByteDance as the fallback.** Both are purpose-built for piano transcription and report 11–13 points higher onset+offset F1 than the previous piano-specific baseline (Onsets & Frames, 79.7–80.5 %).
2. **Keep Pop2Piano only for a separate product feature**: "upload a pop song, get a piano *arrangement*". In that case the tests must not expect a faithful transcription.
3. **basic-pitch is not a good return option.** Its piano onset+offset score is very low, and it does not officially support Python 3.12.
4. **A better model will not fix rhythm notation by itself.** Duration and rhythm errors also come from the notation layer:
   - one global BPM;
   - a fixed 0.5 grid;
   - chords forced to the longest duration;
   - no voices.
   See [architecture.md#known-limitations](architecture.md#known-limitations). PM2S (MIT, ISMIR 2022, "performance MIDI-to-score by neural beat tracking") targets exactly this. It is research code pinned to Python 3.8 / torch 1.12, so integrating it is risky.

Before switching, record the decision in an ADR that supersedes [ADR-0001](adr/0001-pop2piano-for-transcription.md), with our own benchmark numbers.

## Cost estimate

For one developer working with Claude. These are engineering days, not calendar time. Every candidate is open source and runs locally on CPU, so there are **no license or API fees**.

| Step | Effort | Runtime / infra cost | Notes |
|---|---|---|---|
| 1. Evaluation script (`scripts/eval.py`, `mir_eval`, `baseline.json`, scenarios extracted from the current tests) | 1–1.5 d | none | **Prerequisite.** Without it, choosing a backend is guesswork. |
| 2. `TranscriptionBackend` interface; Pop2Piano moved behind it; transcription outputs seconds | 0.5 d | none | Lets you swap backends without touching notation. |
| 3. Transkun spike: install on Python 3.12, adapter, run the eval | 0.5–1 d | CPU is fine for dev, GPU optional | Go/no-go on our own numbers. Python 3.12 compatibility of its dependencies is **unverified**. |
| 4. ByteDance spike (only if 3 fails) | 0.5 d | same | Archived repo: pin the version and vendor it if needed. |
| 5. Remove Pop2Piano dependencies (`essentia`, `transformers`, `resampy`, `pretty-midi` pin), update docs and ADR | 0.5 d | smaller install, faster startup, **native Windows possible** | |
| **Subtotal: validated backend switch (1–5)** | **~3–4 d** | **0 €** | |
| 6. Notation: beat-aware quantization / tempo map, adaptive grid (triplets, 16ths), voices per hand, per-note durations in chords | 2–5 d | none to low | This is where "complex rhythms" are won or lost. Strict TDD, no model involved. |
| 7. (Optional) PM2S integration | 2–4 d, high risk | CPU | Old dependency pins; consider only if step 6 plateaus. |

Inference time on long pieces has **not been measured**. Measure it on the target machine with the eval script before deciding whether a GPU server is needed. That would be the only recurring cost.

## Sources

- Pop2Piano: [Hugging Face docs](https://huggingface.co/docs/transformers/model_doc/pop2piano), [paper (arXiv:2211.00895)](https://arxiv.org/abs/2211.00895)
- basic-pitch: [GitHub](https://github.com/spotify/basic-pitch), [PyPI](https://pypi.org/project/basic-pitch/), [paper (arXiv:2203.09893)](https://arxiv.org/abs/2203.09893), Tables 2–3
- ByteDance: [GitHub (archived)](https://github.com/bytedance/piano_transcription), [PyPI](https://pypi.org/project/piano-transcription-inference/), [paper (arXiv:2010.01815)](https://arxiv.org/abs/2010.01815), Tables I and VI
- Transkun: [GitHub](https://github.com/Yujia-Yan/Transkun), [PyPI](https://pypi.org/project/transkun/)
- MT3: [GitHub](https://github.com/magenta/mt3); YourMT3+: [arXiv:2407.04822](https://arxiv.org/abs/2407.04822)
- aria-amt: [GitHub](https://github.com/EleutherAI/aria-amt)
- hFT-Transformer comparison table: [arXiv:2307.04305](https://arxiv.org/html/2307.04305)
- PM2S: [GitHub](https://github.com/cheriell/PM2S)
