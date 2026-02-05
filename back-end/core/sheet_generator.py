import re
import os
import uuid
from music21 import chord

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def _extract_octave(note_name: str) -> int:
    """Extrait l'octave d'un nom de note (ex: 'C#5' -> 5)"""
    match = re.search(r'(\d+)$', note_name)
    return int(match.group(1)) if match else 4


def generate_piano_sheet(notes_data: list, bpm: int) -> str:
    """
    Génère une partition piano PDF. Les données doivent être pré-quantifiées.

    Returns:
        str: Chemin vers le fichier PDF généré
    """
    from music21 import environment, stream, instrument, clef, meter, tempo, note

    us = environment.UserSettings()
    us['lilypondPath'] = '/opt/homebrew/bin/lilypond'

    score = stream.Score()

    right_hand = stream.Part()
    right_hand.partName = "Right Hand"
    right_hand.insert(0, instrument.Piano())
    right_hand.insert(0, clef.TrebleClef())
    right_hand.insert(0, meter.TimeSignature('4/4'))
    right_hand.insert(0, tempo.MetronomeMark(number=bpm))

    left_hand = stream.Part()
    left_hand.partName = "Left Hand"
    left_hand.insert(0, instrument.Piano())
    left_hand.insert(0, clef.BassClef())
    left_hand.insert(0, meter.TimeSignature('4/4'))

    from collections import defaultdict
    right_hand_notes = defaultdict(list)
    left_hand_notes = defaultdict(list)

    for n in notes_data:
        if _extract_octave(n["note"]) >= 4:
            right_hand_notes[n["time"]].append(n)
        else:
            left_hand_notes[n["time"]].append(n)

    for time, notes in right_hand_notes.items():
        if len(notes) == 1:
            m21_note = note.Note(notes[0]["note"])
            m21_note.quarterLength = notes[0]["duration"]
            right_hand.insert(time, m21_note)
        else:
            pitches = [n["note"] for n in notes]
            duration = max(n["duration"] for n in notes)
            m21_chord = chord.Chord(pitches)
            m21_chord.quarterLength = duration
            right_hand.insert(time, m21_chord)

    for time, notes in left_hand_notes.items():
        if len(notes) == 1:
            m21_note = note.Note(notes[0]["note"])
            m21_note.quarterLength = notes[0]["duration"]
            left_hand.insert(time, m21_note)
        else:
            pitches = [n["note"] for n in notes]
            duration = max(n["duration"] for n in notes)
            m21_chord = chord.Chord(pitches)
            m21_chord.quarterLength = duration
            left_hand.insert(time, m21_chord)

    score.insert(0, right_hand)
    score.insert(0, left_hand)

    base_path = os.path.join(OUTPUT_DIR, str(uuid.uuid4()))
    score.write('lily.pdf', fp=base_path)

    return f"{base_path}.pdf"
