import librosa as lr
from basic_pitch.inference import predict

VALID_DURATIONS = [4.0, 3.0, 2.0, 1.5, 1.0, 0.75, 0.5, 0.375, 0.25, 0.125, 0.0625]
MIN_VELOCITY_THRESHOLD = 0.4

def _quantize_to_nearest(value: float, grid: list) -> float:
    """Arrondit une durée à la valeur musicale la plus proche"""
    if value <= 0:
        return grid[-1]

    return min(grid, key=lambda d: abs(d - value))

def _quantize_time(raw_time: float, grid_resolution: float = 0.5) -> float:
    """
    Quantifie le temps sur une grille musicale.
    grid_resolution = 0.5 pour des croches, 0.25 pour des doubles croches
    """
    return round(raw_time / grid_resolution) * grid_resolution

def _seconds_to_quarter_length(seconds: float, bpm: int) -> float:
    return seconds * (bpm / 60)

def _deduplicate_notes(notes: list) -> list:
    """
    Supprime les doublons : si plusieurs notes ont le même time et pitch,
    on garde celle avec la plus haute vélocité.
    """
    best_notes = {}
    for n in notes:
        key = (n["time"], n["note"])
        if key not in best_notes or n["velocity"] > best_notes[key]["velocity"]:
            best_notes[key] = n
    return list(best_notes.values())


def recognize_notes_structured(
    file_path: str,
    min_note_duration: float = 0.05,
):
    """Analyze audio file and return structured note data with BPM.

    Returns:
        dict: {
            'bpm': int,
            'offset': float,
            'notes': list of dicts with frame, time, note, and duration
            'frame_duration': duration of each frame in seconds
        }
    """
    y, sr = lr.load(file_path, sr=None)
    tempo, beat_frames = lr.beat.beat_track(y=y, sr=sr)
    bpm = int(tempo)
    offset = lr.frames_to_time(beat_frames[0], sr=sr) if len(beat_frames) > 0 else 0.0

    _, _, note_events = predict(file_path)

    notes_list = []
    for start, end, pitch_midi, amplitude, _ in note_events:
        duration_sec = end - start
        if duration_sec >= min_note_duration and amplitude >= MIN_VELOCITY_THRESHOLD:
            raw_quarter_length = _seconds_to_quarter_length(duration_sec, bpm)
            aligned_start = max(0, start-offset)
            raw_offset = _seconds_to_quarter_length(aligned_start, bpm)
            notes_list.append({
                "time": _quantize_time(raw_offset, 0.5),
                "note": lr.midi_to_note(pitch_midi),
                "duration": _quantize_to_nearest(raw_quarter_length, VALID_DURATIONS),
                "velocity": float(amplitude)
            })

    notes_list = _deduplicate_notes(notes_list)
    notes_list.sort(key=lambda n: (n["time"], n["note"]))

    return {
        "bpm": bpm,
        "offset": float(offset),
        "notes": notes_list,
        "sample_rate": int(sr)
    }
