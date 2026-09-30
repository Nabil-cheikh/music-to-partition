"""Strict TDD tests for core.sheet_generator (deterministic, no model)."""
import os
import shutil

import pytest
from music21 import chord, note, stream

from core.sheet_generator import (
    assign_voices,
    build_score,
    fill_legato_gaps,
    generate_piano_sheet,
    split_hands,
)


def n(name, time, duration, velocity=0.8):
    return {"note": name, "time": time, "duration": duration, "velocity": velocity}


def names(notes):
    return sorted(x["note"] for x in notes)


class TestSplitHands:
    def test_extremes_are_fixed(self):
        right, left = split_hands([n("C5", 0, 1), n("B2", 0, 1)] * 1 + [n("C2", 1, 1), n("D5", 1, 1)])
        assert names(right) == ["C5", "D5"] and names(left) == ["B2", "C2"]

    def test_middle_notes_follow_continuity(self):
        # la main gauche monte jusqu'à C4 : elle garde ce C4
        lh = [n(p, i, 1) for i, p in enumerate(["C3", "E3", "G3", "B3", "C4"])]
        rh = [n(p, i, 1) for i, p in enumerate(["E5", "F5", "G5", "A5", "B5"])]
        right, left = split_hands(lh + rh)
        assert "C4" in names(left)

    def test_hand_span_is_limited(self):
        # C4-G5 (19 demi-tons) injouable à droite ; C3-C4 jouable à gauche
        right, left = split_hands([n("C4", 0, 1), n("G5", 0, 1), n("C3", 0, 1), n("C3", 1, 1)])
        assert names(right) == ["G5"] and names(left) == ["C3", "C3", "C4"]

    def test_unplayable_span_is_not_moved_into_another_unplayable_span(self):
        right, left = split_hands([n("C4", 0, 1), n("E5", 0, 1), n("G5", 0, 1), n("C2", 0, 1), n("C3", 1, 1)])
        assert names(right) == ["C4", "E5", "G5"]

    def test_sparse_left_hand_moves_to_right(self):
        notes = [n("C5", i, 1) for i in range(10)] + [n("C3", 0, 1)]
        right, left = split_hands(notes)
        assert left == [] and len(right) == 11


class TestFillLegatoGaps:
    def test_short_gap_is_filled(self):
        result = fill_legato_gaps([n("C4", 0, 1.5), n("D4", 2, 1)])
        assert result[0]["duration"] == 2

    def test_long_gap_is_a_rest(self):
        result = fill_legato_gaps([n("C4", 0, 0.5), n("D4", 2, 1)])
        assert result[0]["duration"] == 0.5

    def test_overlapping_note_is_untouched(self):
        result = fill_legato_gaps([n("C3", 0, 4), n("E4", 1, 1)])
        assert result[0]["duration"] == 4


class TestAssignVoices:
    def test_same_onset_same_duration_is_one_chord(self):
        voices = assign_voices([n("C4", 0, 1), n("E4", 0, 1)])
        assert len(voices) == 1 and voices[0][0]["pitches"] == ["C4", "E4"]

    def test_different_durations_split_into_voices(self):
        voices = assign_voices([n("C3", 0, 4), n("G3", 0, 2), n("E3", 2, 2)])
        assert len(voices) == 2
        assert [(e["time"], e["duration"]) for e in voices[0]] == [(0, 4)]
        assert [(e["time"], e["duration"]) for e in voices[1]] == [(0, 2), (2, 2)]

    def test_held_note_under_melody(self):
        voices = assign_voices([n("C3", 0, 4)] + [n("E4", t, 1) for t in range(4)])
        assert [len(v) for v in voices] == [1, 4]


def _durations(part):
    return [el.quarterLength for el in part.recurse().notesAndRests]


class TestBuildScore:
    def test_two_parts_with_equal_measure_count(self):
        score = build_score([n("C5", 0, 4), n("C3", 0, 8)], 120)
        parts = list(score.parts)
        assert len(parts) == 2
        assert [len(p.getElementsByClass(stream.Measure)) for p in parts] == [2, 2]

    def test_measures_are_full(self):
        score = build_score([n("C5", 0.5, 1), n("E5", 2, 0.5), n("C3", 0, 4)], 120)
        for part in score.parts:
            for m in part.getElementsByClass(stream.Measure):
                voices = m.voices or [m]
                for v in voices:
                    assert sum(el.quarterLength for el in v.notesAndRests) == 4

    def test_note_across_barline_is_tied(self):
        score = build_score([n("C5", 3, 2), n("C3", 0, 8)], 120)
        rh_notes = [el for el in score.parts[0].recurse().notes]
        assert [el.tie.type for el in rh_notes] == ["start", "stop"]

    def test_chord_notes_keep_their_own_durations(self):
        score = build_score([n("C3", 0, 4), n("G3", 0, 2), n("E3", 2, 2), n("C5", 0, 4)], 90)
        left = score.parts[1]
        measure = left.getElementsByClass(stream.Measure)[0]
        assert len(measure.voices) == 2

    def test_triplets_are_written(self):
        score = build_score([n(p, i / 3, 1 / 3) for i, p in enumerate(["C5", "D5", "E5"])] + [n("C3", 0, 4)], 90)
        rh = [el for el in score.parts[0].recurse().notes]
        assert all(el.duration.tuplets for el in rh)

    def test_triplet_duration_is_not_split_into_binary_values(self):
        from core.sheet_generator import _split_duration
        from fractions import Fraction as F
        assert _split_duration(F(0), F(1, 3)) == [F(1, 3)]
        assert _split_duration(F(0), F(2, 3)) == [F(2, 3)]

    def test_dotted_rhythm_is_not_split(self):
        score = build_score([n("E5", 0, 1.5), n("D5", 1.5, 0.5), n("C5", 2, 2), n("C3", 0, 4)], 110)
        rh = [el.quarterLength for el in score.parts[0].recurse().notes]
        assert rh == [1.5, 0.5, 2.0]

    def test_chord_element_for_simultaneous_notes(self):
        score = build_score([n("C5", 0, 4), n("E5", 0, 4), n("C3", 0, 4)], 120)
        rh = list(score.parts[0].recurse().notes)
        assert isinstance(rh[0], chord.Chord) and len(rh[0].pitches) == 2

    def test_exports_valid_musicxml(self, tmp_path):
        score = build_score([n("C3", 0, 4), n("G3", 0, 2), n("E3", 2, 2)]
                            + [n(p, i / 3, 1 / 3) for i, p in enumerate(["C5", "D5", "E5"])], 90)
        out = score.write("musicxml", fp=tmp_path / "score.musicxml")
        assert os.path.getsize(out) > 0


lilypond_available = bool(os.environ.get("LILYPOND_PATH") or shutil.which("lilypond"))


@pytest.mark.skipif(not lilypond_available, reason="LilyPond not installed (set LILYPOND_PATH)")
class TestGeneratePianoSheet:
    def test_produces_pdf_and_cleans_ly_source(self):
        pdf = generate_piano_sheet([n("C3", 0, 4), n("G3", 0, 2), n("E3", 2, 2), n("C5", 0, 1),
                                    n("D5", 1, 1 / 3), n("E5", 4 / 3, 1 / 3), n("F5", 5 / 3, 1 / 3)], 90)
        try:
            with open(pdf, "rb") as f:
                assert f.read(4) == b"%PDF"
            assert not os.path.exists(pdf[: -len(".pdf")])
        finally:
            os.remove(pdf)
