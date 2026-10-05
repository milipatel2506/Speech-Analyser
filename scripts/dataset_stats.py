"""Summary statistics of the built dataset (used in dataset/README.md and the technical report).

Writes docs/results/dataset_stats.json and prints Markdown tables.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "dataset"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    baselines, clips = [], []
    for p in sorted((DS / "labels").glob("*/*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        (baselines if p.name == "baseline.json" else clips).append(d)

    flaw_counts = Counter(f["type"] for c in clips for f in c["flaws"])
    align_err = defaultdict(list)
    for c in clips:
        if "alignment_error_ms" in c:
            key = c["flaws"][0]["type"] if c["kind"] == "single" and c["flaws"] else c["kind"]
            align_err[key].append(c["alignment_error_ms"]["mean"])
    all_err = [e for v in align_err.values() for e in v]

    stats = {
        "baselines": len(baselines),
        "speakers": {"M": sum(b["sex"] == "M" for b in baselines), "F": sum(b["sex"] == "F" for b in baselines)},
        "flawed_clips": len(clips),
        "single_flaw_clips": sum(c["kind"] == "single" for c in clips),
        "mix_clips": sum(c["kind"] == "mix" for c in clips),
        "labelled_flaw_regions": sum(flaw_counts.values()),
        "flaw_regions_by_type": dict(flaw_counts),
        "baseline_audio_min": round(sum(b["duration"] for b in baselines) / 60, 2),
        "total_audio_min": round((sum(b["duration"] for b in baselines) + sum(c["duration"] for c in clips)) / 60, 2),
        "baseline_words": sum(len(b["words"]) for b in baselines),
        "baseline_alignment_mean_score": round(float(np.mean([b["alignment"]["mean_score"] for b in baselines])), 3),
        "flawed_alignment_error_ms": {
            "mean": round(float(np.mean(all_err)), 1) if all_err else None,
            "p95": round(float(np.percentile(all_err, 95)), 1) if all_err else None,
            "by_type": {k: round(float(np.mean(v)), 1) for k, v in sorted(align_err.items())},
        },
    }
    out = ROOT / "docs" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "dataset_stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")

    print("| Baseline | Speaker | Year | Duration | Words | Align score |")
    print("|---|---|---|---|---|---|")
    for b in baselines:
        print(f"| `{b['id']}` | {b['speaker']} ({b['sex']}) | {b['year']} | {b['duration']:.1f} s | {len(b['words'])} | {b['alignment']['mean_score']:.2f} |")
    print()
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
