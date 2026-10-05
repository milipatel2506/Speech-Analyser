"""Cut, normalise, transcribe and force-align the "good" baseline excerpts.

For every row in dataset/sources.csv with excerpt_start/excerpt_end filled in:
  dataset/raw/<id>.*               -> dataset/audio/baseline/<id>.wav  (16 kHz mono, -23 LUFS)
  dataset/transcripts/<id>.txt     (Whisper draft on first run; hand-correct it, then re-run)
  dataset/labels/<id>/baseline.json + baseline.TextGrid  (word-level forced alignment)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from speech_analyser.alignment import align  # noqa: E402
from speech_analyser.audio_io import SAMPLE_RATE, load_audio, save_audio  # noqa: E402
from speech_analyser.textgrid import write_textgrid  # noqa: E402

DS = ROOT / "dataset"
LOW_CONFIDENCE = 0.5
AUDIO_EXTS = {".ogg", ".opus", ".mp3", ".wav", ".flac", ".m4a"}
SNAP_WINDOW_S = 1.5


def snap_to_pause(raw: Path, t: float, window: float = SNAP_WINDOW_S) -> float:
    """Move a cut point to the quietest 200 ms within +-window seconds, so no word is split."""
    lo = max(0.0, t - window)
    y = load_audio(raw, offset=lo, duration=2 * window, normalize=False)
    hop = int(0.01 * SAMPLE_RATE)
    rms = np.sqrt(np.convolve(y**2, np.ones(hop) / hop, mode="same"))[::hop]
    smooth = np.convolve(rms, np.ones(20) / 20, mode="same")
    margin = 10  # ignore frames whose smoothing window falls off the edge
    i = margin + int(np.argmin(smooth[margin:-margin]))
    return round(lo + i * 0.01, 2)


def draft_transcript(wav: Path, model_name: str) -> str:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(wav), language="en", beam_size=5)
    return " ".join(s.text.strip() for s in segments)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--asr-model", default="small.en")
    args = ap.parse_args()

    with open(DS / "sources.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["excerpt_start"] and r["excerpt_end"]]

    for row in rows:
        sid = row["id"]
        if args.ids and sid not in args.ids:
            continue
        raw = next((p for p in (DS / "raw").glob(f"{sid}.*") if p.suffix in AUDIO_EXTS), None)
        if raw is None:
            print(f"[miss] {sid}: run scripts/fetch_sources.py first")
            continue

        start = snap_to_pause(raw, float(row["excerpt_start"])) if float(row["excerpt_start"]) > 0 else 0.0
        end = snap_to_pause(raw, float(row["excerpt_end"]))
        y = load_audio(raw, offset=start, duration=end - start)
        wav = DS / "audio" / "baseline" / f"{sid}.wav"
        save_audio(wav, y)

        tpath = DS / "transcripts" / f"{sid}.txt"
        if not tpath.exists():
            tpath.parent.mkdir(parents=True, exist_ok=True)
            tpath.write_text(draft_transcript(wav, args.asr_model) + "\n", encoding="utf-8")
            print(f"[asr ] {sid}: draft transcript written -> review {tpath.relative_to(ROOT)}")
        transcript = tpath.read_text(encoding="utf-8").strip()

        words = [w.to_dict() for w in align(y, transcript)]
        duration = len(y) / SAMPLE_RATE
        low = [w for w in words if w["score"] < LOW_CONFIDENCE]
        out = DS / "labels" / sid
        out.mkdir(parents=True, exist_ok=True)
        meta = {
            "id": sid,
            "speaker": row["speaker"],
            "sex": row["sex"],
            "title": row["title"],
            "year": int(row["year"]),
            "source_url": row["url"],
            "license": row["license"],
            "excerpt": [start, end],
            "audio": f"audio/baseline/{sid}.wav",
            "sample_rate": SAMPLE_RATE,
            "duration": round(duration, 4),
            "transcript": transcript,
            "alignment": {
                "method": "torchaudio MMS_FA (wav2vec2 CTC) Viterbi forced alignment",
                "mean_score": round(sum(w["score"] for w in words) / max(len(words), 1), 4),
                "low_confidence_words": len(low),
            },
            "words": words,
        }
        (out / "baseline.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        write_textgrid(out / "baseline.TextGrid", duration, {"words": [(w["start"], w["end"], w["word"]) for w in words]})
        print(
            f"[ok  ] {sid}: {duration:5.1f}s, {len(words)} words, "
            f"mean align score {meta['alignment']['mean_score']:.2f}, {len(low)} low-confidence"
        )


if __name__ == "__main__":
    main()
