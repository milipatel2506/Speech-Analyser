"""Acoustic feature extraction on a common 10 ms grid, normalised per speaker.

Frame features
  f0_st      F0 in semitones relative to the speaker's median F0: 12*log2(f0 / median). Removes
             biological pitch differences (e.g. a 100 Hz male and a 210 Hz female voice both sit at 0 st)
  energy_db  RMS level in dB relative to the speaker's median voiced level
  hnr_db     harmonics-to-noise ratio (Praat cross-correlation method); voice clarity / breathiness
  hf_db      spectral balance: power in 2-8 kHz relative to 80 Hz-2 kHz, in dB (articulation crispness)
  air_db     high-band balance: power in 4-8 kHz relative to 80 Hz-4 kHz, in dB (fricatives, bursts);
             far more sensitive than hf_db to subtle loss of consonant detail, but saturates sooner
  centroid   spectral centroid in Hz (from the FFT power spectrum)
  flux       positive spectral flux of the log spectrum (rate of articulatory change)
  mfcc       13 MFCCs with per-utterance mean/variance normalisation

Pitch tracking uses the two-pass speaker-adaptive range of De Looze & Hirst (2008): a first pass
with a wide 60-700 Hz range, then floor = 0.75 * Q1 and ceiling = 1.5 * Q3 of the first-pass F0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import librosa
import numpy as np
import parselmouth

from .audio_io import SAMPLE_RATE

HOP_S = 0.01
N_FFT = 512  # 32 ms at 16 kHz
WIN = 400  # 25 ms analysis window
HF_SPLIT_HZ = 2000.0
AIR_SPLIT_HZ = 4000.0


@dataclass
class FrameFeatures:
    t: np.ndarray
    f0_hz: np.ndarray
    f0_st: np.ndarray
    energy_db: np.ndarray
    hnr_db: np.ndarray
    hf_db: np.ndarray
    air_db: np.ndarray
    centroid: np.ndarray
    flux: np.ndarray
    mfcc: np.ndarray  # (n_frames, 13)
    f0_median_hz: float
    level_ref_db: float
    pitch_range_hz: tuple[float, float]

    def slice(self, start: float, end: float) -> slice:
        a = int(np.searchsorted(self.t, start))
        b = int(np.searchsorted(self.t, end))
        return slice(a, max(b, a + 1))


def _pitch(snd: parselmouth.Sound, floor: float, ceiling: float) -> parselmouth.Pitch:
    return snd.to_pitch_ac(time_step=HOP_S, pitch_floor=floor, pitch_ceiling=ceiling)


def _on_grid(xs: np.ndarray, values: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Nearest-frame resampling of a Praat track onto the librosa grid (NaN stays NaN)."""
    idx = np.clip(np.searchsorted(xs, t), 0, len(xs) - 1)
    return values[idx]


OCTAVE_JUMP_ST = 7.0  # a frame this far from its local median is a tracking error, not intonation
MAX_EXCURSION_ST = 15.0


def remove_octave_jumps(st: np.ndarray, half: int = 7) -> np.ndarray:
    """Drop pitch frames that are halving/doubling errors: far from the speaker median or from the
    median of the surrounding 150 ms of voiced frames."""
    out = st.copy()
    out[np.abs(out) > MAX_EXCURSION_ST] = np.nan
    finite = np.isfinite(out)
    for i in np.flatnonzero(finite):
        win = out[max(0, i - half) : i + half + 1]
        win = win[np.isfinite(win)]
        if len(win) >= 3 and abs(out[i] - np.median(win)) > OCTAVE_JUMP_ST:
            out[i] = np.nan
    return out


def robust_sd(a: np.ndarray) -> float:
    """1.4826 x median absolute deviation: equals the s.d. for Gaussian data, ignores outliers."""
    a = a[np.isfinite(a)]
    return float(1.4826 * np.median(np.abs(a - np.median(a)))) if len(a) else float("nan")


