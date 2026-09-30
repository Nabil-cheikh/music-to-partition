"""Ground-truth scenarios for transcription evaluation (pure data).

Each scenario is a list of (midi_pitch, start_sec, end_sec, velocity) tuples plus its tempo.
Conventions (docs/testing.md): one musical difficulty per scenario, times derived from
beat constants, first note at >= one beat (never at t=0).
"""
from dataclasses import dataclass

# MIDI note numbers
C2, E2, G2 = 36, 40, 43
C3, D3, E3, F3, G3, A3, B3 = 48, 50, 52, 53, 55, 57, 59
C4, D4, E4, F4, G4, A4, B4 = 60, 62, 64, 65, 67, 69, 71
C5, D5, E5, F5, G5 = 72, 74, 76, 77, 79

VEL = 100


@dataclass(frozen=True)
class Scenario:
    description: str
    bpm: int
    notes: tuple  # ((pitch, start_s, end_s, velocity), ...)


def _beats(bpm: int, events) -> tuple:
    """Convert (pitch, start_beat, duration_beats) events to seconds tuples.

    Beat 0 is shifted by one beat so that no note starts at t=0.
    """
    beat = 60 / bpm
    return tuple(
        (pitch, (start + 1) * beat, (start + 1 + dur) * beat, VEL)
        for pitch, start, dur in events
    )


def _scale_with_accompaniment():
    rh = [C4, D4, E4, F4, G4, A4, B4, C5]
    lh = [C3, G3, C3, E3, C3, G3, C3, E3]
    return [(p, i, 1) for i, p in enumerate(rh)] + [(p, i, 1) for i, p in enumerate(lh)]


def _hand_offset():
    rh = [C4, D4, E4, F4, G4, A4, B4, C5]
    lh = [C3, D3, E3, F3, G3, A3, B3]
    return [(p, i, 1) for i, p in enumerate(rh)] + [(p, i + 3, 1) for i, p in enumerate(lh)]


def _mixed_durations_same_pitch():
    events, t = [], 0.0
    for dur, count in [(2, 2), (1, 4), (2, 2), (0.5, 8), (2, 1), (1, 2), (2, 1), (0.5, 4)]:
        for _ in range(count):
            events.append((C4, t, dur))
            t += dur
    return events


def _triplets_over_quarters():
    rh = [C5, D5, E5, D5, C5, G4, A4, B4, C5, E5, D5, C5]
    lh = [C3, G3, E3, G3]
    return [(p, i / 3, 1 / 3) for i, p in enumerate(rh)] + [(p, i, 1) for i, p in enumerate(lh)]


def _sixteenth_run():
    rh = [C4, D4, E4, F4, G4, A4, B4, C5, D5, C5, B4, A4, G4, F4, E4, D4]
    return [(p, i * 0.25, 0.25) for i, p in enumerate(rh)] + [(C3, 0, 2), (G3, 2, 2)]


def _dotted_rhythm():
    # dotted quarter + eighth, twice, then dotted half + quarter
    pattern = [(E4, 0, 1.5), (D4, 1.5, 0.5), (C4, 2, 1.5), (D4, 3.5, 0.5), (E4, 4, 3), (C4, 7, 1)]
    return pattern + [(C3, 0, 4), (G2, 4, 4)]


SCENARIOS: dict[str, Scenario] = {
    # Migrated from the former tests/test_transcription.py (times shifted by one beat)
    "scale_with_accompaniment": Scenario(
        "RH C major scale in quarters over LH quarter accompaniment, simultaneous onsets",
        120, _beats(120, _scale_with_accompaniment())),
    "hand_offset": Scenario(
        "RH scale starts alone, LH scale enters 3 beats later",
        120, _beats(120, _hand_offset())),
    "chord_rh_moving_lh": Scenario(
        "RH C-E-G chord held a half note while LH plays 4 quarters",
        120, _beats(120, [(C4, 0, 2), (E4, 0, 2), (G4, 0, 2),
                          (C2, 0, 1), (E2, 1, 1), (G2, 2, 1), (C2, 3, 1)])),
    "chord_lh_moving_rh": Scenario(
        "LH C-E-G chord held a half note while RH plays 4 quarters",
        120, _beats(120, [(C2, 0, 2), (E2, 0, 2), (G2, 0, 2),
                          (C4, 0, 1), (D4, 1, 1), (E4, 2, 1), (F4, 3, 1)])),
    "mixed_durations_same_pitch": Scenario(
        "Repeated C4 with half, quarter and eighth notes mixed",
        120, _beats(120, _mixed_durations_same_pitch())),

    # New scenarios targeting complex rhythms
    "held_bass_moving_melody": Scenario(
        "LH whole notes held under RH eighth-note melody (different duration per note)",
        100, _beats(100, [(C3, 0, 4), (G2, 4, 4)]
                    + [(p, i * 0.5, 0.5) for i, p in enumerate(
                        [E4, G4, C5, G4, E4, G4, C5, E5, D5, B4, G4, B4, D5, B4, G4, D4])])),
    "chord_with_different_durations": Scenario(
        "Same-onset notes with different lengths: bass whole, tenor half, melody quarters",
        90, _beats(90, [(C3, 0, 4), (G3, 0, 2), (E3, 2, 2)]
                   + [(p, i, 1) for i, p in enumerate([C5, B4, A4, G4])])),
    "triplets_over_quarters": Scenario(
        "RH eighth-note triplets over LH quarter notes",
        90, _beats(90, _triplets_over_quarters())),
    "sixteenth_run": Scenario(
        "RH sixteenth-note run over LH half notes",
        100, _beats(100, _sixteenth_run())),
    "dotted_rhythm": Scenario(
        "Dotted quarter + eighth patterns and a dotted half over LH whole notes",
        110, _beats(110, _dotted_rhythm())),
    "wide_chords_both_hands": Scenario(
        "Four-note chords in both hands, half notes, octave doublings",
        80, _beats(80, [(p, 0, 2) for p in (C2, C3, G3, E3)] + [(p, 0, 2) for p in (C4, E4, G4, C5)]
                   + [(p, 2, 2) for p in (G2, G3, D3, B3)] + [(p, 2, 2) for p in (B4, D5, G4, G5)])),
}
