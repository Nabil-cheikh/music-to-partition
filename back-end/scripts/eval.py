"""Évaluation de la transcription et de la partition sur les scénarios synthétisés.

Usage (depuis back-end/) :
    uv run python scripts/eval.py                                  # tableau
    uv run python scripts/eval.py --compare baseline.json          # + deltas, exit 1 si régression
    uv run python scripts/eval.py --backend pop2piano --write out.json
    uv run python scripts/eval.py --only triplets_over_quarters

Métriques (voir docs/testing.md) :
    onset_f1         transcription : hauteur juste et onset à ±50 ms (mir_eval)
    onset_offset_f1  transcription : + offset à 20 % de la durée (min 50 ms)
    score_onset_f1   partition : hauteur + position (en noires) exactes après quantification
    score_duration   partition : part des notes bien placées qui ont aussi la bonne durée
"""
import argparse
import json
import os
import sys
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import librosa as lr  # noqa: E402
import mir_eval  # noqa: E402
import numpy as np  # noqa: E402

from core.processing import estimate_tempo, transcribe_raw  # noqa: E402
from core.quantization import quantize_notes  # noqa: E402
from core.sheet_generator import prepare_hands  # noqa: E402
from tests.conftest import SOUNDFONT_PATH, make_piano_midi, synthesize_to_wav  # noqa: E402
from tests.scenarios import SCENARIOS, Scenario  # noqa: E402

METRICS = ("onset_f1", "onset_offset_f1", "score_onset_f1", "score_duration")
DEFAULT_TOLERANCE = 0.02


def _transcription_scores(scenario: Scenario, raw) -> dict:
    ref = np.array([[s, e] for _, s, e, _ in scenario.notes])
    ref_p = lr.midi_to_hz(np.array([p for p, *_ in scenario.notes]))
    if raw:
        est = np.array([[n.onset, max(n.offset, n.onset + 1e-3)] for n in raw])
        est_p = lr.midi_to_hz(np.array([n.pitch for n in raw]))
    else:
        est, est_p = np.zeros((0, 2)), np.zeros(0)
    p, r, f, _ = mir_eval.transcription.precision_recall_f1_overlap(ref, ref_p, est, est_p, offset_ratio=None)
    _, _, f_off, _ = mir_eval.transcription.precision_recall_f1_overlap(ref, ref_p, est, est_p)
    return {"onset_precision": p, "onset_recall": r, "onset_f1": f, "onset_offset_f1": f_off}


def _expected_score_notes(scenario: Scenario, scale: float) -> list[tuple]:
    """Vérité terrain en noires, relative à la première note."""
    beat = 60 / scenario.bpm
    first = min(s for _, s, _, _ in scenario.notes)
    return [
        (p, round((s - first) / beat * scale, 3), round((e - s) / beat * scale, 3))
        for p, s, e, _ in scenario.notes
    ]


def _score_scores(scenario: Scenario, notes: list[dict], bpm: float) -> dict:
    # Une lecture à tempo double ou moitié est musicalement valide : on met la vérité à l'échelle.
    ratio = bpm / scenario.bpm
    scale = min((0.5, 1.0, 2.0), key=lambda s: abs(np.log(ratio / s)))
    expected = _expected_score_notes(scenario, scale)

    right, left = prepare_hands(notes)
    final = right + left
    if final:
        first = min(n["time"] for n in final)
        detected = [(lr.note_to_midi(n["note"]), round(n["time"] - first, 3), round(n["duration"], 3)) for n in final]
    else:
        detected = []

    exp_pos = Counter((p, t) for p, t, _ in expected)
    det_pos = Counter((p, t) for p, t, _ in detected)
    matched = sum((exp_pos & det_pos).values())
    precision = matched / len(detected) if detected else 0.0
    recall = matched / len(expected)
    f1 = 2 * precision * recall / (precision + recall) if matched else 0.0

    exp_full = Counter(expected)
    det_full = Counter(detected)
    dur_ok = sum((exp_full & det_full).values())
    return {
        "score_onset_f1": f1,
        "score_duration": dur_ok / matched if matched else 0.0,
        "bpm_detected": round(bpm, 1),
        "tempo_scale": scale,
    }


