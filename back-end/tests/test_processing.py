"""Tests for core.processing.estimate_tempo (librosa runs on a short synthetic signal, no model)."""
import numpy as np
import pytest
from scipy.io import wavfile

from core.processing import estimate_tempo
from core.quantization import quantize_notes
from core.transcription import RawNote


@pytest.fixture
def click_track(tmp_path):
    sr, bpm = 22050, 120
    y = np.zeros(int(sr * 6), dtype=np.float32)
    for k in range(10):
        start = int((0.5 + k * 60 / bpm) * sr)
        y[start:start + 200] = 0.8
    path = tmp_path / "clicks.wav"
    wavfile.write(path, sr, y)
    return str(path)


def test_removed_ghost_note_is_not_the_anchor(click_track):
    melody = [RawNote(72, 1.0 + k * 0.5, 1.4 + k * 0.5, 0.8) for k in range(8)]
    ghost = RawNote(84, 0.8, 0.81, 0.8)  # 10 ms: supprimée par clean_notes
    tempo, _ = estimate_tempo(click_track, [ghost] + melody)
    notes = quantize_notes([ghost] + melody, tempo)
    assert notes[0]["time"] == 0
    assert [n["time"] for n in notes] == [0, 1, 2, 3, 4, 5, 6, 7]
