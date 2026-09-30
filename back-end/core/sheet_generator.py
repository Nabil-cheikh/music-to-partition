# Couche notation (2/2) : notes quantifiées -> partition music21 -> PDF (LilyPond).
# Déterministe : testé en TDD strict (tests/test_sheet_generator.py). Voir docs/architecture.md.
import math
import os
import shutil
import tempfile
import uuid
from collections import defaultdict
from fractions import Fraction

import librosa as lr
from music21 import chord, clef, environment, instrument, layout, meter, note, stream, tempo, tie

MEASURES_PER_LINE = 4
BEATS_PER_MEASURE = 4  # 4/4 fixe

# Séparation des mains
LEFT_HAND_RATIO_THRESHOLD = 0.1
ALWAYS_RIGHT_FROM = 72     # C5 et au-dessus : main droite
ALWAYS_LEFT_BELOW = 48     # sous C3 : main gauche
RIGHT_START_CENTER, LEFT_START_CENTER = 67, 48
CENTER_SMOOTHING = 0.3
MAX_HAND_SPAN = 14         # demi-tons couverts par une main sur un même onset

# Legato : un silence plus court que cette fraction de l'écart entre onsets est comblé
LEGATO_MAX_GAP_RATIO = 0.5

# Durées écrivables (en noires), de la plus longue à la plus courte
_WRITABLE = [Fraction(x) for x in ("4", "3", "2", "3/2", "1", "3/4", "1/2", "3/8", "1/4", "1/8")] + \
            [Fraction(2, 3), Fraction(1, 3), Fraction(1, 6)]


def _configure_lilypond():
    # LILYPOND_PATH permet de surcharger la détection (ex: installation hors PATH sous Windows)
    lilypond_path = os.environ.get('LILYPOND_PATH') or shutil.which('lilypond')
    if not lilypond_path or not os.path.exists(lilypond_path):
        raise RuntimeError(
            "LilyPond introuvable. Installez-le et ajoutez-le au PATH, "
            "ou définissez la variable d'environnement LILYPOND_PATH."
        )
    environment.UserSettings()['lilypondPath'] = lilypond_path


# ---------------------------------------------------------------------------
# Mains
# ---------------------------------------------------------------------------

def split_hands(notes_data: list) -> tuple[list, list]:
    """Répartit les notes entre main droite et main gauche.

    Limites fixes aux extrêmes, sinon continuité : chaque note va à la main dont la
    hauteur moyenne récente est la plus proche. Une main ne couvre pas plus de
    MAX_HAND_SPAN sur un même onset. Si la main gauche est quasi vide, tout va à droite.
    """
    by_time = defaultdict(list)
    for n in notes_data:
        by_time[n["time"]].append(n)

    right, left = [], []
    centers = {"right": RIGHT_START_CENTER, "left": LEFT_START_CENTER}
    for time in sorted(by_time):
        group = sorted(by_time[time], key=lambda n: lr.note_to_midi(n["note"]))
        assigned = {"right": [], "left": []}
        for n in group:
            pitch = lr.note_to_midi(n["note"])
            if pitch >= ALWAYS_RIGHT_FROM:
                hand = "right"
            elif pitch < ALWAYS_LEFT_BELOW:
                hand = "left"
            else:
                hand = min(centers, key=lambda h: abs(centers[h] - pitch))
            assigned[hand].append(n)
        # une main trop étendue cède sa note extrême à l'autre, si celle-ci reste jouable
        while _span(assigned["right"]) > MAX_HAND_SPAN and _span(assigned["left"] + assigned["right"][:1]) <= MAX_HAND_SPAN:
            assigned["left"].append(assigned["right"].pop(0))
        while _span(assigned["left"]) > MAX_HAND_SPAN and _span(assigned["left"][-1:] + assigned["right"]) <= MAX_HAND_SPAN:
            assigned["right"].insert(0, assigned["left"].pop())
        for hand, bucket in (("right", right), ("left", left)):
            for n in assigned[hand]:
                bucket.append(n)
                pitch = lr.note_to_midi(n["note"])
                centers[hand] = (1 - CENTER_SMOOTHING) * centers[hand] + CENTER_SMOOTHING * pitch

    if notes_data and len(left) / len(notes_data) <= LEFT_HAND_RATIO_THRESHOLD:
        return sorted(right + left, key=lambda n: n["time"]), []
    return right, left


