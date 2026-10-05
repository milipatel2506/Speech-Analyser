"""Generate the flawed "bad mirror" spectrum for every prepared baseline.

Reads  dataset/labels/<id>/baseline.json + dataset/audio/baseline/<id>.wav
Writes dataset/audio/flawed/<id>/<clip>.wav
       dataset/labels/<id>/<clip>.json + <clip>.TextGrid
       dataset/manifest.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from speech_analyser.alignment import align  # noqa: E402
from speech_analyser.audio_io import load_audio, save_audio  # noqa: E402
from speech_analyser.flaws import Baseline, inject  # noqa: E402
from speech_analyser.flaws.plan import plan_variants, rng_for  # noqa: E402
from speech_analyser.textgrid import write_textgrid  # noqa: E402

DS = ROOT / "dataset"
GENERATOR_VERSION = "1.0"


def build_one(meta: dict, realign: bool, force: bool) -> tuple[int, int]:
    """Generate every flawed variant of one baseline. Returns (built, skipped)."""
    sid = meta["id"]
    y = load_audio(DS / meta["audio"], normalize=False)  # baseline is already normalised
    base = Baseline(y, meta["words"], meta["sample_rate"])
    built = skipped = 0

    for v in plan_variants(base, sid):
        lpath = DS / "labels" / sid / f"{v['clip_id']}.json"
        audio_rel = f"audio/flawed/{sid}/{v['clip_id']}.wav"
        if not force and _complete(lpath, DS / audio_rel, realign):
            skipped += 1  # generation is deterministic, so an existing clip is already correct
            continue
        res = inject(base, v["flaws"], rng_for(sid, v["clip_id"], "noise"))
        duration = round(len(res.audio) / base.sr, 4)
        save_audio(DS / audio_rel, res.audio, base.sr)

        label = {
            "clip_id": v["clip_id"],
            "baseline_id": sid,
            "kind": v["kind"],
            "level": v["level"],
            "generator_version": GENERATOR_VERSION,
            "audio": audio_rel,
            "baseline_audio": meta["audio"],
            "sample_rate": base.sr,
            "duration": duration,
            "transcript": meta["transcript"],
            "flaws": res.flaws,
            "words": res.words,  # exact, derived from the injection time map
            "time_map": res.time_map,
        }
        if realign:  # independent forced alignment of the flawed audio (what the detector sees)
            label["aligned_words"] = [w.to_dict() for w in align(res.audio, meta["transcript"])]
            err = [abs(a["start"] - w["start"]) for a, w in zip(label["aligned_words"], res.words)]
            label["alignment_error_ms"] = {
                "mean": round(1000 * sum(err) / max(len(err), 1), 1),
                "max": round(1000 * max(err, default=0.0), 1),
            }
        lpath.write_text(json.dumps(label, indent=1), encoding="utf-8")
        write_textgrid(
            lpath.with_suffix(".TextGrid"),
            duration,
            {
                "words": [(w["start"], w["end"], w["word"]) for w in res.words],
                "flaws": [(f["start"], f["end"], f"{f['type']}:s{f['severity']}") for f in res.flaws],
            },
        )
        built += 1
    return built, skipped


def _complete(lpath: Path, wav: Path, realign: bool) -> bool:
    if not (lpath.exists() and wav.exists()):
        return False
    return not realign or "aligned_words" in json.loads(lpath.read_text(encoding="utf-8"))


def write_manifest() -> int:
    """One row per clip, rebuilt from every label file on disk (baselines, flawed and self-recorded)."""
    rows = []
    for p in sorted((DS / "labels").glob("*/*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        is_base = p.name == "baseline.json"
        rows.append(
            {
                "clip_id": f"{d['id']}__baseline" if is_base else d["clip_id"],
                "baseline_id": d["id"] if is_base else d["baseline_id"],
                "kind": "baseline" if is_base else d["kind"],
                "level": 0 if is_base else d.get("level"),
                "n_flaws": 0 if is_base else len(d["flaws"]),
                "flaw_types": "" if is_base else ";".join(f["type"] for f in d["flaws"]),
                "duration": d["duration"],
                "audio": d["audio"],
                "labels": p.relative_to(DS).as_posix(),
            }
        )
    with open(DS / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--no-align", action="store_true", help="skip forced alignment of flawed clips (fast)")
    ap.add_argument("--force", action="store_true", help="regenerate clips that already exist")
    args = ap.parse_args()

    for mpath in sorted((DS / "labels").glob("*/baseline.json")):
        meta = json.loads(mpath.read_text(encoding="utf-8"))
        if args.ids and meta["id"] not in args.ids:
            continue
        built, skipped = build_one(meta, realign=not args.no_align, force=args.force)
        print(f"[ok  ] {meta['id']}: {built} built, {skipped} already complete", flush=True)

    print(f"[done] {write_manifest()} clips -> dataset/manifest.csv")


if __name__ == "__main__":
    main()
