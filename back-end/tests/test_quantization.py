"""Strict TDD tests for core.quantization (deterministic, no model)."""
import numpy as np
import pytest

from core.quantization import (
    TempoMap,
    choose_grids,
    clean_notes,
    normalize_beats,
    quantize_notes,
    BINARY_GRID,
    TRIPLET_GRID,
)
from core.transcription import RawNote


def steady_beats(bpm: float, n: int = 16, start: float = 0.5) -> np.ndarray:
    return start + np.arange(n) * 60 / bpm


def raw(pitch, onset, offset, velocity=0.8):
    return RawNote(pitch, onset, offset, velocity)


class TestCleanNotes:
    def test_drops_very_short_notes(self):
        assert clean_notes([raw(60, 1.0, 1.01)]) == []

    def test_drops_very_quiet_notes(self):
        assert clean_notes([raw(60, 1.0, 2.0, velocity=0.01)]) == []

    def test_drops_quiet_octave_ghost(self):
        notes = [raw(48, 1.0, 2.0, 0.8), raw(60, 1.01, 1.5, 0.2)]
        assert clean_notes(notes) == [notes[0]]

    def test_keeps_real_octave_of_similar_loudness(self):
        notes = [raw(48, 1.0, 2.0, 0.8), raw(60, 1.0, 2.0, 0.7)]
        assert clean_notes(notes) == notes

    def test_keeps_quiet_note_that_is_not_a_harmonic_interval(self):
        notes = [raw(48, 1.0, 2.0, 0.8), raw(52, 1.0, 2.0, 0.2)]
        assert clean_notes(notes) == notes


class TestNormalizeBeats:
    def test_keeps_tempo_in_range(self):
        beats = steady_beats(100)
        assert np.allclose(normalize_beats(beats), beats)

    def test_halves_too_fast_tempo(self):
        beats = normalize_beats(steady_beats(240, n=32))
        assert 60 / np.median(np.diff(beats)) == pytest.approx(120)

    def test_doubles_too_slow_tempo(self):
        beats = normalize_beats(steady_beats(40))
        assert 60 / np.median(np.diff(beats)) == pytest.approx(80)


class TestTempoMap:
    def test_steady_tempo_is_linear(self):
        tm = TempoMap(steady_beats(120))
        assert tm.bpm == pytest.approx(120)
        assert tm.to_beats(0.5) == pytest.approx(0)
        assert tm.to_beats(1.75) == pytest.approx(2.5)

    def test_extrapolates_before_first_beat(self):
        tm = TempoMap(steady_beats(120, start=1.0))
        assert tm.to_beats(0.5) == pytest.approx(-1)

    def test_rubato_follows_beats(self):
        # beats qui ralentissent : 0.5 s puis 0.8 s d'écart
        beats = np.array([0.0, 0.5, 1.0, 1.5, 2.3, 3.1, 3.9])
        tm = TempoMap(beats)
        assert tm.to_beats(2.3) == pytest.approx(4)
        assert tm.to_beats(2.7) == pytest.approx(4.5)

    def test_fallback_when_no_beats(self):
        tm = TempoMap([], fallback_bpm=90)
        assert tm.bpm == 90
        assert tm.to_beats(2.0) == pytest.approx(3.0)


class TestChooseGrids:
    def test_binary_positions_use_binary_grid(self):
        assert choose_grids([0.0, 0.5, 0.75]) == {0: BINARY_GRID}

    def test_triplet_positions_use_triplet_grid(self):
        assert choose_grids([1.0, 1.333, 1.667]) == {1: TRIPLET_GRID}

    def test_single_position_never_triplet(self):
        assert choose_grids([2.34]) == {2: BINARY_GRID}

    def test_grid_is_chosen_per_beat(self):
        grids = choose_grids([0.0, 0.5, 1.0, 1.333, 1.667])
        assert grids == {0: BINARY_GRID, 1: TRIPLET_GRID}


class TestQuantizeNotes:
    TEMPO = TempoMap(steady_beats(120))  # beat 0 = 0.5 s, 0.5 s par temps

    def test_first_note_starts_at_zero(self):
        notes = quantize_notes([raw(60, 2.5, 3.0)], self.TEMPO)
        assert notes[0]["time"] == 0

    def test_first_note_slightly_before_beat_starts_at_zero(self):
        # cas réel : onset 0.2117 s, ancre arrondie à 0.212 s -> -0.0006 temps
        tempo = TempoMap.steady(120, anchor=0.212)
        notes = quantize_notes([raw(72, 0.2117, 0.5), raw(72, 0.7117, 1.0)], tempo)
        assert [n["time"] for n in notes] == [0, 1]

    def test_positions_and_durations_in_quarter_lengths(self):
        notes = quantize_notes([raw(60, 0.5, 1.5), raw(62, 1.5, 1.75)], self.TEMPO)
        assert [(n["note"], n["time"], n["duration"]) for n in notes] == [("C4", 0, 2), ("D4", 2, 0.5)]

    def test_small_timing_errors_are_snapped(self):
        notes = quantize_notes([raw(60, 0.52, 0.98), raw(62, 1.01, 1.49)], self.TEMPO)
        assert [(n["time"], n["duration"]) for n in notes] == [(0, 1), (1, 1)]

    def test_triplets_are_kept(self):
        third = 0.5 / 3
        notes = quantize_notes([raw(60 + i, 0.5 + i * third, 0.5 + (i + 1) * third) for i in range(3)], self.TEMPO)
        assert [n["time"] for n in notes] == pytest.approx([0, 1 / 3, 2 / 3], abs=1e-6)
        assert [n["duration"] for n in notes] == pytest.approx([1 / 3] * 3, abs=1e-6)

    def test_long_note_ends_on_half_beat(self):
        # 3.8 temps mesurés -> 4 (et pas 3.75)
        notes = quantize_notes([raw(48, 0.5, 0.5 + 3.8 * 0.5)], self.TEMPO)
        assert notes[0]["duration"] == 4

    def test_short_note_keeps_fine_resolution(self):
        notes = quantize_notes([raw(60, 0.5, 0.5 + 0.75 * 0.5)], self.TEMPO)
        assert notes[0]["duration"] == 0.75

    def test_duration_is_never_zero(self):
        notes = quantize_notes([raw(60, 0.5, 0.55)], self.TEMPO)
        assert notes[0]["duration"] == BINARY_GRID

    def test_empty_input(self):
        assert quantize_notes([], self.TEMPO) == []
