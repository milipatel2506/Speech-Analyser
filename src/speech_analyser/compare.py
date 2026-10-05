"""Contrastive comparison of a participant delivery against a baseline delivery of the same text.

Both recordings are force-aligned to the transcript, so word i of the participant corresponds to
word i of the baseline (when the two transcripts differ, words are matched by sequence alignment).
For every word we compute a signed deviation per delivery dimension, *relative to the participant's
own global behaviour* (their overall tempo, pitch spread and level offset). This removes stable
speaker differences and leaves only local breakdowns, which are grouped into flaw regions bounded
by the aligned word timestamps.

Dimension     per-word metric (participant vs baseline)                        flagged when
pace          log2 duration ratio of a 3-word window, minus global median      |dev| > log2(1 + tol)
pitch         log2 ratio of F0 s.d. (semitones) over a 5-word window, - median  ratio < tol  (monotone)
energy        level difference (dB) of a 3-word window, minus global median     drop > tol dB
clarity       2-8 kHz and 4-8 kHz spectral balance differences (dB), - median  either drop > tol dB
pausing       gap after word i vs baseline gap scaled by local tempo            inserted / removed
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

import numpy as np

from .alignment import normalize_word
from .features import FrameFeatures, robust_sd
from .flaws.spec import FLAWS


@dataclass
class DetectorConfig:
    pace_tol: float = 0.12  # +-12 % local tempo change after removing the global tempo
    pace_min_words: int = 3
    pitch_ratio_tol: float = 0.78  # local pitch spread below 78 % of expected => monotone
    pitch_min_words: int = 4
    energy_tol_db: float = 3.0
    energy_min_words: int = 2
    clarity_tol_db: float = 2.0  # 2-8 kHz balance
    air_tol_db: float = 4.0  # 4-8 kHz balance (larger natural variability)
    clarity_min_words: int = 3
    pause_insert_s: float = 0.30  # extra silence beyond the expected pause
    pause_insert_min_s: float = 0.40  # and the pause itself must be at least this long
    pause_phrase_s: float = 0.30  # baseline gaps >= this are treated as intentional pauses
    pause_removed_ratio: float = 0.50  # participant keeps < 50 % of an intentional pause
    max_hole_words: int = 1  # bridge one unflagged word inside a region


@dataclass
class Region:
    type: str
    start: float
    end: float
    w0: int  # participant word indices (inclusive)
    w1: int
    measured: dict = field(default_factory=dict)
    severity: int = 1
    score: float = 0.0  # peak normalised deviation (>= 1 means past tolerance)


# --------------------------------------------------------------------------- word matching


def match_words(base_words: list[dict], part_words: list[dict]) -> list[tuple[int, int]]:
    """Pairs (participant index, baseline index) of corresponding words."""
    a = [normalize_word(w["word"]) for w in part_words]
    b = [normalize_word(w["word"]) for w in base_words]
    if a == b:
        return [(i, i) for i in range(len(a))]
    pairs = []
    for blk in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        pairs += [(blk.a + k, blk.b + k) for k in range(blk.size)]
    return pairs


# --------------------------------------------------------------------------- helpers


def _window_sum(x: np.ndarray, half: int) -> np.ndarray:
    k = np.ones(2 * half + 1)
    num = np.convolve(np.nan_to_num(x), k, mode="same")
    return num


def _rolling(fn, x: list[np.ndarray], half: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        seg = np.concatenate(x[max(0, i - half) : i + half + 1])
        seg = seg[np.isfinite(seg)]
        if len(seg) >= 5:
            out[i] = fn(seg)
    return out


def _runs(flag: np.ndarray, max_hole: int, min_len: int) -> list[tuple[int, int]]:
    """Contiguous True runs (bridging holes of <= max_hole), at least min_len long."""
    idx = np.flatnonzero(flag)
    if not len(idx):
        return []
    runs, s, p = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - p - 1 > max_hole:
            runs.append((s, p))
            s = i
        p = i
    runs.append((s, p))
    return [(int(a), int(b)) for a, b in runs if b - a + 1 >= min_len]


def _ladder_severity(ftype: str, value: float) -> int:
    """Severity 1-5 = nearest rung of the dataset's injection ladder for this flaw type."""
    ladder = np.array(FLAWS[ftype].ladder)
    if ftype in ("monotone", "rushing", "dragging", "pause_removal"):
        # ratio ladders: compare in log space (ratios of 0 are clipped)
        lv, lad = np.log(max(value, 0.02)), np.log(np.maximum(ladder, 0.02))
        return int(np.argmin(np.abs(lad - lv))) + 1
    return int(np.argmin(np.abs(ladder - value))) + 1


