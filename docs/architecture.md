# Architecture

## Pipeline

```
 front-end (React)                         back-end (FastAPI)
 ─────────────────                         ──────────────────────────────────────────────────────────────
 UploadButton ── file ──► POST /api/recognize-notes/ ──► core/processing.py  (orchestration)
                                                          1. core/transcription/: backend (Transkun) → RawNote[] (seconds)
                                                          2. estimate_tempo: 2 beat trackers → best BPM → TempoMap
                                                          3. core/quantization.py: clean, seconds → beats, adaptive grid
                          ◄── RecognizeNotesResponse ────
 GenerationSection ─ JSON ► POST /api/generate-sheet/ ──► core/sheet_generator.py
                                                          4. hands, legato gaps, voices, measures → music21 Score
                                                          5. music21 → LilyPond → PDF (temp dir, .ly removed)
 PdfViewer ◄──────────────── application/pdf ───────────
```

| Layer | Code | Nature | How it is tested |
|---|---|---|---|
| **Transcription** | `core/transcription/` (`TranscriptionBackend`, `RawNote`, `get_backend`) | ML model, slow | `scripts/eval.py`: `onset` / `on+off` metrics against `baseline.json` |
| **Notation** | `estimate_tempo` in `core/processing.py`, `core/quantization.py`, `core/sheet_generator.py` | Deterministic rules | Strict TDD (`test_quantization.py`, `test_sheet_generator.py`) and the eval's `score` / `dur` metrics |

## Transcription layer

```python
@dataclass(frozen=True)
class RawNote:
    pitch: int       # MIDI
    onset: float     # seconds
    offset: float    # seconds
    velocity: float  # 0-1

class TranscriptionBackend(Protocol):
    def transcribe(self, audio_path: str) -> list[RawNote]: ...
```

- `get_backend(name)` loads a backend **lazily and once** (`lru_cache`). The name comes from the argument, then the `TRANSCRIPTION_BACKEND` env var, then `DEFAULT_BACKEND = "transkun"`. Importing `core.*` never loads a model.
- `transkun`: Transkun V2, checkpoint bundled in the pip package, 44.1 kHz mono input, pedal events dropped. See [ADR-0005](adr/0005-transkun-replaces-pop2piano.md).
- `pop2piano`: the previous backend, kept for reproducing old numbers. Its dependencies are in the optional uv group `pop2piano`.
- **Adding a backend**: one module in `core/transcription/`, one branch in `get_backend`, then the `try-transcription-backend` skill.

## Notation layer

### Tempo (`estimate_tempo`, `core/processing.py`)
1. Two beat trackers: librosa on the audio, and librosa on a synthetic onset envelope built from the transcribed notes.
2. `choose_bpm`: the candidates are both tempos × (½, ⅔, 1, 3/2, 2), within `MIN_BPM`–`MAX_BPM` (50–160). The winner minimizes the onsets' grid error plus a penalty for onsets off the beat or half-beat.
3. `TempoMap`: if a tracker found that tempo, its beat times are used, with interpolation between beats when they are irregular (rubato). Otherwise the tempo is constant. **The first onset is anchored on beat 0.**

### Quantization (`core/quantization.py`)
- `clean_notes`: drops notes shorter than 30 ms or with velocity under 0.05. Also drops *harmonic ghosts*: a quiet note an octave, octave+fifth or two octaves above a louder note starting at the same time.
- `choose_grids`: per beat, a **sixteenth** (¼) or **triplet** (⅓) grid, whichever fits the onsets of that beat best. The triplet must at least halve the error, and needs ≥ 2 onsets.
- `quantize_notes`: onsets and offsets are snapped with that grid. A note of ≥ 1 beat ends on a half-beat. The minimum duration is one grid step. Times start at 0; a first note up to `SHIFT_TOLERANCE` (0.1 beat) early still counts as beat 0.

### Score (`core/sheet_generator.py`)
- `split_hands`: fixed extremes (≥ C5 right, < C3 left); otherwise **continuity**, meaning the hand whose recent average pitch is closest. A hand spans at most 14 semitones on one onset; a note moves only if the receiving hand stays playable. If ≤ 10 % of notes are left-hand, everything goes to the right hand.
- `fill_legato_gaps`: a silence shorter than 50 % of the gap to the next onset in the same hand is filled. Models often cut note ends early.
- `assign_voices`: same (time, duration) → one chord. Overlapping chords → separate music21 `Voice`s, so **each note keeps its own duration**.
- `build_part`: measures are built explicitly (4/4). Notes crossing a barline are tied. Durations are split into writable values (dotted, triplets), and a system break is inserted every `MEASURES_PER_LINE`.
- `generate_piano_sheet`: LilyPond is resolved via `LILYPOND_PATH`, then `PATH`. music21's `.ly` source file is deleted after rendering.

## Data contract: `NoteSegment` / `RecognizeNotesResponse`

Defined in `back-end/models/schemas.py`. The front-end passes this JSON back unchanged to `/generate-sheet/`.

| Field | Unit | Meaning |
|---|---|---|
| `bpm` | int | Tempo chosen by `estimate_tempo` |
| `offset` | seconds | Time of the first transcribed note, which is beat 0 of the score |
| `notes[].time` | **quarter lengths** | Start position, on the adaptive grid (multiples of ¼ or ⅓) |
| `notes[].duration` | **quarter lengths** | Snapped duration, before legato filling (that happens in the sheet generator) |
| `notes[].note` | string | Scientific pitch with sharps, e.g. `C#4` |
| `notes[].velocity` | 0–1 | From the model |
| `sample_rate` | Hz | Native sample rate of the upload (informational) |

**Changing this contract is a breaking change** for the front-end, the notation layer and every test. It needs an ADR.

## File lifecycle

- Upload: written to `tempfile.mkstemp(suffix=<ext>)` and deleted in a `finally` after transcription. The client filename is never used as a path.
- PDF: deleted by a `BackgroundTask` after the response is sent. The LilyPond source is deleted right after rendering.
- `back-end/uploads/`: sample audio for manual testing. The API does not write there.

## Known limitations

Measured numbers are in [transcription-backends.md](transcription-backends.md#measured-results-on-our-scenarios).

Tempo:
- **Tempo is ambiguous for triplet-heavy passages.** Eighth-note triplets at 90 BPM are also plain eighths at 135 BPM. `choose_bpm` picks the simpler reading (135), so `triplets_over_quarters` is written with binary rhythms at the wrong tempo.
- Anchoring the first onset on beat 0 means **pickup (anacrusis) notes start the first measure**. There is no downbeat detection.

Transcription:
- On FluidSynth-synthesized audio, Transkun cuts note ends early. That keeps `on+off` around 0.7 (vs 0.93 published on real pianos). Legato filling and long-note end snapping compensate partly.

Score:
- 4/4 is hard-coded; there is no key or time signature detection.
- Pedal events are dropped.
- The only output format is PDF. MusicXML export (`score.write('musicxml')`) is tested but not exposed by the API.
