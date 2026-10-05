"""Audio loading, normalisation and saving.

Every audio file entering the pipeline goes through `load_audio`, so all downstream code can assume
16 kHz mono float32 at a fixed integrated loudness.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf

SAMPLE_RATE = 16_000
TARGET_LUFS = -23.0  # EBU R128 broadcast reference level


def load_audio(
    path: str | Path,
    sr: int = SAMPLE_RATE,
    normalize: bool = True,
    offset: float = 0.0,
    duration: float | None = None,
) -> np.ndarray:
    """Load an audio file as mono float32 at `sr`, optionally loudness-normalised."""
    y, _ = librosa.load(str(path), sr=sr, mono=True, offset=offset, duration=duration)
    y = y.astype(np.float32)
    return loudness_normalize(y, sr) if normalize else y


def decode_any(path: str | Path, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Decode any container ffmpeg understands (webm/opus from browsers, m4a, mp4...) to mono `sr`."""
    try:
        return load_audio(path, sr=sr, normalize=False)
    except Exception:
        out = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
            capture_output=True,
            check=True,
        ).stdout
        return np.frombuffer(out, dtype=np.float32).copy()


def loudness_normalize(y: np.ndarray, sr: int = SAMPLE_RATE, target: float = TARGET_LUFS) -> np.ndarray:
    """Scale to `target` integrated loudness (ITU-R BS.1770), then guard against clipping."""
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(y)
    if not np.isfinite(loudness):  # silent input
        return y
    out = pyln.normalize.loudness(y, loudness, target)
    peak = np.max(np.abs(out))
    if peak > 0.99:
        out = out * (0.99 / peak)
    return out.astype(np.float32)


def save_audio(path: str | Path, y: np.ndarray, sr: int = SAMPLE_RATE) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(y, -1.0, 1.0), sr, subtype="PCM_16")


def trim(y: np.ndarray, start: float | None, end: float | None, sr: int = SAMPLE_RATE) -> np.ndarray:
    a = 0 if start is None else int(round(start * sr))
    b = len(y) if end is None else int(round(end * sr))
    return y[a:b]