SILENCE_ABSORB_S = 0.15

# Clarity severity cut points (dB), placed midway between the measured band changes of adjacent
# rungs of the mumble ladder (low-pass 5.0 / 3.8 / 2.8 / 2.0 / 1.4 kHz) on the dataset baselines.
AIR_S2_DB = -11.0  # 4-8 kHz: severity 1 drops ~5 dB, severity 2+ ~18 dB (band emptied)
HF_S3_DB, HF_S4_DB, HF_S5_DB = -2.0, -5.3, -8.0  # 2-8 kHz: -1.1 / -2.9 / -7.7 / -8.2 dB


def _clarity_severity(hf_drop: float, air_drop: float) -> int:
    if hf_drop <= HF_S5_DB:
        return 5
    if hf_drop <= HF_S4_DB:
        return 4
    if hf_drop <= HF_S3_DB:
        return 3
    return 2 if air_drop <= AIR_S2_DB else 1


# Physically coupled diagnoses: mumbling also lowers level, and a quiet stretch shifts the spectral
# balance. When both fire on the same span, keep the one that is further past its own tolerance.
COUPLED = {frozenset({"volume_drop", "mumble"})}


# A pause stretched inside a dragged span (or squeezed inside a rushed one) is part of that tempo
# change, not a separate flaw: tempo edits scale the silences between the words too. The pause is
# dropped only when the tempo region's *measured* ratio accounts for it; an inserted pause that a
# mild neighbouring tempo change cannot explain is kept.
TEMPO_EXPLAINS = {"long_pause": "dragging", "pause_removal": "rushing"}
EXPLAIN_SLACK_S = 0.05


def _explained_by_tempo(r: Region, t: Region, cfg: DetectorConfig) -> bool:
    if t.type != TEMPO_EXPLAINS.get(r.type) or not (t.start - EXPLAIN_SLACK_S <= r.end and r.start <= t.end + EXPLAIN_SLACK_S):
        return False
    scaled = r.measured["baseline_pause_s"] * t.measured["duration_ratio"]
    if r.type == "long_pause":
        return r.measured["pause_s"] - scaled <= cfg.pause_insert_s
    return r.measured["pause_s"] >= cfg.pause_removed_ratio * scaled


def _resolve_overlaps(regions: list[Region], cfg: DetectorConfig) -> list[Region]:
    regions = [r for r in regions if not any(_explained_by_tempo(r, t, cfg) for t in regions)]
    drop = set()
    for i, a in enumerate(regions):
        for j, b in enumerate(regions[i + 1 :], i + 1):
            if frozenset({a.type, b.type}) not in COUPLED:
                continue
            inter = min(a.end, b.end) - max(a.start, b.start)
            if inter > 0.5 * min(a.end - a.start, b.end - b.start):
                drop.add(j if a.score >= b.score else i)
    return [r for k, r in enumerate(regions) if k not in drop]


# --------------------------------------------------------------------------- detector


@dataclass
class Comparison:
    pairs: list[tuple[int, int]]
    series: dict[str, np.ndarray]  # per participant word: signed deviations (NaN = unmatched)
    globals: dict
    regions: list[Region]


