"""Unit tests for the pure post-processing functions in core.processing."""

from core.processing import (
    _quantize_to_nearest,
    _quantize_time,
    _seconds_to_quarter_length,
    _deduplicate_notes,
    VALID_DURATIONS,
)


# ---------------------------------------------------------------------------
# _quantize_to_nearest
# ---------------------------------------------------------------------------

class TestQuantizeToNearest:
    def test_exact_values(self):
        for d in VALID_DURATIONS:
            assert _quantize_to_nearest(d, VALID_DURATIONS) == d

    def test_intermediate_rounds_to_closest(self):
        # 0.75 is between 0.5 and 1.0 — closer to 1.0
        assert _quantize_to_nearest(0.75, VALID_DURATIONS) == 1.0
        # 0.3 is between 0.25 and 0.5 — closer to 0.25
        assert _quantize_to_nearest(0.3, VALID_DURATIONS) == 0.25
        # 2.5 is between 2.0 and 3.0 — closer to 2.0 (tie goes to first match)
        assert _quantize_to_nearest(2.5, VALID_DURATIONS) in (2.0, 3.0)

    def test_zero_returns_smallest(self):
        assert _quantize_to_nearest(0, VALID_DURATIONS) == VALID_DURATIONS[-1]

    def test_negative_returns_smallest(self):
        assert _quantize_to_nearest(-1.0, VALID_DURATIONS) == VALID_DURATIONS[-1]

    def test_very_large_value(self):
        assert _quantize_to_nearest(10.0, VALID_DURATIONS) == 4.0


# ---------------------------------------------------------------------------
# _quantize_time
# ---------------------------------------------------------------------------

class TestQuantizeTime:
    def test_exact_grid_values(self):
        assert _quantize_time(0.0, 0.5) == 0.0
        assert _quantize_time(0.5, 0.5) == 0.5
        assert _quantize_time(1.0, 0.5) == 1.0

    def test_rounds_to_nearest_grid(self):
        assert _quantize_time(0.3, 0.5) == 0.5
        assert _quantize_time(0.2, 0.5) == 0.0
        assert _quantize_time(0.74, 0.5) == 0.5
        assert _quantize_time(0.76, 0.5) == 1.0

    def test_finer_grid(self):
        assert _quantize_time(0.1, 0.25) == 0.0
        assert _quantize_time(0.2, 0.25) == 0.25
        assert _quantize_time(0.4, 0.25) == 0.5


# ---------------------------------------------------------------------------
# _seconds_to_quarter_length
# ---------------------------------------------------------------------------

class TestSecondsToQuarterLength:
    def test_at_120_bpm(self):
        # At 120 BPM, 1 quarter note = 0.5 seconds
        assert _seconds_to_quarter_length(0.5, 120) == 1.0
        assert _seconds_to_quarter_length(1.0, 120) == 2.0
        assert _seconds_to_quarter_length(0.25, 120) == 0.5

    def test_at_60_bpm(self):
        # At 60 BPM, 1 quarter note = 1.0 seconds
        assert _seconds_to_quarter_length(1.0, 60) == 1.0
        assert _seconds_to_quarter_length(2.0, 60) == 2.0

    def test_zero(self):
        assert _seconds_to_quarter_length(0, 120) == 0.0


# ---------------------------------------------------------------------------
# _deduplicate_notes
# ---------------------------------------------------------------------------

class TestDeduplicateNotes:
    def test_keeps_highest_velocity(self):
        notes = [
            {"time": 0.0, "note": "C4", "duration": 1.0, "velocity": 0.5},
            {"time": 0.0, "note": "C4", "duration": 1.0, "velocity": 0.8},
        ]
        result = _deduplicate_notes(notes)
        assert len(result) == 1
        assert result[0]["velocity"] == 0.8

    def test_different_times_kept(self):
        notes = [
            {"time": 0.0, "note": "C4", "duration": 1.0, "velocity": 0.5},
            {"time": 1.0, "note": "C4", "duration": 1.0, "velocity": 0.5},
        ]
        result = _deduplicate_notes(notes)
        assert len(result) == 2

    def test_different_pitches_kept(self):
        notes = [
            {"time": 0.0, "note": "C4", "duration": 1.0, "velocity": 0.5},
            {"time": 0.0, "note": "E4", "duration": 1.0, "velocity": 0.5},
        ]
        result = _deduplicate_notes(notes)
        assert len(result) == 2

    def test_empty_list(self):
        assert _deduplicate_notes([]) == []
