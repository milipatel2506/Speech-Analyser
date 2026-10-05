"""Inject controlled delivery flaws into an aligned baseline recording.

Each injector replaces one region of the baseline (cut at word boundaries) with a modified version
and reports a piecewise-linear time map from the original timeline to the output timeline. The
map makes the labels exact: every word timestamp and flaw boundary in the flawed file is derived
from the edit itself, not re-estimated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import parselmouth
from parselmouth.praat import call
from scipy.signal import butter, sosfiltfilt

from ..audio_io import SAMPLE_RATE
from ..features import speaker_pitch_range
from .spec import FLAWS, MUMBLE_GAIN_DB

EDGE_BLEND_S = 0.005  # blend replacement into original at splice points to avoid clicks
GAIN_RAMP_S = 0.08


@dataclass
class Flaw:
    type: str
    severity: int
    w0: int  # first affected word (index into baseline words)
    w1: int  # last affected word (inclusive)


@dataclass
class Edit:
    start: float  # region in the original timeline (s)
    end: float
    audio: np.ndarray  # replacement samples for y[start:end]
    anchors: list[tuple[float, float]]  # (orig, new) times relative to region start
    flaw: Flaw
    params: dict
    label_rel: tuple[float, float] | None = None  # explicit label in new region time, else words


@dataclass
class InjectionResult:
    audio: np.ndarray
    words: list[dict]
    flaws: list[dict]
    time_map: list[tuple[float, float]] = field(default_factory=list)


class Baseline:
    """A baseline recording plus the speaker statistics injectors need."""

    def __init__(self, y: np.ndarray, words: list[dict], sr: int = SAMPLE_RATE):
        self.y, self.words, self.sr = y, words, sr
        snd = parselmouth.Sound(y.astype(np.float64), sampling_frequency=sr)
        # same speaker-adaptive range as feature extraction, so PSOLA does not inherit octave errors
        self.pitch_floor, self.pitch_ceiling = speaker_pitch_range(snd)
        pitch = snd.to_pitch_ac(time_step=0.01, pitch_floor=self.pitch_floor, pitch_ceiling=self.pitch_ceiling)
        f0 = pitch.selected_array["frequency"]
        self.f0_median = float(np.median(f0[f0 > 0]))
        frame = int(0.025 * sr)
        rms = np.sqrt(np.mean(y[: len(y) // frame * frame].reshape(-1, frame) ** 2, axis=1))
        self.noise_rms = float(np.percentile(rms, 5))

    def gap(self, i: int) -> tuple[float, float]:
        """Silence between word i and word i+1."""
        return self.words[i]["end"], self.words[i + 1]["start"]

    def span_bounds(self, w0: int, w1: int) -> tuple[float, float]:
        """Region covering words w0..w1, cut at the middle of the surrounding gaps."""
        w = self.words
        start = (w[w0 - 1]["end"] + w[w0]["start"]) / 2 if w0 > 0 else max(0.0, w[w0]["start"] - 0.05)
        last = len(self.y) / self.sr
        end = (w[w1]["end"] + w[w1 + 1]["start"]) / 2 if w1 + 1 < len(w) else min(last, w[w1]["end"] + 0.05)
        return start, end

    def segment(self, start: float, end: float) -> np.ndarray:
        return self.y[int(round(start * self.sr)) : int(round(end * self.sr))]


# --------------------------------------------------------------------------- region injectors


def _psola(base: Baseline, seg: np.ndarray, pitch_formula: str | None = None, duration: float | None = None):
    snd = parselmouth.Sound(seg.astype(np.float64), sampling_frequency=base.sr)
    manip = call(snd, "To Manipulation", 0.01, base.pitch_floor, base.pitch_ceiling)
    if pitch_formula is not None:
        tier = call(manip, "Extract pitch tier")
        call(tier, "Formula...", pitch_formula)
        call([manip, tier], "Replace pitch tier")
    if duration is not None:
        tier = call("Create DurationTier", "dur", snd.xmin, snd.xmax)
        call(tier, "Add point", snd.xmin, duration)
        call([manip, tier], "Replace duration tier")
    out = call(manip, "Get resynthesis (overlap-add)")
    return out.values[0].astype(np.float32)


def _blend_edges(new: np.ndarray, orig: np.ndarray, sr: int) -> np.ndarray:
    n = min(int(EDGE_BLEND_S * sr), len(new) // 2, len(orig) // 2)
    if n == 0:
        return new
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    new = new.copy()
    new[:n] = ramp * new[:n] + (1 - ramp) * orig[:n]
    new[-n:] = ramp[::-1] * new[-n:] + (1 - ramp[::-1]) * orig[-n:]
    return new


def _span_edit(base: Baseline, flaw: Flaw, transform) -> Edit:
    start, end = base.span_bounds(flaw.w0, flaw.w1)
    seg = base.segment(start, end)
    new, params = transform(seg)
    if len(new) == len(seg):
        new = _blend_edges(new, seg, base.sr)
    L, N = len(seg) / base.sr, len(new) / base.sr
    return Edit(start, end, new, [(0.0, 0.0), (L, N)], flaw, params)


def _monotone(base: Baseline, flaw: Flaw) -> Edit:
    keep = FLAWS["monotone"].value(flaw.severity)
    med = base.f0_median
    formula = f"{med} * (self / {med}) ^ {keep}"  # compress log-F0 deviations by `keep`

    def tf(seg):
        out = _psola(base, seg, pitch_formula=formula)[: len(seg)]
        out = np.pad(out, (0, len(seg) - len(out)))
        return out, {"pitch_range_kept": keep, "speaker_f0_median_hz": round(med, 1)}

    return _span_edit(base, flaw, tf)


def _tempo(name: str):
    def injector(base: Baseline, flaw: Flaw) -> Edit:
        factor = FLAWS[name].value(flaw.severity)
        return _span_edit(
            base, flaw, lambda seg: (_psola(base, seg, duration=factor), {"duration_factor": factor})
        )

    return injector


def _gain_envelope(n: int, gain_db: float, sr: int) -> np.ndarray:
    g = np.full(n, 10 ** (gain_db / 20), dtype=np.float32)
    r = min(int(GAIN_RAMP_S * sr), n // 2)
    if r:
        ramp = np.linspace(1.0, g[0], r, dtype=np.float32)
        g[:r], g[-r:] = ramp, ramp[::-1]
    return g


def _volume_drop(base: Baseline, flaw: Flaw) -> Edit:
    db = FLAWS["volume_drop"].value(flaw.severity)
    return _span_edit(
        base, flaw, lambda seg: (seg * _gain_envelope(len(seg), db, base.sr), {"gain_db": db})
    )


def _mumble(base: Baseline, flaw: Flaw) -> Edit:
    cutoff = FLAWS["mumble"].value(flaw.severity)
    db = MUMBLE_GAIN_DB[flaw.severity - 1]

    def tf(seg):
        sos = butter(6, cutoff, btype="low", fs=base.sr, output="sos")
        filt = sosfiltfilt(sos, seg).astype(np.float32) * 10 ** (db / 20)
        # crossfade dry -> wet with the same ramp shape as the gain envelope
        w = 1 - (_gain_envelope(len(seg), -120.0, base.sr))
        return (1 - w) * seg + w * filt, {"lowpass_hz": cutoff, "gain_db": db}

    return _span_edit(base, flaw, tf)


def _room_tone(base: Baseline, seconds: float, rng: np.random.Generator) -> np.ndarray:
    return (rng.standard_normal(int(seconds * base.sr)) * base.noise_rms).astype(np.float32)


def _long_pause(base: Baseline, flaw: Flaw, rng: np.random.Generator) -> Edit:
    pause = FLAWS["long_pause"].value(flaw.severity)
    g0, g1 = base.gap(flaw.w0)
    mid = (g0 + g1) / 2
    left, right = base.segment(g0, mid), base.segment(mid, g1)
    new = np.concatenate([left, _room_tone(base, pause, rng), right])
    a = len(left) / base.sr
    anchors = [(0.0, 0.0), (a, a), (a + 1e-6, a + pause), (g1 - g0, g1 - g0 + pause)]
    return Edit(g0, g1, new, anchors, flaw, {"pause_s": pause}, label_rel=(a, a + pause))


def _pause_removal(base: Baseline, flaw: Flaw) -> Edit:
    keep = FLAWS["pause_removal"].value(flaw.severity)
    g0, g1 = base.gap(flaw.w0)
    gap = g1 - g0
    new_gap = 0.04 + (gap - 0.04) * keep
    seg = base.segment(g0, g1)
    half = int(new_gap * base.sr / 2)
    new = np.concatenate([seg[:half], seg[len(seg) - half :]]) if half else seg[:0]
    return Edit(
        g0, g1, new, [(0.0, 0.0), (gap, len(new) / base.sr)], flaw,
        {"pause_kept": keep, "original_pause_s": round(gap, 3), "new_pause_s": round(len(new) / base.sr, 3)},
    )


INJECTORS = {
    "monotone": _monotone,
    "rushing": _tempo("rushing"),
    "dragging": _tempo("dragging"),
    "volume_drop": _volume_drop,
    "mumble": _mumble,
    "pause_removal": _pause_removal,
}


# --------------------------------------------------------------------------- assembly


def inject(base: Baseline, flaws: list[Flaw], rng: np.random.Generator) -> InjectionResult:
    """Apply non-overlapping flaws and return the flawed audio with exact labels."""
    edits = []
    for f in flaws:
        if f.type == "long_pause":
            edits.append(_long_pause(base, f, rng))
        else:
            edits.append(INJECTORS[f.type](base, f))
    edits.sort(key=lambda e: e.start)
    for a, b in zip(edits, edits[1:]):
        if a.end > b.start:
            raise ValueError(f"overlapping flaw regions: {a.flaw} / {b.flaw}")

    sr, pieces, cursor = base.sr, [], 0.0
    orig_pts, new_pts = [0.0], [0.0]
    new_t = 0.0
    edit_new_start = []
    for e in edits:
        pieces.append(base.segment(cursor, e.start))
        new_t += e.start - cursor
        orig_pts.append(e.start)
        new_pts.append(new_t)
        edit_new_start.append(new_t)
        for o, n in e.anchors[1:]:
            orig_pts.append(e.start + o)
            new_pts.append(new_t + n)
        pieces.append(e.audio)
        new_t += len(e.audio) / sr
        cursor = e.end
    pieces.append(base.y[int(round(cursor * sr)) :])
    total_orig = len(base.y) / sr
    orig_pts.append(total_orig)
    new_pts.append(new_t + (total_orig - cursor))
    y = np.concatenate(pieces).astype(np.float32)

    def tmap(t: float) -> float:
        return float(np.interp(t, orig_pts, new_pts))

    words = [
        {"word": w["word"], "start": round(tmap(w["start"]), 4), "end": round(tmap(w["end"]), 4)}
        for w in base.words
    ]

    labels = []
    for e, ns in zip(edits, edit_new_start):
        f, spec = e.flaw, FLAWS[e.flaw.type]
        if e.label_rel is not None:
            start, end = ns + e.label_rel[0], ns + e.label_rel[1]
        else:  # for pause_removal this is the "run-on" join: word before through word after
            start, end = words[f.w0]["start"], words[f.w1]["end"]
        labels.append(
            {
                "type": f.type,
                "label": spec.label,
                "rubric": spec.rubric,
                "severity": f.severity,
                "start": round(start, 4),
                "end": round(end, 4),
                "word_span": [f.w0, f.w1],
                "text": " ".join(w["word"] for w in base.words[f.w0 : f.w1 + 1]),
                "params": e.params,
                "description": spec.describe.format(value=spec.value(f.severity)),
            }
        )

    time_map = [(round(o, 4), round(n, 4)) for o, n in zip(orig_pts, new_pts)]
    return InjectionResult(y, words, labels, time_map)
