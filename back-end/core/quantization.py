# Couche notation (1/2) : notes brutes en secondes -> notes quantifiées en noires.
# Déterministe : testé en TDD strict (tests/test_quantization.py). Voir docs/architecture.md.
import math

import numpy as np

from core.transcription import RawNote

# Nettoyage
MIN_NOTE_SECONDS = 0.03          # plus court : faux positif typique
MIN_VELOCITY = 0.05
GHOST_INTERVALS = (12, 19, 24)   # octave, octave+quinte, double octave (harmoniques)
GHOST_ONSET_WINDOW = 0.03        # s
GHOST_VELOCITY_RATIO = 0.5

# Tempo
MIN_BPM, MAX_BPM = 50, 160
STEADY_TEMPO_MAX_RESIDUAL = 0.04  # s : en dessous, tempo constant ; au-dessus, carte de tempo
TEMPO_FACTORS = (0.5, 2 / 3, 1, 1.5, 2)
ON_BEAT_TOLERANCE = 0.03          # s
COMPLEXITY_WEIGHT = 0.1           # s de pénalité pour une note hors temps / demi-temps

# Grille
BINARY_GRID = 0.25               # double croche
TRIPLET_GRID = 1 / 3             # croche de triolet
TRIPLET_BIAS = 0.5               # le triolet doit réduire l'erreur de moitié pour être choisi
MIN_QUARTER_LENGTH = 0.25
SHIFT_TOLERANCE = 0.1            # temps : une première note un peu avant un temps compte sur ce temps
LONG_NOTE_BEATS = 1.0            # une note d'au moins un temps...
LONG_NOTE_END_GRID = 0.5         # ...finit sur un demi-temps


# ---------------------------------------------------------------------------
# Helpers historiques (conservés, testés dans tests/test_processing_units.py)
# ---------------------------------------------------------------------------

VALID_DURATIONS = [4.0, 3.0, 2.0, 1.5, 1.0, 0.5, 0.25]


def _quantize_to_nearest(value: float, grid: list) -> float:
    """Arrondit une durée à la valeur musicale la plus proche"""
    if value <= 0:
        return grid[-1]
    return min(grid, key=lambda d: abs(d - value))


def _quantize_time(raw_time: float, grid_resolution: float = 0.5) -> float:
    """Quantifie le temps sur une grille régulière."""
    return round(raw_time / grid_resolution) * grid_resolution


def _seconds_to_quarter_length(seconds: float, bpm: int) -> float:
    return seconds * (bpm / 60)


def _deduplicate_notes(notes: list) -> list:
    """Si plusieurs notes ont le même time et pitch, garde la plus forte vélocité."""
    best_notes = {}
    for n in notes:
        key = (n["time"], n["note"])
        if key not in best_notes or n["velocity"] > best_notes[key]["velocity"]:
            best_notes[key] = n
    return list(best_notes.values())


# ---------------------------------------------------------------------------
# Nettoyage des notes brutes
# ---------------------------------------------------------------------------

def clean_notes(notes: list[RawNote]) -> list[RawNote]:
    """Supprime les notes trop courtes, trop faibles, et les harmoniques fantômes."""
    kept = [n for n in notes if n.offset - n.onset >= MIN_NOTE_SECONDS and n.velocity >= MIN_VELOCITY]
    ghosts = set()
    for i, n in enumerate(kept):
        for m in kept:
            if (
                n.pitch - m.pitch in GHOST_INTERVALS
                and abs(n.onset - m.onset) <= GHOST_ONSET_WINDOW
                and n.velocity < GHOST_VELOCITY_RATIO * m.velocity
            ):
                ghosts.add(i)
                break
    return [n for i, n in enumerate(kept) if i not in ghosts]


# ---------------------------------------------------------------------------
# Tempo : secondes -> temps (beats)
# ---------------------------------------------------------------------------

def normalize_beats(beat_times: np.ndarray) -> np.ndarray:
    """Ramène le tempo dans [MIN_BPM, MAX_BPM] en sautant ou en subdivisant des beats."""
    beats = np.asarray(beat_times, dtype=float)
    if len(beats) < 2:
        return beats
    bpm = 60 / np.median(np.diff(beats))
    while bpm > MAX_BPM and len(beats) >= 4:
        beats, bpm = beats[::2], bpm / 2
    while bpm < MIN_BPM:
        beats = np.sort(np.concatenate([beats, (beats[:-1] + beats[1:]) / 2]))
        bpm *= 2
    return beats


def _grid_cost(onsets: list[float], bpm: float) -> float:
    """Coût d'un tempo : erreur moyenne (s) des onsets sur la grille adaptative,
    plus une pénalité pour les onsets hors temps et hors demi-temps."""
    period = 60 / bpm
    first = min(onsets)
    cost = 0.0
    for t in onsets:
        x = (t - first) / period
        error = min(abs(x - _snap(x, BINARY_GRID)), abs(x - _snap(x, TRIPLET_GRID))) * period
        if abs(x - round(x)) * period < ON_BEAT_TOLERANCE:
            complexity = 0.0
        elif abs(x - _snap(x, 0.5)) * period < ON_BEAT_TOLERANCE:
            complexity = 0.5
        else:
            complexity = 1.0
        cost += error + COMPLEXITY_WEIGHT * complexity
    return cost / len(onsets)


