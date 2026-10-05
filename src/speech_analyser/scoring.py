"""Rubric scoring: deterministic 0-100 scores per delivery dimension and overall.

score(dimension) = 100 - sum(region penalties) - global penalty, clipped to [0, 100]

* region penalty grows with severity (rung of the calibrated injection ladder) and is weighted by
  how much of the speech the region covers, so one long monotone stretch costs more than a short one
* global penalty covers whole-speech deviations that are not local (e.g. reading the entire speech
  25 % faster than the reference, or with a uniformly flat pitch)
"""

from __future__ import annotations

import math

RUBRIC = {
    "pace": {"label": "Pace", "weight": 0.20},
    "pausing": {"label": "Pausing", "weight": 0.20},
    "pitch_variety": {"label": "Pitch variety", "weight": 0.20},
    "energy": {"label": "Vocal energy", "weight": 0.20},
    "clarity": {"label": "Clarity", "weight": 0.20},
}
SEVERITY_PENALTY = {1: 8.0, 2: 16.0, 3: 28.0, 4: 42.0, 5: 58.0}
REFERENCE_SPAN_S = 5.0  # a region this long receives the full severity penalty
MIN_COVERAGE = 0.6

GLOBAL_TOL = {"tempo": 0.15, "pitch": 0.25}  # tolerated whole-speech deviation (ratio)

BANDS = [(90, "Excellent"), (75, "Strong"), (60, "Developing"), (40, "Weak"), (0, "Poor")]


def _band(score: float) -> str:
    return next(name for lo, name in BANDS if score >= lo)


def score(flaws: list[dict], globals_: dict) -> dict:
    penalties = {k: [] for k in RUBRIC}
    for f in flaws:
        # coverage is measured on the reference duration where known: rushing *shortens* its own
        # span, so the participant-side length would make worse rushing look smaller
        span = f["measured"].get("baseline_s", f["end"] - f["start"])
        cover = max(MIN_COVERAGE, min(1.5, span / REFERENCE_SPAN_S)) if f["type"] not in ("long_pause", "pause_removal") else 1.0
        penalties[f["rubric"]].append(
            {"flaw": f["label"], "at": f["start"], "points": round(SEVERITY_PENALTY[f["severity"]] * cover, 1)}
        )

    tempo_dev = abs(math.log2(globals_["tempo_ratio"]))
    if tempo_dev > math.log2(1 + GLOBAL_TOL["tempo"]):
        pts = min(30.0, 80 * (tempo_dev - math.log2(1 + GLOBAL_TOL["tempo"])))
        kind = "slower" if globals_["tempo_ratio"] > 1 else "faster"
        penalties["pace"].append({"flaw": f"Whole speech {abs(globals_['tempo_ratio'] - 1):.0%} {kind} than reference", "at": None, "points": round(pts, 1)})
    if globals_["pitch_spread_ratio"] < 1 - GLOBAL_TOL["pitch"]:
        pts = min(30.0, 80 * (1 - GLOBAL_TOL["pitch"] - globals_["pitch_spread_ratio"]))
        penalties["pitch_variety"].append({"flaw": f"Overall pitch spread {globals_['pitch_spread_ratio']:.0%} of reference", "at": None, "points": round(pts, 1)})

    dims = {}
    for key, meta in RUBRIC.items():
        s = max(0.0, 100.0 - sum(p["points"] for p in penalties[key]))
        dims[key] = {"label": meta["label"], "score": round(s, 1), "band": _band(s), "deductions": penalties[key]}
    overall = sum(RUBRIC[k]["weight"] * d["score"] for k, d in dims.items())
    return {"overall": round(overall, 1), "band": _band(overall), "dimensions": dims}
