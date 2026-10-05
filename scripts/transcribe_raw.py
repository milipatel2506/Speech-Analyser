"""Transcribe raw source speeches with timestamps to help choose clean excerpts.

Writes dataset/raw/<id>.segments.json (Whisper segments with start/end/text). This is a scouting
step only; final baseline transcripts are produced per excerpt by prepare_baseline.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "dataset" / "raw"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="base.en")
    ap.add_argument("ids", nargs="*", help="source ids (default: all raw files)")
    args = ap.parse_args()

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    files = [p for p in sorted(RAW.iterdir()) if p.suffix in {".ogg", ".opus", ".mp3", ".wav", ".flac"}]
    for path in files:
        if args.ids and path.stem not in args.ids:
            continue
        out = RAW / f"{path.stem}.segments.json"
        if out.exists():
            print(f"[skip] {path.stem}")
            continue
        print(f"[asr ] {path.stem}", flush=True)
        segments, _ = model.transcribe(str(path), language="en", beam_size=5, vad_filter=False)
        rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
        out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
