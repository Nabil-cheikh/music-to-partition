import sys
import librosa as lr
from basic_pitch import build_icassp_2022_model_path, FilenameSuffix

_suffix = FilenameSuffix.coreml if sys.platform == "darwin" else FilenameSuffix.onnx
ICASSP_2022_MODEL_PATH = build_icassp_2022_model_path(_suffix)
from basic_pitch.inference import predict

VALID_DURATIONS = [4.0, 3.0, 2.0, 1.5, 1.0, 0.75, 0.5, 0.375, 0.25]
MIN_QUARTER_LENGTH = 0.25
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

def _filter_harmonics(notes: list) -> list:
    """Remove likely harmonic overtones: left-hand notes that are weaker than
    right-hand notes at the same time are likely resonance artifacts."""
    import re
    from collections import defaultdict

    by_time = defaultdict(list)
    for n in notes:
        by_time[n["time"]].append(n)

    result = []
    for _, group in by_time.items():
        rh = [n for n in group if int(re.search(r'(\d+)$', n["note"]).group(1)) >= 4]
        lh = [n for n in group if int(re.search(r'(\d+)$', n["note"]).group(1)) < 4]

        result.extend(rh)
        if rh:
            # Keep left-hand notes only if they're stronger than the
            # average right-hand velocity (filters out harmonic artifacts)
            rh_avg_vel = sum(n["velocity"] for n in rh) / len(rh)
            result.extend(n for n in lh if n["velocity"] > rh_avg_vel)
        else:
            result.extend(lh)
    return result


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

    _, _, note_events = predict(file_path, ICASSP_2022_MODEL_PATH)

    # Filter and sort note events by start time
    filtered_events = [
        (start, end, pitch_midi, amplitude)
        for start, end, pitch_midi, amplitude, _ in note_events
        if (end - start) >= min_note_duration and amplitude >= MIN_VELOCITY_THRESHOLD
    ]
    filtered_events.sort(key=lambda e: e[0])

    # Split into right hand (octave >= 4) and left hand for IOI computation
    right_hand_events = [e for e in filtered_events if lr.midi_to_note(e[2])[-1] >= '4']
    left_hand_events = [e for e in filtered_events if lr.midi_to_note(e[2])[-1] < '4']

    def _compute_ioi_durations(events):
        """Use inter-onset interval to correct durations per voice."""
        results = []
        for i, (start, end, pitch_midi, amplitude) in enumerate(events):
            raw_duration_sec = end - start
            # Find next note in same hand that starts strictly after this one
            next_start = None
            for j in range(i + 1, len(events)):
                if events[j][0] > start + 0.05:
                    next_start = events[j][0]
                    break
            if next_start is not None:
                ioi_sec = next_start - start
                if raw_duration_sec < ioi_sec <= raw_duration_sec * 2.5:
                    duration_sec = ioi_sec
                else:
                    duration_sec = raw_duration_sec
            else:
                duration_sec = raw_duration_sec
            results.append((start, duration_sec, pitch_midi, amplitude))
        return results

    corrected_events = _compute_ioi_durations(right_hand_events) + \
                       _compute_ioi_durations(left_hand_events)

    notes_list = []
    for start, duration_sec, pitch_midi, amplitude in corrected_events:
        raw_quarter_length = _seconds_to_quarter_length(duration_sec, bpm)
        aligned_start = max(0, start - offset)
        raw_offset = _seconds_to_quarter_length(aligned_start, bpm)
        notes_list.append({
            "time": _quantize_time(raw_offset, 0.5),
            "note": lr.midi_to_note(pitch_midi),
            "duration": _quantize_to_nearest(raw_quarter_length, VALID_DURATIONS),
            "velocity": float(amplitude)
        })

    notes_list = [n for n in notes_list if n["duration"] >= MIN_QUARTER_LENGTH]
    notes_list = _deduplicate_notes(notes_list)
    notes_list = _filter_harmonics(notes_list)
    notes_list.sort(key=lambda n: (n["time"], n["note"]))

    return {
        "bpm": bpm,
        "offset": float(offset),
        "notes": notes_list,
        "sample_rate": int(sr)
    }