def _span(notes: list) -> int:
    pitches = [lr.note_to_midi(n["note"]) for n in notes]
    return max(pitches) - min(pitches) if pitches else 0


def fill_legato_gaps(hand_notes: list) -> list:
    """Prolonge une note jusqu'à l'onset suivant de la même main quand le silence
    entre les deux est court (les modèles coupent souvent les fins de notes)."""
    onsets = sorted({n["time"] for n in hand_notes})
    result = []
    for n in hand_notes:
        end = n["time"] + n["duration"]
        following = [t for t in onsets if t > n["time"]]
        if following:
            next_onset = following[0]
            gap = next_onset - end
            if 0 < gap <= LEGATO_MAX_GAP_RATIO * (next_onset - n["time"]):
                n = {**n, "duration": round(next_onset - n["time"], 6)}
        result.append(n)
    return result


def prepare_hands(notes_data: list) -> tuple[list, list]:
    """Notes quantifiées -> (main droite, main gauche) avec durées finales de la partition."""
    right, left = split_hands(notes_data)
    return fill_legato_gaps(right), fill_legato_gaps(left)


# ---------------------------------------------------------------------------
# Voix : chaque note garde sa propre durée
# ---------------------------------------------------------------------------

def assign_voices(hand_notes: list) -> list[list[dict]]:
    """Regroupe les notes de même (time, duration) en accords, puis répartit les accords
    en voix sans chevauchement. Retourne une liste de voix : [{time, duration, pitches}]."""
    events = defaultdict(list)
    for n in hand_notes:
        events[(n["time"], n["duration"])].append(n["note"])
    ordered = sorted(events.items(), key=lambda kv: (kv[0][0], -kv[0][1]))

    voices: list[list[dict]] = []
    for (time, duration), pitches in ordered:
        event = {"time": time, "duration": duration,
                 "pitches": sorted(pitches, key=lr.note_to_midi)}
        for voice in voices:
            last = voice[-1]
            if last["time"] + last["duration"] <= time + 1e-9:
                voice.append(event)
                break
        else:
            voices.append([event])
    return voices


# ---------------------------------------------------------------------------
# Mesures
# ---------------------------------------------------------------------------

def _split_duration(start: Fraction, duration: Fraction) -> list[Fraction]:
    """Découpe une durée en valeurs écrivables, en coupant aux temps forts si nécessaire."""
    pieces, pos, remaining = [], start, duration
    while remaining > 0:
        # valeur exacte d'abord, puis la famille (binaire / triolet) de la durée restante
        triplet_first = remaining.denominator % 3 == 0
        candidates = sorted(_WRITABLE, key=lambda d: (d != remaining, (d.denominator % 3 == 0) != triplet_first, -d))
        for d in candidates:
            if d <= remaining and _fits(pos, d):
                break
        else:
            d = remaining
        pieces.append(d)
        pos += d
        remaining -= d
    return pieces


def _fits(pos: Fraction, d: Fraction) -> bool:
    """Une valeur binaire commence sur un multiple d'elle-même (ou d'un temps) ;
    une valeur de triolet reste dans son temps."""
    if d.denominator % 3 == 0:
        return math.floor(pos) == math.floor(pos + d - Fraction(1, 10**6))
    unit = d if d < 1 else Fraction(1)
    return (pos / unit).denominator == 1


