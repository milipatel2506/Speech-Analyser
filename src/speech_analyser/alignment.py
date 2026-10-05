"""Forced alignment of a known transcript to audio.

Uses torchaudio's MMS_FA bundle (wav2vec2 CTC acoustic model trained for multilingual forced
alignment) with CTC Viterbi alignment. Output is one entry per transcript word with start/end in
seconds and a confidence score in [0, 1].
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from functools import lru_cache

import numpy as np
import torch
import torchaudio

from .audio_io import SAMPLE_RATE

# Emission is computed in windows to bound memory on CPU (self-attention is quadratic in length).
_CHUNK_S = 20.0
_CONTEXT_S = 1.0


@dataclass
class Word:
    word: str  # word as written in the transcript (punctuation stripped)
    start: float
    end: float
    score: float

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def tokenize_transcript(text: str) -> list[str]:
    """Split a transcript into display words (keeps apostrophes and hyphenated words intact)."""
    return [w for w in re.findall(r"[\w'’\-]+", text) if re.search(r"\w", w)]


def normalize_word(word: str) -> str:
    """Map a display word to the MMS_FA alphabet (lowercase a-z and apostrophe)."""
    w = unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode()
    w = w.lower().replace("’", "'")
    return re.sub(r"[^a-z']", "", w)


@lru_cache(maxsize=1)
def _bundle():
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model(with_star=False).eval()
    return bundle, model, bundle.get_tokenizer(), bundle.get_aligner()


def _emission(model, y: np.ndarray, sr: int) -> torch.Tensor:
    """Frame-level log-probabilities for the whole signal, computed chunk-wise with context."""
    wav = torch.from_numpy(y).float().unsqueeze(0)
    chunk, ctx = int(_CHUNK_S * sr), int(_CONTEXT_S * sr)
    if wav.shape[1] <= chunk + 2 * ctx:
        with torch.inference_mode():
            return model(wav)[0][0]

    parts = []
    for a in range(0, wav.shape[1], chunk):
        b = min(a + chunk, wav.shape[1])
        lo, hi = max(0, a - ctx), min(wav.shape[1], b + ctx)
        with torch.inference_mode():
            em = model(wav[:, lo:hi])[0][0]
        frames_per_sample = em.shape[0] / (hi - lo)
        keep_from = int(round((a - lo) * frames_per_sample))
        keep_to = keep_from + int(round((b - a) * frames_per_sample))
        parts.append(em[keep_from:keep_to])
    return torch.cat(parts, dim=0)


def align(y: np.ndarray, transcript: str, sr: int = SAMPLE_RATE) -> list[Word]:
    """Align `transcript` to audio `y` (mono, `sr` Hz). Returns one Word per alignable token."""
    bundle, model, tokenizer, aligner = _bundle()
    if sr != bundle.sample_rate:
        raise ValueError(f"expected {bundle.sample_rate} Hz audio, got {sr}")

    display = tokenize_transcript(transcript)
    pairs = [(d, normalize_word(d)) for d in display]
    pairs = [(d, n) for d, n in pairs if n]
    if not pairs:
        return []

    emission = _emission(model, y, sr)
    spans = aligner(emission, tokenizer([n for _, n in pairs]))
    sec_per_frame = len(y) / sr / emission.shape[0]

    words = []
    for (disp, _), token_spans in zip(pairs, spans):
        n_frames = sum(len(s) for s in token_spans)
        score = sum(s.score * len(s) for s in token_spans) / max(n_frames, 1)
        words.append(
            Word(
                word=disp,
                start=token_spans[0].start * sec_per_frame,
                end=token_spans[-1].end * sec_per_frame,
                score=float(score),
            )
        )
    return words