@lru_cache(maxsize=None)
def _audio(name: str) -> str:
    scenario = SCENARIOS[name]
    return synthesize_to_wav(make_piano_midi(list(scenario.notes), scenario.bpm))


def evaluate_scenario(name: str, backend: str | None = None) -> dict:
    scenario = SCENARIOS[name]
    wav = _audio(name)
    raw = transcribe_raw(wav, backend)
    tempo_map, _ = estimate_tempo(wav, raw)
    notes = quantize_notes(raw, tempo_map)
    result = {"n_expected": len(scenario.notes), "n_detected": len(raw)}
    result.update(_transcription_scores(scenario, raw))
    result.update(_score_scores(scenario, notes, tempo_map.bpm))
    return {k: round(v, 4) if isinstance(v, float) else v for k, v in result.items()}


def run(backend: str | None, only: list[str] | None) -> dict:
    names = only or list(SCENARIOS)
    started = time.time()
    scenarios = {name: evaluate_scenario(name, backend) for name in names}
    mean = {m: round(float(np.mean([s[m] for s in scenarios.values()])), 4) for m in METRICS}
    return {
        "backend": backend or os.environ.get("TRANSCRIPTION_BACKEND", "transkun"),
        "soundfont": os.path.basename(SOUNDFONT_PATH or "none"),
        "duration_s": round(time.time() - started, 1),
        "scenarios": scenarios,
        "mean": mean,
    }


def regressions(result: dict, baseline: dict, tolerance: float) -> list[str]:
    problems = []
    if result["soundfont"] != baseline.get("soundfont"):
        problems.append(f"soundfont differs ({result['soundfont']} vs {baseline.get('soundfont')}): comparison invalid")
    for name, scores in result["scenarios"].items():
        base = baseline["scenarios"].get(name)
        if base is None:
            continue
        for m in METRICS:
            if scores[m] < base[m] - tolerance:
                problems.append(f"{name}.{m}: {base[m]:.3f} -> {scores[m]:.3f}")
    return problems


def print_table(result: dict, baseline: dict | None):
    header = f"{'scenario':32} {'onset':>7} {'on+off':>7} {'score':>7} {'dur':>7} {'bpm':>6}  n(exp/det)"
    print(f"backend={result['backend']}  soundfont={result['soundfont']}  duration={result['duration_s']}s")
    print(header)
    print("-" * len(header))
    for name, s in result["scenarios"].items():
        cells = []
        for m in METRICS:
            cell = f"{s[m]:.3f}"
            if baseline and name in baseline["scenarios"]:
                delta = s[m] - baseline["scenarios"][name][m]
                cell = f"{s[m]:.2f}{delta:+.2f}" if abs(delta) >= 0.005 else f"{s[m]:.3f}"
            cells.append(f"{cell:>7}")
        print(f"{name:32} {' '.join(cells)} {s['bpm_detected']:>6}  {s['n_expected']}/{s['n_detected']}")
    print("-" * len(header))
    print(f"{'MEAN':32} " + " ".join(f"{result['mean'][m]:>7.3f}" for m in METRICS))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", help="transkun (default) | pop2piano")
    parser.add_argument("--only", nargs="+", choices=list(SCENARIOS), help="subset of scenarios")
    parser.add_argument("--compare", type=Path, help="baseline JSON to compare against")
    parser.add_argument("--tolerance", type=float, help=f"allowed drop per metric (default: baseline's, else {DEFAULT_TOLERANCE})")
    parser.add_argument("--write", type=Path, help="write results JSON here")
    args = parser.parse_args()

    result = run(args.backend, args.only)
    baseline = json.loads(args.compare.read_text()) if args.compare else None
    print_table(result, baseline)

    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + "\n")
        print(f"\nwritten: {args.write}")

    if baseline:
        tolerance = args.tolerance if args.tolerance is not None else baseline.get("tolerance", DEFAULT_TOLERANCE)
        problems = regressions(result, baseline, tolerance)
        if problems:
            print(f"\nREGRESSIONS (tolerance {tolerance}):")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"\nno regression vs {args.compare} (tolerance {tolerance})")


if __name__ == "__main__":
    main()
