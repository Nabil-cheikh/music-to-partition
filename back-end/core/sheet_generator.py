import re
import shutil
import os
import tempfile
import uuid
from collections import defaultdict
from music21 import environment, layout, stream, instrument, clef, meter, tempo, note, chord

MEASURES_PER_LINE = 4


def _extract_octave(note_name: str) -> int:
    """Extrait l'octave d'un nom de note (ex: 'C#5' -> 5)"""
    match = re.search(r'(\d+)$', note_name)
    return int(match.group(1)) if match else 4


def _configure_lilypond():
    us = environment.UserSettings()
    lilypond_path = shutil.which('lilypond')
    if lilypond_path:
        us['lilypondPath'] = lilypond_path


def _create_part(name: str, clef_type, bpm: int = None) -> stream.Part:
    part = stream.Part()
    part.partName = name
    part.insert(0, instrument.Piano())
    part.insert(0, clef_type)
    part.insert(0, meter.TimeSignature('4/4'))
    if bpm:
        part.insert(0, tempo.MetronomeMark(number=bpm))
    return part


LEFT_HAND_RATIO_THRESHOLD = 0.1


def _split_notes_by_hand(notes_data: list) -> tuple:
    low_count = sum(1 for n in notes_data if _extract_octave(n["note"]) < 4)
    force_right = len(notes_data) > 0 and low_count / len(notes_data) <= LEFT_HAND_RATIO_THRESHOLD

    right_hand_notes = defaultdict(list)
    left_hand_notes = defaultdict(list)
    for n in notes_data:
        if force_right or _extract_octave(n["note"]) >= 4:
            right_hand_notes[n["time"]].append(n)
        else:
            left_hand_notes[n["time"]].append(n)
    return right_hand_notes, left_hand_notes


def _insert_notes(part: stream.Part, grouped_notes: dict):
    for time, notes in grouped_notes.items():
        if len(notes) == 1:
            m21_note = note.Note(notes[0]["note"])
            m21_note.quarterLength = notes[0]["duration"]
            part.insert(time, m21_note)
        else:
            pitches = [n["note"] for n in notes]
            duration = max(n["duration"] for n in notes)
            m21_chord = chord.Chord(pitches)
            m21_chord.quarterLength = duration
            part.insert(time, m21_chord)


def _align_parts_duration(parts: list, notes_data: list):
    max_end = max(
        (n["time"] + n["duration"] for n in notes_data),
        default=0
    )
    for part in parts:
        if part.highestTime < max_end:
            part.insert(max_end, note.Rest(quarterLength=0))


def _finalize_parts(*parts: stream.Part) -> list:
    finalized = []
    for part in parts:
        part = part.makeMeasures()
        part.makeRests(fillGaps=True, inPlace=True)
        finalized.append(part)
    return finalized


def _insert_system_breaks(parts: list, measures_per_line: int = MEASURES_PER_LINE):
    for part in parts:
        measures = list(part.getElementsByClass('Measure'))
        for i, m in enumerate(measures):
            if i > 0 and i % measures_per_line == 0:
                m.insert(0, layout.SystemLayout(isNew=True))


def generate_piano_sheet(notes_data: list, bpm: int) -> str:
    """
    Génère une partition piano PDF. Les données doivent être pré-quantifiées.

    Returns:
        str: Chemin vers le fichier PDF généré
    """
    _configure_lilypond()

    right_hand = _create_part("Right Hand", clef.TrebleClef(), bpm)
    left_hand = _create_part("Left Hand", clef.BassClef())

    right_notes, left_notes = _split_notes_by_hand(notes_data)
    _insert_notes(right_hand, right_notes)

    parts = [right_hand]
    if left_notes:
        _insert_notes(left_hand, left_notes)
        parts.append(left_hand)

    _align_parts_duration(parts, notes_data)
    parts = _finalize_parts(*parts)
    _insert_system_breaks(parts)

    score = stream.Score()
    for part in parts:
        score.insert(0, part)

    base_path = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
    score.write('lily.pdf', fp=base_path)

    return f"{base_path}.pdf"