def speaker_pitch_range(snd: parselmouth.Sound, stable_floor: bool = False) -> tuple[float, float]:
    """Two-pass speaker-adaptive F0 search range (De Looze & Hirst 2008).

    With `stable_floor` the floor is also capped at 0.6 x the first-pass median. The plain
    0.75 x Q1 floor rises when part of a recording is flattened (Q1 moves towards the median),
    which silently deletes genuine low notes elsewhere in the same recording. Analysis uses the
    stable floor; the dataset generator keeps the original rule so the dataset rebuilds exactly.
    """
    p1 = _pitch(snd, 60.0, 700.0).selected_array["frequency"]
    p1 = p1[p1 > 0]
    if len(p1) <= 20:
        return 60.0, 500.0
    floor = 0.75 * np.percentile(p1, 25)
    if stable_floor:
        floor = min(floor, 0.6 * np.median(p1))
    return max(50.0, floor), min(800.0, 1.5 * np.percentile(p1, 75))


def extract_frames(y: np.ndarray, sr: int = SAMPLE_RATE) -> FrameFeatures:
    hop = int(HOP_S * sr)
    n_frames = 1 + len(y) // hop
    t = np.arange(n_frames) * HOP_S

    # --- F0 (two-pass speaker-adaptive range)
    snd = parselmouth.Sound(y.astype(np.float64), sampling_frequency=sr)
    floor, ceiling = speaker_pitch_range(snd, stable_floor=True)
    pitch = _pitch(snd, floor, ceiling)
    f0 = pitch.selected_array["frequency"].astype(float)
    f0[f0 <= 0] = np.nan
    f0 = _on_grid(pitch.xs(), f0, t)
    f0_median = float(np.nanmedian(f0)) if np.any(np.isfinite(f0)) else float("nan")
    f0_st = remove_octave_jumps(12 * np.log2(f0 / f0_median))
    f0[~np.isfinite(f0_st)] = np.nan

    # --- harmonicity
    harm = snd.to_harmonicity_cc(time_step=HOP_S, minimum_pitch=floor)
    hnr = harm.values[0].astype(float)
    hnr[hnr < -100] = np.nan  # Praat marks unvoiced frames with -200 dB
    hnr = _on_grid(harm.xs(), hnr, t)

    # --- energy (RMS) and FFT-based spectral features
    rms = librosa.feature.rms(y=y, frame_length=WIN, hop_length=hop, center=True)[0][:n_frames]
    energy = 20 * np.log10(rms + 1e-8)
    voiced = np.isfinite(f0[: len(energy)])
    level_ref = float(np.median(energy[voiced])) if voiced.sum() > 10 else float(np.median(energy))
    energy_db = np.pad(energy - level_ref, (0, n_frames - len(energy)), constant_values=-80.0)

    S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=hop, win_length=WIN, center=True)) ** 2
    S = S[:, :n_frames]
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    lo = (freqs >= 80) & (freqs < HF_SPLIT_HZ)
    hi = freqs >= HF_SPLIT_HZ
    hf_db = 10 * np.log10((S[hi].sum(0) + 1e-10) / (S[lo].sum(0) + 1e-10))
    air_lo = (freqs >= 80) & (freqs < AIR_SPLIT_HZ)
    air_db = 10 * np.log10((S[freqs >= AIR_SPLIT_HZ].sum(0) + 1e-10) / (S[air_lo].sum(0) + 1e-10))
    centroid = librosa.feature.spectral_centroid(S=np.sqrt(S), sr=sr)[0]
    logS = np.log(S + 1e-10)
    flux = np.r_[0.0, np.sqrt(np.sum(np.maximum(np.diff(logS, axis=1), 0) ** 2, axis=0))]

    mel = librosa.feature.melspectrogram(S=S, sr=sr, n_mels=40)
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(mel), n_mfcc=13).T
    mfcc = (mfcc - mfcc.mean(0)) / (mfcc.std(0) + 1e-8)

    def fit(a):
        return np.pad(a, (0, max(0, n_frames - len(a))), mode="edge")[:n_frames]

    return FrameFeatures(
        t=t,
        f0_hz=f0,
        f0_st=f0_st,
        energy_db=energy_db,
        hnr_db=hnr,
        hf_db=fit(hf_db),
        air_db=fit(air_db),
        centroid=fit(centroid),
        flux=fit(flux),
        mfcc=np.pad(mfcc, ((0, max(0, n_frames - len(mfcc))), (0, 0)), mode="edge")[:n_frames],
        f0_median_hz=f0_median,
        level_ref_db=level_ref,
        pitch_range_hz=(round(floor, 1), round(ceiling, 1)),
    )


