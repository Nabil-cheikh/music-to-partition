# Orchestration : audio -> transcription (backend) -> tempo -> quantification.
import librosa as lr
import numpy as np

from core.quantization import TempoMap, choose_bpm, clean_notes, quantize_notes
from core.transcription import RawNote, get_backend

ENVELOPE_SR, ENVELOPE_HOP = 22050, 256
TEMPO_TOLERANCE = 0.02  # écart relatif pour réutiliser les beats d'un tracker


def _onset_envelope(notes: list[RawNote]) -> np.ndarray:
    """Enveloppe d'onsets synthétique construite à partir des notes transcrites."""
    frames = int((max(n.onset for n in notes) + 2) * ENVELOPE_SR / ENVELOPE_HOP)
    env = np.zeros(frames)
    for n in notes:
        env[int(round(n.onset * ENVELOPE_SR / ENVELOPE_HOP))] += n.velocity
    return np.convolve(env, np.hanning(5), mode="same")


def _track(**kwargs) -> tuple[float, np.ndarray]:
    tempo, frames = lr.beat.beat_track(**kwargs)
    sr, hop = kwargs.get("sr", 22050), kwargs.get("hop_length", 512)
    return float(np.atleast_1d(tempo)[0]), lr.frames_to_time(frames, sr=sr, hop_length=hop)


def estimate_tempo(file_path: str, notes: list[RawNote]) -> tuple[TempoMap, int]:
    """Tempo à partir de deux beat trackers (audio, onsets transcrits) ; le candidat retenu
    est celui qui aligne le mieux les onsets (voir core.quantization.choose_bpm).
    Le premier onset est ancré sur un temps. Retourne aussi le sample rate natif."""
    y, sr = lr.load(file_path, sr=None)
    trackers = [_track(y=y, sr=sr)]
    if len(notes) >= 2:
        trackers.append(_track(onset_envelope=_onset_envelope(notes), sr=ENVELOPE_SR, hop_length=ENVELOPE_HOP))

    # mêmes notes que la quantification : un fantôme supprimé ne doit pas servir d'ancre
    onsets = sorted({round(n.onset, 3) for n in clean_notes(notes)})
    first = onsets[0] if onsets else None
    bpm = choose_bpm(onsets, [t for t, _ in trackers])
    if bpm is None:
        return TempoMap(trackers[0][1], fallback_bpm=trackers[0][0] or 120.0, anchor=first), int(sr)
    for tracker_bpm, beat_times in trackers:
        if abs(tracker_bpm / bpm - 1) < TEMPO_TOLERANCE and len(beat_times) >= 2:
            return TempoMap(beat_times, fallback_bpm=bpm, anchor=first), int(sr)
    return TempoMap.steady(bpm, anchor=first), int(sr)


def transcribe_raw(file_path: str, backend: str | None = None) -> list[RawNote]:
    """Couche transcription seule : notes en secondes, non quantifiées."""
    return get_backend(backend).transcribe(file_path)


def recognize_notes_structured(file_path: str, backend: str | None = None) -> dict:
    """Analyse un fichier audio et retourne les notes quantifiées (RecognizeNotesResponse).

    Returns:
        dict: {
            'bpm': int,
            'offset': float,   # secondes : position du temps 0 de la partition
            'notes': list of dicts with time, note, duration, velocity (en noires)
            'sample_rate': int
        }
    """
    raw = transcribe_raw(file_path, backend)
    tempo, sr = estimate_tempo(file_path, raw)
    notes = quantize_notes(raw, tempo)
    return {
        "bpm": int(round(tempo.bpm)),
        "offset": float(min((n.onset for n in raw), default=0.0)),
        "notes": notes,
        "sample_rate": sr,
    }
