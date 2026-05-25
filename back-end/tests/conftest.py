import os
import tempfile
import numpy as np
import pretty_midi
import pytest
from scipy.io import wavfile

_SOUNDFONT_CANDIDATES = [
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/sounds/sf2/TimGM6mb.sf2",
    "/usr/share/sounds/sf2/default-GM.sf2",
    os.path.join(os.path.dirname(pretty_midi.__file__), "TimGM6mb.sf2"),
]
SOUNDFONT_PATH = next(p for p in _SOUNDFONT_CANDIDATES if os.path.exists(p))
SAMPLE_RATE = 44100


def synthesize_to_wav(midi_obj: pretty_midi.PrettyMIDI) -> str:
    """Synthesize a PrettyMIDI object to a temporary WAV file via FluidSynth.

    Returns the path to the WAV file (caller is responsible for cleanup).
    """
    audio = midi_obj.fluidsynth(fs=SAMPLE_RATE, sf2_path=SOUNDFONT_PATH)
    # Normalize to prevent clipping
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wavfile.write(path, SAMPLE_RATE, (audio * 32767).astype(np.int16))
    return path


def make_piano_midi(notes: list[tuple], bpm: int = 120) -> pretty_midi.PrettyMIDI:
    """Create a PrettyMIDI object with piano notes.

    Args:
        notes: list of (pitch_midi, start_sec, end_sec, velocity) tuples
        bpm: tempo in BPM
    """
    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    piano = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano")
    )
    for pitch, start, end, velocity in notes:
        piano.notes.append(pretty_midi.Note(
            velocity=velocity, pitch=pitch, start=start, end=end
        ))
    midi.instruments.append(piano)
    return midi


@pytest.fixture
def generate_audio():
    """Fixture that returns a function to generate audio from note specs.

    Usage in tests:
        wav_path = generate_audio(notes, bpm=120)
    """
    paths = []

    def _generate(notes: list[tuple], bpm: int = 120) -> str:
        midi = make_piano_midi(notes, bpm)
        path = synthesize_to_wav(midi)
        paths.append(path)
        return path

    yield _generate

    for p in paths:
        if os.path.exists(p):
            os.remove(p)


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

def find_notes_at_time(notes: list[dict], target_time: float, tolerance: float = 1.0) -> list[dict]:
    """Return all detected notes whose time is within tolerance of target_time."""
    return [n for n in notes if abs(n["time"] - target_time) <= tolerance]


def assert_note_present(
    notes: list[dict],
    expected_pitch: str,
    expected_time: float,
    time_tolerance: float = 1.5,
    pitch_tolerance: int = 1,
):
    """Assert that a note with the expected pitch exists near the expected time.

    pitch_tolerance: allowed semitone difference (0 = exact, 1 = +-1 semitone).
    """
    import librosa
    expected_midi = librosa.note_to_midi(expected_pitch)
    for n in notes:
        if abs(n["time"] - expected_time) > time_tolerance:
            continue
        detected_midi = librosa.note_to_midi(n["note"])
        if abs(detected_midi - expected_midi) <= pitch_tolerance:
            return n
    nearby = find_notes_at_time(notes, expected_time, time_tolerance)
    nearby_str = [f"{n['note']}@t={n['time']}" for n in nearby]
    raise AssertionError(
        f"Note {expected_pitch} not found near time {expected_time} "
        f"(tolerance: time={time_tolerance}, pitch={pitch_tolerance} semitones). "
        f"Nearby notes: {nearby_str}"
    )


def assert_chord_present(
    notes: list[dict],
    expected_pitches: list[str],
    expected_time: float,
    time_tolerance: float = 1.5,
    pitch_tolerance: int = 1,
):
    """Assert that all pitches of a chord appear at roughly the same time."""
    found = []
    for pitch in expected_pitches:
        n = assert_note_present(notes, pitch, expected_time, time_tolerance, pitch_tolerance)
        found.append(n)
    # All chord notes should share the same quantized time
    times = [n["time"] for n in found]
    assert max(times) - min(times) <= 1.0, (
        f"Chord notes should be simultaneous but times spread: {times}"
    )


VALID_DURATIONS = [4.0, 3.0, 2.0, 1.5, 1.0, 0.5, 0.25]


def assert_duration_near(
    note: dict,
    expected_duration: float,
    tolerance_steps: int = 1,
):
    """Assert that a note's duration is within tolerance_steps of the expected
    duration in the VALID_DURATIONS grid.

    tolerance_steps=1 means the detected duration can be one step away
    (e.g., expected 1.0 accepts 0.5 or 1.5).
    """
    idx = VALID_DURATIONS.index(expected_duration)
    lo = max(0, idx - tolerance_steps)
    hi = min(len(VALID_DURATIONS) - 1, idx + tolerance_steps)
    allowed = set(VALID_DURATIONS[lo:hi + 1])
    assert note["duration"] in allowed, (
        f"Note {note['note']}@t={note['time']} has duration {note['duration']}, "
        f"expected ~{expected_duration} (allowed: {sorted(allowed, reverse=True)})"
    )