# --------------------------------------------------------------------------- word level

_VOWEL_GROUPS = re.compile(r"[aeiouy]+")


def count_syllables(word: str) -> int:
    """Orthographic syllable estimate (vowel groups, silent final -e, -le endings)."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n = len(_VOWEL_GROUPS.findall(w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    return max(1, n)


def _nanstat(fn, a: np.ndarray) -> float:
    a = a[np.isfinite(a)]
    return float(fn(a)) if len(a) else float("nan")


def _speech_mean(track: np.ndarray, f0: np.ndarray, e: np.ndarray) -> float:
    """Mean of a spectral track over the frames of a word that carry speech (voiced or loud)."""
    keep = np.isfinite(f0) | (e > -20)
    return float(np.mean(track[keep])) if keep.any() else float("nan")


def word_features(ff: FrameFeatures, words: list[dict]) -> list[dict]:
    """Per-word acoustic summary; `gap_after` is the silence before the next word."""
    out = []
    for i, w in enumerate(words):
        s = ff.slice(w["start"], w["end"])
        f0 = ff.f0_st[s]
        voiced = np.isfinite(f0)
        e = ff.energy_db[s]
        out.append(
            {
                "word": w["word"],
                "start": w["start"],
                "end": w["end"],
                "duration": w["end"] - w["start"],
                "syllables": count_syllables(w["word"]),
                "gap_after": (words[i + 1]["start"] - w["end"]) if i + 1 < len(words) else 0.0,
                "f0_mean_st": _nanstat(np.mean, f0),
                "f0_range_st": _nanstat(lambda a: np.percentile(a, 90) - np.percentile(a, 10), f0),
                "voiced_frac": float(voiced.mean()) if len(f0) else 0.0,
                "energy_db": float(10 * np.log10(np.mean(10 ** (e / 10)) + 1e-12)),  # power mean
                "energy_peak_db": float(np.max(e)) if len(e) else float("nan"),
                "hnr_db": _nanstat(np.mean, ff.hnr_db[s]),
                "hf_db": _speech_mean(ff.hf_db[s], f0, e),
                "air_db": _speech_mean(ff.air_db[s], f0, e),
                "centroid": float(np.mean(ff.centroid[s])),
            }
        )
    return out


def global_summary(ff: FrameFeatures, wf: list[dict], pause_min: float = 0.25) -> dict:
    """Utterance-level delivery statistics (all speaker-normalised where applicable)."""
    if not wf:
        return {}
    total = wf[-1]["end"] - wf[0]["start"]
    speaking = sum(w["duration"] for w in wf)
    syll = sum(w["syllables"] for w in wf)
    pauses = [w["gap_after"] for w in wf[:-1] if w["gap_after"] >= pause_min]
    span = ff.slice(wf[0]["start"], wf[-1]["end"])
    f0 = ff.f0_st[span]
    f0 = f0[np.isfinite(f0)]
    e = ff.energy_db[span]
    voiced_e = e[np.isfinite(ff.f0_st[span])]
    return {
        "duration_s": round(total, 3),
        "words": len(wf),
        "speech_rate_wpm": round(60 * len(wf) / total, 1),
        "speech_rate_sps": round(syll / total, 3),
        "articulation_rate_sps": round(syll / speaking, 3),
        "pause_count": len(pauses),
        "pause_mean_s": round(float(np.mean(pauses)), 3) if pauses else 0.0,
        "pause_ratio": round(1 - speaking / total, 3),
        "f0_median_hz": round(ff.f0_median_hz, 1),
        "pitch_sd_st": round(float(np.std(f0)), 3) if len(f0) else 0.0,
        "pitch_range_st": round(float(np.percentile(f0, 95) - np.percentile(f0, 5)), 3) if len(f0) else 0.0,
        "energy_range_db": round(float(np.percentile(voiced_e, 95) - np.percentile(voiced_e, 10)), 3)
        if len(voiced_e)
        else 0.0,
        "hnr_mean_db": round(_nanstat(np.mean, ff.hnr_db[span]), 3),
        "hf_mean_db": round(float(np.nanmean([w["hf_db"] for w in wf])), 3),
    }