def compare(
    ff_b: FrameFeatures,
    wf_b: list[dict],
    ff_p: FrameFeatures,
    wf_p: list[dict],
    cfg: DetectorConfig | None = None,
) -> Comparison:
    cfg = cfg or DetectorConfig()
    pairs = match_words(wf_b, wf_p)
    n = len(wf_p)
    bmap = dict(pairs)  # participant index -> baseline index
    m = np.array([i in bmap for i in range(n)])

    def per_word(key: str, src: list[dict], default=np.nan) -> np.ndarray:
        out = np.full(n, default, dtype=float)
        for i, j in pairs:
            out[i] = src[j][key] if src is wf_b else src[i][key]
        return out

    # Pace uses each word's duration plus up to SILENCE_ABSORB_S of the silence after it. CTC
    # alignment places word onsets reliably, but where a word *ends* inside trailing silence is
    # ambiguous (the same audio can align as a 1.12 s word + 0 s gap or 0.88 s + 0.24 s), so raw
    # word durations would turn that ambiguity into false tempo changes. Longer pauses are left
    # out here and judged by the pause detector.
    def paced(src: list[dict]) -> np.ndarray:
        return per_word("duration", src) + np.minimum(per_word("gap_after", src), SILENCE_ABSORB_S)

    dur_p, dur_b = paced(wf_p), paced(wf_b)
    regions: list[Region] = []

    # ---------------- pace: 3-word duration ratio, relative to the global tempo
    half = 1
    ratio_local = _window_sum(dur_p * m, half) / np.maximum(_window_sum(dur_b * m, half), 1e-3)
    log_r = np.log2(np.maximum(ratio_local, 1e-3))
    tempo_global = float(np.nanmedian(log_r[m]))
    pace_dev = log_r - tempo_global
    pace_dev[~m] = np.nan
    tol = np.log2(1 + cfg.pace_tol)
    for sign, ftype in ((-1, "rushing"), (1, "dragging")):
        flag = np.nan_to_num(sign * pace_dev) > tol
        for a, b in _runs(flag, cfg.max_hole_words, cfg.pace_min_words):
            # trim edge words that only got flagged through window smoothing
            raw = np.log2(np.maximum(dur_p / np.maximum(dur_b, 1e-3), 1e-3)) - tempo_global
            while b - a + 1 > cfg.pace_min_words and sign * raw[a] < tol / 2:
                a += 1
            while b - a + 1 > cfg.pace_min_words and sign * raw[b] < tol / 2:
                b -= 1
            # measured over the whole span (onset of first word to offset of last), so micro-gaps
            # count too; summing word durations alone under-states strong tempo changes
            pd = wf_p[b]["end"] - wf_p[a]["start"]
            if a in bmap and b in bmap:
                bd = wf_b[bmap[b]]["end"] - wf_b[bmap[a]]["start"]
            else:
                bd = np.nansum(dur_b[a : b + 1]) * pd / max(np.nansum(dur_p[a : b + 1]), 1e-3)
            ratio = (pd / bd) / 2**tempo_global
            regions.append(
                Region(
                    ftype, wf_p[a]["start"], wf_p[b]["end"], a, b,
                    {"duration_ratio": ratio, "participant_s": pd, "baseline_s": bd,
                     "syll_rate_participant": sum(w["syllables"] for w in wf_p[a : b + 1]) / max(pd, 1e-3),
                     "syll_rate_baseline": sum(wf_b[bmap[i]]["syllables"] for i in range(a, b + 1) if i in bmap) / max(bd, 1e-3)},
                    _ladder_severity(ftype, ratio),
                    float(np.nanmax(sign * pace_dev[a : b + 1]) / tol),
                )
            )

    # ---------------- pitch variety: F0 spread over a 5-word window
    def word_f0(ff, words, idx):
        return [ff.f0_st[ff.slice(words[k]["start"], words[k]["end"])] for k in idx]

    f0_p = word_f0(ff_p, wf_p, range(n))
    f0_b = [np.array([np.nan]) if i not in bmap else ff_b.f0_st[ff_b.slice(wf_b[bmap[i]]["start"], wf_b[bmap[i]]["end"])] for i in range(n)]
    sd_p, sd_b = _rolling(robust_sd, f0_p, 2), _rolling(robust_sd, f0_b, 2)
    pitch_lr = np.log2(np.maximum(sd_p, 1e-3) / np.maximum(sd_b, 1e-3))
    pitch_global = float(np.nanmedian(pitch_lr[m]))
    pitch_dev = pitch_lr - pitch_global
    pitch_dev[~m] = np.nan
    ptol = np.log2(cfg.pitch_ratio_tol)
    for a, b in _runs(np.nan_to_num(pitch_dev) < ptol, cfg.max_hole_words, cfg.pitch_min_words):
        seg_p = np.concatenate(f0_p[a : b + 1])
        seg_b = np.concatenate(f0_b[a : b + 1])
        sp = robust_sd(seg_p)
        sb = robust_sd(seg_b)
        ratio = (sp / max(sb, 1e-3)) / 2**pitch_global
        regions.append(
            Region(
                "monotone", wf_p[a]["start"], wf_p[b]["end"], a, b,
                {"pitch_sd_ratio": ratio, "pitch_sd_participant_st": sp, "pitch_sd_baseline_st": sb,
                 "pitch_range_participant_st": float(np.nanpercentile(seg_p, 95) - np.nanpercentile(seg_p, 5)) if np.isfinite(seg_p).any() else 0.0,
                 "pitch_range_baseline_st": float(np.nanpercentile(seg_b, 95) - np.nanpercentile(seg_b, 5)) if np.isfinite(seg_b).any() else 0.0},
                _ladder_severity("monotone", ratio),
                float(np.nanmin(pitch_dev[a : b + 1]) / ptol),
            )
        )

    # ---------------- energy and clarity: 3-word smoothed differences
    def smoothed_delta(key: str) -> tuple[np.ndarray, float]:
        d = per_word(key, wf_p) - per_word(key, wf_b)
        d[~m] = np.nan
        sm = np.array([np.nanmedian(d[max(0, i - 1) : i + 2]) if np.isfinite(d[max(0, i - 1) : i + 2]).any() else np.nan for i in range(n)])
        g = float(np.nanmedian(d))
        return sm - g, g

    energy_dev, energy_global = smoothed_delta("energy_db")
    for a, b in _runs(np.nan_to_num(energy_dev) < -cfg.energy_tol_db, cfg.max_hole_words, cfg.energy_min_words):
        drop = float(np.nanmean(energy_dev[a : b + 1]))
        regions.append(
            Region("volume_drop", wf_p[a]["start"], wf_p[b]["end"], a, b,
                   {"level_change_db": drop}, _ladder_severity("volume_drop", drop),
                   float(-np.nanmin(energy_dev[a : b + 1]) / cfg.energy_tol_db))
        )

    # clarity uses two bands: 4-8 kHz "air" is sensitive to subtle consonant loss but saturates,
    # 2-8 kHz grades the severe end. A word is flagged when either band is past its tolerance.
    clarity_dev, clarity_global = smoothed_delta("hf_db")
    air_dev, _ = smoothed_delta("air_db")
    hnr_dev, _ = smoothed_delta("hnr_db")
    clarity_score = np.fmax(-clarity_dev / cfg.clarity_tol_db, -air_dev / cfg.air_tol_db)
    for a, b in _runs(np.nan_to_num(clarity_score) > 1, cfg.max_hole_words, cfg.clarity_min_words):
        drop = float(np.nanmean(clarity_dev[a : b + 1]))
        air = float(np.nanmean(air_dev[a : b + 1]))
        regions.append(
            Region("mumble", wf_p[a]["start"], wf_p[b]["end"], a, b,
                   {"hf_balance_change_db": drop, "air_balance_change_db": air,
                    "hnr_change_db": float(np.nanmean(hnr_dev[a : b + 1]))},
                   _clarity_severity(drop, air), float(np.nanmax(clarity_score[a : b + 1])))
        )

    # ---------------- pauses (gap after word i), expected gap scales with local tempo
    gap_p = per_word("gap_after", wf_p)
    gap_b = np.full(n, np.nan)
    for i, j in pairs:
        if i + 1 < n and bmap.get(i + 1) == j + 1:  # consecutive in both
            gap_b[i] = wf_b[j]["gap_after"]
    local_tempo = 2 ** np.nan_to_num(log_r, nan=tempo_global)
    expected = gap_b * local_tempo
    pause_dev = gap_p - expected
    for i in range(n - 1):
        if not np.isfinite(gap_b[i]):
            continue
        if pause_dev[i] > cfg.pause_insert_s and gap_p[i] > cfg.pause_insert_min_s:
            extra = float(pause_dev[i])
            regions.append(
                Region("long_pause", wf_p[i]["end"], wf_p[i + 1]["start"], i, i + 1,
                       {"pause_s": float(gap_p[i]), "expected_pause_s": float(expected[i]), "extra_s": extra,
                        "baseline_pause_s": float(gap_b[i])},
                       _ladder_severity("long_pause", extra), extra / cfg.pause_insert_s)
            )
        elif gap_b[i] >= cfg.pause_phrase_s and gap_p[i] < cfg.pause_removed_ratio * expected[i]:
            kept = float(max(gap_p[i] - 0.04, 0) / max(expected[i] - 0.04, 1e-3))
            regions.append(
                Region("pause_removal", wf_p[i]["start"], wf_p[i + 1]["end"], i, i + 1,
                       {"pause_s": float(gap_p[i]), "expected_pause_s": float(expected[i]), "pause_kept": kept,
                        "baseline_pause_s": float(gap_b[i])},
                       _ladder_severity("pause_removal", kept),
                       float(expected[i] / max(gap_p[i], 0.02)) * cfg.pause_removed_ratio)
            )

    regions = _resolve_overlaps(regions, cfg)
    regions.sort(key=lambda r: r.start)
    return Comparison(
        pairs=pairs,
        series={
            "pace_dev_log2": pace_dev,
            "pitch_dev_log2": pitch_dev,
            "energy_dev_db": energy_dev,
            "clarity_dev_db": clarity_dev,
            "air_dev_db": air_dev,
            "pause_dev_s": pause_dev,
        },
        globals={
            "tempo_ratio": float(2**tempo_global),
            "pitch_spread_ratio": float(2**pitch_global),
            "level_offset_db": energy_global,
            "hf_offset_db": clarity_global,
            "matched_words": len(pairs),
            "participant_words": n,
            "baseline_words": len(wf_b),
        },
        regions=regions,
    )


