import librosa as lr
import numpy as np
import aifc


def recognize_notes(
    file_path: str,
    fmin_hz: float | None = None,
    fmax_hz: float | None = None,
    hop_length: int = 512,
):
    """Estimate fundamental frequency (F0) track using pYIN.

    Returns arrays aligned per frame: times (s), f0 (Hz, NaN when unvoiced),
    voiced_flag (bool), voiced_probs ([0,1]).
    """
    # Preserve the native sampling rate of the file
    y, sr = lr.load(file_path, sr=None)

    # Sensible musical range by default (C2..C7)
    if fmin_hz is None:
        fmin_hz = float(lr.note_to_hz("C2"))
    if fmax_hz is None:
        fmax_hz = float(lr.note_to_hz("C7"))

    f0_hz, voiced_flag, voiced_probs = lr.pyin(
        y,
        fmin=fmin_hz,
        fmax=fmax_hz,
        sr=sr,
        hop_length=hop_length,
    )

    times_s = lr.times_like(f0_hz, sr=sr, hop_length=hop_length)
    return times_s, f0_hz, voiced_flag, voiced_probs, sr


def recognize_notes_structured(
    file_path: str,
    fmin_hz: float | None = None,
    fmax_hz: float | None = None,
    hop_length: int = 512,
    min_voiced_prob: float = 0.5,
):
    """Analyze audio file and return structured note data with BPM.

    Returns:
        dict: {
            'bpm': float,
            'offset': float,
            'notes': list of dicts with frame, time, note, and duration
            'frame_duration': duration of each frame in seconds
        }
    """
    # Load audio
    y, sr = lr.load(file_path, sr=None)

    # Estimate BPM and beat frames
    tempo, beat_frames = lr.beat.beat_track(y=y, sr=sr, hop_length=hop_length)

    # Calculate offset (time of first beat, or 0 if no beats detected)
    if len(beat_frames) > 0:
        offset = lr.frames_to_time(beat_frames[0], sr=sr, hop_length=hop_length)
    else:
        offset = 0.0

    # Sensible musical range by default (C2..C7)
    if fmin_hz is None:
        fmin_hz = float(lr.note_to_hz("C2"))
    if fmax_hz is None:
        fmax_hz = float(lr.note_to_hz("C7"))

    # Extract pitch with pYIN
    f0_hz, voiced_flag, voiced_probs = lr.pyin(
        y,
        fmin=fmin_hz,
        fmax=fmax_hz,
        sr=sr,
        hop_length=hop_length,
    )

    times_s = lr.times_like(f0_hz, sr=sr, hop_length=hop_length)
    frame_duration = hop_length / sr

    # Detect note onsets (attaques de notes)
    onset_frames = lr.onset.onset_detect(
        y=y,
        sr=sr,
        hop_length=hop_length,
        backtrack=True
    )

    # Group consecutive frames with the same note into segments
    notes_list = []
    current_note = None
    current_frame_start = None
    current_time_start = None

    for i, (freq, is_voiced, prob, time) in enumerate(zip(f0_hz, voiced_flag, voiced_probs, times_s)):
        if is_voiced and prob >= min_voiced_prob and not np.isnan(freq):
            note_name = lr.hz_to_note(freq)

            # Start a new note or continue current one
            if current_note != note_name:
                # Save previous note if it exists
                if current_note is not None:
                    duration = time - current_time_start
                    notes_list.append({
                        "frame": int(current_frame_start),
                        "time": float(current_time_start),
                        "note": current_note,
                        "duration": float(duration)
                    })

                # Start new note
                current_note = note_name
                current_frame_start = i
                current_time_start = time
        else:
            # Silence or unvoiced - end current note
            if current_note is not None:
                duration = time - current_time_start
                notes_list.append({
                    "frame": int(current_frame_start),
                    "time": float(current_time_start),
                    "note": current_note,
                    "duration": float(duration)
                })
                current_note = None

    # Don't forget the last note
    if current_note is not None:
        duration = times_s[-1] - current_time_start
        notes_list.append({
            "frame": int(current_frame_start),
            "time": float(current_time_start),
            "note": current_note,
            "duration": float(duration)
        })

    return {
        "bpm": float(tempo),
        "offset": float(offset),
        "notes": notes_list,
        "frame_duration": float(frame_duration),
        "sample_rate": int(sr),
        "hop_length": int(hop_length)
    }