def choose_bpm(onsets: list[float], tracker_bpms: list[float]) -> float | None:
    """Parmi les tempos des beat trackers et leurs multiples usuels (x1/2, x2/3, x3/2, x2),
    choisit celui sur lequel les onsets transcrits tombent le plus proprement."""
    candidates = {b * f for b in tracker_bpms if b > 0 for f in TEMPO_FACTORS if MIN_BPM <= b * f <= MAX_BPM}
    if not onsets or not candidates:
        return None
    return min(sorted(candidates), key=lambda b: _grid_cost(onsets, b))


class TempoMap:
    """Convertit des secondes en temps. Tempo constant si les beats sont réguliers,
    sinon interpolation linéaire entre beats (rubato). Extrapolation au tempo moyen.
    Si anchor est donné, cet instant (ex : premier onset) tombe exactement sur un temps."""

    def __init__(self, beat_times, fallback_bpm: float = 120.0, anchor: float | None = None):
        beats = normalize_beats(np.asarray(beat_times, dtype=float))
        if len(beats) < 2:
            self.bpm = float(fallback_bpm)
            self._origin, self._period, self._beats = (beats[0] if len(beats) else 0.0), 60 / self.bpm, None
        else:
            idx = np.arange(len(beats))
            period, origin = np.polyfit(idx, beats, 1)
            residual = np.std(beats - (origin + period * idx))
            self.bpm = 60 / period
            self._origin, self._period = origin, period
            self._beats = beats if residual > STEADY_TEMPO_MAX_RESIDUAL else None
        self._anchor_beats = 0.0
        if anchor is not None:
            self._anchor_beats = self._raw_beats(anchor)

    @classmethod
    def steady(cls, bpm: float, anchor: float) -> "TempoMap":
        return cls([], fallback_bpm=bpm, anchor=anchor)

    def _raw_beats(self, t: float) -> float:
        if self._beats is None or t < self._beats[0] or t > self._beats[-1]:
            return (t - self._origin) / self._period
        return float(np.interp(t, self._beats, np.arange(len(self._beats))))

    def to_beats(self, t: float) -> float:
        return self._raw_beats(t) - self._anchor_beats


# ---------------------------------------------------------------------------
# Grille adaptative
# ---------------------------------------------------------------------------

def _snap(x: float, grid: float) -> float:
    return round(x / grid) * grid


def choose_grids(positions: list[float]) -> dict[int, float]:
    """Pour chaque temps (beat entier), choisit la grille binaire ou ternaire
    qui minimise l'erreur de quantification des positions qui y tombent."""
    by_beat: dict[int, list[float]] = {}
    for x in positions:
        by_beat.setdefault(math.floor(x + 1e-9), []).append(x)
    grids = {}
    for beat, xs in by_beat.items():
        binary_err = sum(abs(x - _snap(x, BINARY_GRID)) for x in xs)
        triplet_err = sum(abs(x - _snap(x, TRIPLET_GRID)) for x in xs)
        use_triplet = len(xs) >= 2 and triplet_err < TRIPLET_BIAS * binary_err
        grids[beat] = TRIPLET_GRID if use_triplet else BINARY_GRID
    return grids


def _snap_adaptive(x: float, grids: dict[int, float]) -> float:
    grid = grids.get(math.floor(x + 1e-9), BINARY_GRID)
    return round(_snap(x, grid), 6)


def quantize_notes(notes: list[RawNote], tempo: TempoMap) -> list[dict]:
    """Notes brutes -> NoteSegment (dicts) en noires, premier note ramenée dans [0, 1)."""
    import librosa as lr

    notes = clean_notes(notes)
    if not notes:
        return []
    onsets = [tempo.to_beats(n.onset) for n in notes]
    offsets = [tempo.to_beats(n.offset) for n in notes]
    shift = math.floor(min(onsets) + SHIFT_TOLERANCE)
    onsets = [x - shift for x in onsets]
    offsets = [x - shift for x in offsets]

    grids = choose_grids(onsets)
    result = []
    for n, on, off in zip(notes, onsets, offsets):
        start = _snap_adaptive(on, grids)
        if off - on >= LONG_NOTE_BEATS:
            end = round(_snap(off, LONG_NOTE_END_GRID), 6)
        else:
            end = _snap_adaptive(off, grids)
        step = grids.get(math.floor(start + 1e-9), BINARY_GRID)
        duration = round(max(end - start, step), 6)
        result.append({
            "time": start,
            "note": lr.midi_to_note(n.pitch, unicode=False),
            "duration": duration,
            "velocity": round(n.velocity, 3),
        })
    result = _deduplicate_notes(result)
    result.sort(key=lambda n: (n["time"], n["note"]))
    return result