# --------------------------------------------------------------------------- overlay


def time_warp(pairs: list[tuple[int, int]], wf_p: list[dict], wf_b: list[dict]):
    """Piecewise-linear map participant time -> baseline time through matched word boundaries."""
    xp, xb = [0.0], [0.0]
    for i, j in pairs:
        for kp, kb in ((wf_p[i]["start"], wf_b[j]["start"]), (wf_p[i]["end"], wf_b[j]["end"])):
            if kp > xp[-1] and kb >= xb[-1]:
                xp.append(kp)
                xb.append(kb)
    return lambda t: np.interp(t, xp, xb)


def overlay_series(ff_b: FrameFeatures, ff_p: FrameFeatures, warp, step_s: float = 0.02) -> dict:
    """Participant and time-warped baseline feature tracks on the participant timeline."""
    stride = max(1, int(round(step_s / (ff_p.t[1] - ff_p.t[0]))))
    t = ff_p.t[::stride]
    tb = warp(t)
    jb = np.clip(np.searchsorted(ff_b.t, tb), 0, len(ff_b.t) - 1)

    def clean(a):
        return [None if not np.isfinite(v) else round(float(v), 3) for v in a]

    return {
        "t": [round(float(x), 3) for x in t],
        "participant": {
            "f0_hz": clean(ff_p.f0_hz[::stride]),
            "f0_st": clean(ff_p.f0_st[::stride]),
            "energy_db": clean(np.maximum(ff_p.energy_db[::stride], -60)),
            "hf_db": clean(ff_p.hf_db[::stride]),
        },
        "baseline": {
            "f0_hz": clean(ff_b.f0_hz[jb]),
            "f0_st": clean(ff_b.f0_st[jb]),
            "energy_db": clean(np.maximum(ff_b.energy_db[jb], -60)),
            "hf_db": clean(ff_b.hf_db[jb]),
        },
    }
