"""Import a self-recorded reading of a baseline transcript into the dataset.

  uv run python scripts/import_recording.py --baseline jfk_1961 --speaker mp --take A  take_A.m4a

* decodes any audio format, normalises loudness, force-aligns the baseline transcript
* takes `good`  -> no flaws (cross-speaker control; any detection is a false positive)
* takes `A`/`B` -> flaw regions from the directed spans in dataset/recording_kit/<id>.json,
                   bounded by the forced-aligned words of *this* recording
* --textgrid    -> override with hand-checked labels: a Praat tier named "flaws" whose interval
                   texts are "<type>" or "<type>:<severity>"

Writes dataset/audio/self/<id>/<clip>.wav and dataset/labels/<id>/<clip>.json (+ .TextGrid), where
clip = <id>__self_<speaker>_<take>. The importer also writes a TextGrid for review in Praat.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from speech_analyser.alignment import align  # noqa: E402
from speech_analyser.audio_io import SAMPLE_RATE, decode_any, loudness_normalize, save_audio  # noqa: E402
from speech_analyser.flaws.spec import FLAWS  # noqa: E402
from speech_analyser.textgrid import write_textgrid  # noqa: E402

DS = ROOT / "dataset"


def read_flaw_tier(path: Path) -> list[tuple[float, float, str]]:
    """Intervals of the tier named 'flaws' from a long-format Praat TextGrid."""
    text = path.read_text(encoding="utf-8", errors="replace")
    for block in re.split(r"item \[\d+\]:", text)[1:]:
        if re.search(r'name = "flaws"', block):
            ivs = re.findall(r"xmin = ([\d.]+)\s+xmax = ([\d.]+)\s+text = \"(.*?)\"", block, flags=re.S)
            return [(float(a), float(b), t.strip()) for a, b, t in ivs if t.strip()]
    raise ValueError(f"no 'flaws' tier in {path}")


def span_of(words: list[dict], t0: float, t1: float) -> list[int]:
    idx = [i for i, w in enumerate(words) if w["end"] > t0 and w["start"] < t1]
    return [idx[0], idx[-1]] if idx else [0, 0]


def flaw_entry(ftype: str, sev: int | None, start: float, end: float, span: list[int], words: list[dict], source: str) -> dict:
    spec = FLAWS[ftype]
    return {
        "type": ftype,
        "label": spec.label,
        "rubric": spec.rubric,
        "severity": sev,  # None = performed by a human, physical size not controlled
        "start": round(start, 4),
        "end": round(end, 4),
        "word_span": span,
        "text": " ".join(w["word"] for w in words[span[0] : span[1] + 1]),
        "params": {},
        "description": f"Self-performed {spec.label.lower()} ({source})",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", type=Path)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--speaker", required=True, help="short anonymous speaker id, e.g. initials")
    ap.add_argument("--take", required=True, help="good, A or B (see docs/recording_kit)")
    ap.add_argument("--textgrid", type=Path, help="hand-checked labels (tier 'flaws')")
    args = ap.parse_args()

    meta = json.loads((DS / "labels" / args.baseline / "baseline.json").read_text(encoding="utf-8"))
    clip_id = f"{args.baseline}__self_{args.speaker}_{args.take}"
    y = loudness_normalize(decode_any(args.audio))
    audio_rel = f"audio/self/{args.baseline}/{clip_id}.wav"
    save_audio(DS / audio_rel, y)
    words = [w.to_dict() for w in align(y, meta["transcript"])]

    flaws = []
    if args.textgrid:
        for t0, t1, label in read_flaw_tier(args.textgrid):
            ftype, _, sev = label.partition(":")
            flaws.append(flaw_entry(ftype, int(sev) if sev else None, t0, t1, span_of(words, t0, t1), words, "hand-labelled"))
    elif args.take != "good":
        kit = json.loads((DS / "recording_kit" / f"{args.baseline}.json").read_text(encoding="utf-8"))
        for d in kit["scripts"][args.take]:
            a, b = d["w0"], d["w1"]
            if d["type"] == "long_pause":
                start, end = words[a]["end"], words[b]["start"]
            else:  # spans, and pause_removal's run-on join, are bounded by the words themselves
                start, end = words[a]["start"], words[b]["end"]
            flaws.append(flaw_entry(d["type"], None, start, end, [a, b], words, "directed script"))

    duration = round(len(y) / SAMPLE_RATE, 4)
    label = {
        "clip_id": clip_id,
        "baseline_id": args.baseline,
        "kind": "self",
        "level": 0 if args.take == "good" else None,
        "speaker": args.speaker,
        "take": args.take,
        "audio": audio_rel,
        "baseline_audio": meta["audio"],
        "sample_rate": SAMPLE_RATE,
        "duration": duration,
        "transcript": meta["transcript"],
        "flaws": flaws,
        "words": words,
        "aligned_words": words,
    }
    lpath = DS / "labels" / args.baseline / f"{clip_id}.json"
    lpath.write_text(json.dumps(label, indent=1), encoding="utf-8")
    write_textgrid(
        lpath.with_suffix(".TextGrid"),
        duration,
        {
            "words": [(w["start"], w["end"], w["word"]) for w in words],
            "flaws": [(f["start"], f["end"], f["type"]) for f in flaws],
        },
    )
    low = sum(w["score"] < 0.5 for w in words)
    print(f"[ok  ] {clip_id}: {duration:.1f}s, {len(words)} words ({low} low-confidence), {len(flaws)} flaw labels")
    print(f"       review in Praat: {lpath.with_suffix('.TextGrid').relative_to(ROOT)} + {audio_rel}")


if __name__ == "__main__":
    main()
