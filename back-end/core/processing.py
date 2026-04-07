import librosa as lr
from transformers import Pop2PianoForConditionalGeneration, Pop2PianoProcessor

# Load model and processor once at module level
_model = Pop2PianoForConditionalGeneration.from_pretrained("sweetcocoa/pop2piano")
_processor = Pop2PianoProcessor.from_pretrained("sweetcocoa/pop2piano")

VALID_DURATIONS = [4.0, 3.0, 2.0, 1.5, 1.0, 0.5, 0.25]
MIN_QUARTER_LENGTH = 0.25


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


def recognize_notes_structured(file_path: str):
    """Analyze audio file using Pop2Piano and return structured note data with BPM.

    Returns:
        dict: {
            'bpm': int,
            'offset': float,
            'notes': list of dicts with time, note, duration, and velocity
            'sample_rate': int
        }
    """
    # BPM detection with librosa
    y, sr = lr.load(file_path, sr=None)
    tempo, beat_frames = lr.beat.beat_track(y=y, sr=sr)
    bpm = int(tempo)
    offset = lr.frames_to_time(beat_frames[0], sr=sr) if len(beat_frames) > 0 else 0.0

    # Pop2Piano inference (needs 44100 Hz)
    audio_44k, _ = lr.load(file_path, sr=44100)
    inputs = _processor(audio=audio_44k, sampling_rate=44100, return_tensors="pt")
    model_output = _model.generate(
        input_features=inputs["input_features"],
        composer="composer1",
    )
    decoded = _processor.batch_decode(
        token_ids=model_output,
        feature_extractor_output=inputs,
    )
    midi_obj = decoded["pretty_midi_objects"][0]

    # Extract notes from the MIDI object
    notes_list = []
    for instr in midi_obj.instruments:
        for n in instr.notes:
            duration_sec = n.end - n.start
            aligned_start = max(0, n.start - offset)

            raw_offset = _seconds_to_quarter_length(aligned_start, bpm)
            raw_quarter_length = _seconds_to_quarter_length(duration_sec, bpm)

            notes_list.append({
                "time": _quantize_time(raw_offset, 0.5),
                "note": lr.midi_to_note(n.pitch, unicode=False),
                "duration": _quantize_to_nearest(raw_quarter_length, VALID_DURATIONS),
                "velocity": n.velocity / 127.0,
            })

    notes_list = [n for n in notes_list if n["duration"] >= MIN_QUARTER_LENGTH]
    notes_list = _deduplicate_notes(notes_list)
    notes_list.sort(key=lambda n: (n["time"], n["note"]))

    return {
        "bpm": bpm,
        "offset": float(offset),
        "notes": notes_list,
        "sample_rate": int(sr),
    }
