"""End-to-end analysis: audio + transcript in, scored and explained report out."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .alignment import align
from .audio_io import SAMPLE_RATE, loudness_normalize
from .compare import Comparison, DetectorConfig, compare, overlay_series, time_warp
from .explain import explain
from .features import FrameFeatures, extract_frames, global_summary, word_features
from .scoring import score


@dataclass
class Analysed:
    """One recording after alignment and feature extraction."""

    y: np.ndarray
    words: list[dict]
    frames: FrameFeatures
    word_feats: list[dict]
    summary: dict


def analyse_recording(y: np.ndarray, transcript: str, words: list[dict] | None = None) -> Analysed:
    """Align (unless word timings are supplied) and extract features for one recording."""
    if words is None:
        words = [w.to_dict() for w in align(y, transcript)]
    ff = extract_frames(y, SAMPLE_RATE)
    wf = word_features(ff, words)
    return Analysed(y, words, ff, wf, global_summary(ff, wf))


def jsonable(x):
    """Recursively convert numpy scalars/arrays (and non-finite floats) to plain JSON types."""
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return jsonable(x.tolist())
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    return x


def report(base: Analysed, part: Analysed, cfg: DetectorConfig | None = None) -> dict:
    return jsonable(_report(base, part, cfg))


def _report(base: Analysed, part: Analysed, cfg: DetectorConfig | None = None) -> dict:
    cfg = cfg or DetectorConfig()
    comp: Comparison = compare(base.frames, base.word_feats, part.frames, part.word_feats, cfg)
    flaws = [explain(r, part.words, comp, cfg) for r in comp.regions]
    warp = time_warp(comp.pairs, part.words, base.words)
    return {
        "score": score(flaws, comp.globals),
        "flaws": flaws,
        "globals": comp.globals,
        "summary": {"participant": part.summary, "baseline": base.summary},
        "words": {"participant": part.words, "baseline": base.words},
        "word_deviation": {
            k: [None if not np.isfinite(v) else round(float(v), 4) for v in arr] for k, arr in comp.series.items()
        },
        "overlay": overlay_series(base.frames, part.frames, warp),
        "duration": round(len(part.y) / SAMPLE_RATE, 3),
    }


def analyse(participant_y: np.ndarray, transcript: str, baseline: Analysed, cfg: DetectorConfig | None = None) -> dict:
    """Full report for a participant recording against a prepared baseline."""
    part = analyse_recording(loudness_normalize(participant_y), transcript)
    return report(baseline, part, cfg)
