# ADR-0006: notation redesign (tempo selection, adaptive grid, voices)

- **Status**: accepted
- **Date**: 2026-09-27
- **Deciders**: project owner
- **Supersedes**: [ADR-0003](0003-quarter-length-quantization.md)

## Context
Even with a faithful transcription, the old notation layer lost information:
- one global librosa BPM, which was often wrong: 39.5 instead of 120, 66 instead of 100, 72.8 instead of 110 on our scenarios;
- a fixed 0.5 grid, so no sixteenths or triplets;
- chords forced to their longest note;
- no voices, and a fixed octave-4 hand split.

## Decision
1. **Tempo** (`estimate_tempo`, `choose_bpm`): run librosa beat tracking on the audio *and* on an onset envelope built from the transcribed notes. Try each tempo × (½, ⅔, 1, 3/2, 2) and keep the one on which the onsets fall most cleanly (grid error plus an off-beat penalty). The first onset is anchored on beat 0. Rubato is followed when a tracker's beats are irregular (`TempoMap`).
2. **Grid** (`choose_grids`): per beat, a sixteenth or triplet grid, whichever fits best. Notes of ≥ 1 beat end on a half-beat.
3. **Cleaning** (`clean_notes`): drop very short and very quiet notes, and quiet harmonic ghosts (octave, octave+fifth, two octaves).
4. **Hands** (`split_hands`): fixed extremes plus pitch continuity, and a playable-span limit of 14 semitones.
5. **Legato** (`fill_legato_gaps`): fill silences shorter than 50 % of the gap to the next onset in the same hand.
6. **Voices and measures** (`assign_voices`, `build_part`): each note keeps its duration via music21 `Voice`s. Measures are built explicitly, with ties across barlines and writable durations (dotted values, triplets).

## Measured results (Transkun backend, `scripts/eval.py`)
| | score | dur |
|---|---|---|
| Grid + voices + legato, BPM from librosa on audio only | 0.757 | 0.519 |
| + tempo selection | 0.905 | 0.795 |
| + long-note end snapping | 0.905 | **0.821** |

The tempo candidates and cost were chosen on these same scenarios. An extra "prefer the audio tracker's tempo" prior was tried and **rejected**: it did not help, and it would have been tuning on the test set.

## Consequences
- The `NoteSegment` contract is unchanged in shape. `time` and `duration` are now on an adaptive grid (multiples of ¼ or ⅓), and `offset` is the first note's time.
- **Known failure**: `triplets_over_quarters`. Triplet eighths at 90 BPM are also plain eighths at 135 BPM, and the cost prefers the simpler reading (score 0.125). Fixing it needs musical context (e.g. the left hand's regular quarters), not a parameter tweak.
- `wide_chords_both_hands` durations stay at 0.5: chord ends cut early by the model leave gaps larger than the legato threshold. The threshold was not raised, because that would overfit the synthetic soundfont; real pianos have accurate offsets.
- Pickup notes start the first measure (no downbeat detection); 4/4 is still hard-coded.
- Everything here is deterministic and covered by `tests/test_quantization.py` and `tests/test_sheet_generator.py` (TDD).