def _make_element(pitches: list[str], ql: Fraction):
    el = note.Note(pitches[0]) if len(pitches) == 1 else chord.Chord(pitches)
    el.quarterLength = ql
    return el


def _voice_measures(voice: list[dict], n_measures: int) -> list[list]:
    """Éléments music21 (notes/accords/silences) d'une voix, découpés par mesure."""
    measures = [[] for _ in range(n_measures)]
    pos = Fraction(0)
    measure_len = Fraction(BEATS_PER_MEASURE)

    def emit(pitches, start: Fraction, duration: Fraction):
        segments = []
        while duration > 0:
            m = int(start // measure_len)
            in_measure = min(duration, (m + 1) * measure_len - start)
            for piece in _split_duration(start - m * measure_len, in_measure):
                segments.append((m, pitches, piece))
            start += in_measure
            duration -= in_measure
        for i, (m, pitches_, piece) in enumerate(segments):
            el = note.Rest(quarterLength=piece) if pitches_ is None else _make_element(pitches_, piece)
            if pitches_ is not None and len(segments) > 1:
                el.tie = tie.Tie("start" if i == 0 else "stop" if i == len(segments) - 1 else "continue")
            measures[m].append(el)

    for event in voice:
        start = Fraction(event["time"]).limit_denominator(48)
        duration = Fraction(event["duration"]).limit_denominator(48)
        if start > pos:
            emit(None, pos, start - pos)
        emit(event["pitches"], start, duration)
        pos = start + duration
    end = n_measures * measure_len
    if pos < end:
        emit(None, pos, end - pos)
    return measures


def build_part(hand_notes: list, name: str, clef_obj, n_measures: int, bpm: int | None = None) -> stream.Part:
    part = stream.Part()
    part.partName = name
    part.insert(0, instrument.Piano())
    voices = assign_voices(hand_notes) or [[]]
    per_voice = [_voice_measures(v, n_measures) for v in voices]

    for m in range(n_measures):
        measure = stream.Measure(number=m + 1)
        if m == 0:
            measure.insert(0, clef_obj)
            measure.insert(0, meter.TimeSignature(f"{BEATS_PER_MEASURE}/4"))
            if bpm:
                measure.insert(0, tempo.MetronomeMark(number=bpm))
        elif m % MEASURES_PER_LINE == 0:
            measure.insert(0, layout.SystemLayout(isNew=True))

        # une voix secondaire n'apparaît que dans les mesures où elle joue
        active = [0] + [i for i in range(1, len(voices))
                        if any(not isinstance(e, note.Rest) for e in per_voice[i][m])]
        if len(active) == 1:
            for el in per_voice[0][m]:
                measure.append(el)
        else:
            for i in active:
                v = stream.Voice(id=str(i + 1))
                for el in per_voice[i][m]:
                    v.append(el)
                measure.insert(0, v)
        part.append(measure)
    return part


def build_score(notes_data: list, bpm: int) -> stream.Score:
    right, left = prepare_hands(notes_data)
    end = max((n["time"] + n["duration"] for n in notes_data), default=0)
    n_measures = max(1, math.ceil(end / BEATS_PER_MEASURE - 1e-9))

    score = stream.Score()
    score.insert(0, build_part(right, "Right Hand", clef.TrebleClef(), n_measures, bpm))
    if left:
        score.insert(0, build_part(left, "Left Hand", clef.BassClef(), n_measures))
    return score


def generate_piano_sheet(notes_data: list, bpm: int) -> str:
    """
    Génère une partition piano PDF. Les données doivent être pré-quantifiées.

    Returns:
        str: Chemin vers le fichier PDF généré
    """
    _configure_lilypond()
    score = build_score(notes_data, bpm)

    base_path = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
    try:
        score.write('lily.pdf', fp=base_path)
    finally:
        # music21 laisse le source LilyPond (sans extension) à côté du PDF
        if os.path.exists(base_path):
            os.remove(base_path)
    return f"{base_path}.pdf"
