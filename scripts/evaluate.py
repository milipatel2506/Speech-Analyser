"""Stress-test the detector against the dataset's exact injection labels.

For every flawed clip: realign the flawed audio from scratch (full pipeline, no label leakage),
compare it with its baseline, and match predicted regions to ground-truth flaws.

A prediction matches a ground-truth flaw when both have the same flaw type and their temporal
IoU >= --iou. Reported per flaw type and severity:
  recall            fraction of injected flaws detected
  IoU               mean temporal intersection-over-union of matched pairs
  onset/offset err  mean |start/end error| in ms of matched pairs
  severity MAE      mean |predicted - true severity|
plus false positives per minute, and Spearman correlation between quality level and overall score.

Writes docs/results/evaluation.json and docs/results/evaluation.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from speech_analyser.audio_io import load_audio  # noqa: E402
from speech_analyser.flaws.spec import FLAWS  # noqa: E402
from speech_analyser.pipeline import analyse_recording, report  # noqa: E402

DS = ROOT / "dataset"
OUT = ROOT / "docs" / "results"
TUNING_SET = {"fdr_1933", "clinton_1995"}  # detector thresholds were set on these; the rest are held out


def iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def match(gt: list[dict], pred: list[dict], thr: float) -> tuple[list[tuple[dict, dict | None]], list[dict]]:
    """Greedy one-to-one matching by IoU within the same flaw type."""
    used, pairs = set(), []
    for g in gt:
        best, best_iou = None, thr
        for k, p in enumerate(pred):
            if k in used or p["type"] != g["type"]:
                continue
            v = iou((g["start"], g["end"]), (p["start"], p["end"]))
            if v >= best_iou:
                best, best_iou = k, v
        if best is not None:
            used.add(best)
        pairs.append((g, pred[best] if best is not None else None))
    return pairs, [p for k, p in enumerate(pred) if k not in used]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--iou", type=float, default=0.3)
    ap.add_argument("--oracle-alignment", action="store_true", help="use label word timings instead of realigning")
    args = ap.parse_args()

    clips = defaultdict(list)
    for lpath in sorted((DS / "labels").glob("*/*.json")):
        if lpath.name == "baseline.json":
            continue
        lab = json.loads(lpath.read_text(encoding="utf-8"))
        if not args.ids or lab["baseline_id"] in args.ids:
            clips[lab["baseline_id"]].append(lab)

    def cell():
        return {"n": 0, "hit": 0, "iou": [], "on": [], "off": [], "sev": []}

    per = defaultdict(cell)  # (type, severity) -> synthetic results
    per_base = defaultdict(cell)  # baseline id -> synthetic results
    fp_base, minutes_base = defaultdict(int), defaultdict(float)
    per_self = defaultdict(cell)  # type -> self-recorded (human-performed) results
    fp, minutes, levels, scores, single = [], 0.0, [], [], defaultdict(list)
    fp_self, minutes_self, self_scores = [], 0.0, defaultdict(list)
    t0 = time.time()
    for sid, labs in clips.items():
        meta = json.loads((DS / "labels" / sid / "baseline.json").read_text(encoding="utf-8"))
        base = analyse_recording(load_audio(DS / meta["audio"], normalize=False), meta["transcript"], meta["words"])
        for lab in labs:
            y = load_audio(DS / lab["audio"], normalize=False)
            # default: the aligner's own output for this audio (cached at build time); never the labels
            words = lab["words"] if args.oracle_alignment else lab.get("aligned_words")
            part = analyse_recording(y, lab["transcript"], words)
            rep = report(base, part)
            pairs, extra = match(lab["flaws"], rep["flaws"], args.iou)
            is_self = lab["kind"] == "self"
            for g, p in pairs:
                cells = [per_self[g["type"]]] if is_self else [per[(g["type"], g["severity"])], per_base[sid]]
                for s in cells:
                    s["n"] += 1
                    if p is not None:
                        s["hit"] += 1
                        s["iou"].append(iou((g["start"], g["end"]), (p["start"], p["end"])))
                        s["on"].append(abs(p["start"] - g["start"]) * 1000)
                        s["off"].append(abs(p["end"] - g["end"]) * 1000)
                        if g["severity"] is not None:
                            s["sev"].append(abs(p["severity"] - g["severity"]))
            extra_rows = [{"clip": lab["clip_id"], "type": p["type"], "start": p["start"], "end": p["end"]} for p in extra]
            if is_self:
                fp_self += extra_rows
                minutes_self += lab["duration"] / 60
                self_scores[lab["take"]].append(rep["score"]["overall"])
            else:
                fp += extra_rows
                minutes += lab["duration"] / 60
                fp_base[sid] += len(extra_rows)
                minutes_base[sid] += lab["duration"] / 60
                if lab["kind"] == "mix":
                    levels.append(lab["level"])
                    scores.append(rep["score"]["overall"])
                else:
                    single[lab["flaws"][0]["type"]].append((lab["level"], rep["score"]["overall"]))
            print(
                f"{lab['clip_id']:<34} gt={len(lab['flaws'])} pred={len(rep['flaws'])} "
                f"hit={sum(p is not None for _, p in pairs)} score={rep['score']['overall']:.1f}",
                flush=True,
            )

    def agg(rows):
        n = sum(r["n"] for r in rows)
        hit = sum(r["hit"] for r in rows)
        cat = lambda k: [v for r in rows for v in r[k]]  # noqa: E731
        mean = lambda a: round(float(np.mean(a)), 3) if a else None  # noqa: E731
        return {
            "n": n,
            "recall": round(hit / n, 3) if n else None,
            "iou": mean(cat("iou")),
            "onset_err_ms": mean(cat("on")),
            "offset_err_ms": mean(cat("off")),
            "severity_mae": mean(cat("sev")),
        }

    by_type = {t: {sev: agg([per[(t, sev)]]) for sev in range(1, 6)} | {"all": agg([per[(t, s)] for s in range(1, 6)])} for t in FLAWS}
    rho = spearmanr(levels, scores).statistic if len(set(levels)) > 1 else None
    single_rho = {t: round(float(spearmanr(*zip(*v)).statistic), 3) for t, v in single.items() if len(v) > 2}
    result = {
        "settings": {"iou_threshold": args.iou, "oracle_alignment": args.oracle_alignment, "baselines": list(clips)},
        "overall": agg(list(per.values())),
        "by_type": by_type,
        "by_baseline": {
            b: agg([v]) | {"fp_per_minute": round(fp_base[b] / max(minutes_base[b], 1e-9), 3), "tuning_set": b in TUNING_SET}
            for b, v in per_base.items()
        },
        "false_positives": {"count": len(fp), "per_minute": round(len(fp) / max(minutes, 1e-9), 3), "items": fp},
        "score_vs_level_spearman": {"mix": None if rho is None else round(float(rho), 3), "single": single_rho},
        "self_recorded": {
            "by_type": {t: agg([v]) for t, v in per_self.items()},
            "overall": agg(list(per_self.values())) if per_self else None,
            "false_positives_per_minute": round(len(fp_self) / minutes_self, 3) if minutes_self else None,
            "mean_score_by_take": {k: round(float(np.mean(v)), 1) for k, v in self_scores.items()},
            "minutes": round(minutes_self, 2),
            "false_positive_items": fp_self,
        },
        "runtime_s": round(time.time() - t0, 1),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "evaluation.json").write_text(json.dumps(result, indent=1), encoding="utf-8")

    lines = [
        f"# Detector evaluation (IoU ≥ {args.iou}, {'oracle' if args.oracle_alignment else 'full re-alignment'})",
        "",
        "| Flaw | Sev 1 | Sev 2 | Sev 3 | Sev 4 | Sev 5 | Recall | IoU | Onset err (ms) | Offset err (ms) | Severity MAE |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t, d in by_type.items():
        cells = [f"{d[s]['recall']:.0%}" if d[s]["recall"] is not None else "–" for s in range(1, 6)]
        a = d["all"]
        fmt = lambda v, f: "–" if v is None else format(v, f)  # noqa: E731
        lines.append(
            f"| {FLAWS[t].label} | " + " | ".join(cells)
            + f" | {fmt(a['recall'], '.0%')} | {fmt(a['iou'], '.2f')} | {fmt(a['onset_err_ms'], '.0f')} | {fmt(a['offset_err_ms'], '.0f')} | {fmt(a['severity_mae'], '.2f')} |"
        )
    o = result["overall"]
    lines += [
        "",
        f"**Overall:** recall {o['recall']:.0%}, mean IoU {o['iou']:.2f}, onset error {o['onset_err_ms']:.0f} ms, "
        f"offset error {o['offset_err_ms']:.0f} ms, false positives {result['false_positives']['per_minute']:.2f}/min.",
        "",
        f"**Score vs quality level (Spearman ρ):** mix clips {result['score_vs_level_spearman']['mix']}, "
        + ", ".join(f"{FLAWS[t].label} {v}" for t, v in single_rho.items()),
        "",
        "| Baseline | Set | Recall | IoU | Onset err (ms) | Offset err (ms) | False pos./min |",
        "|---|---|---|---|---|---|---|",
    ]
    for b, d in result["by_baseline"].items():
        lines.append(
            f"| `{b}` | {'tuning' if d['tuning_set'] else 'held-out'} | {d['recall']:.0%} | {d['iou']:.2f} | "
            f"{d['onset_err_ms']:.0f} | {d['offset_err_ms']:.0f} | {d['fp_per_minute']:.2f} |"
        )
    held = [v for b, v in per_base.items() if b not in TUNING_SET]
    if held:
        h = agg(held)
        fp_h = sum(fp_base[b] for b in per_base if b not in TUNING_SET)
        min_h = sum(minutes_base[b] for b in per_base if b not in TUNING_SET)
        lines += ["", f"**Held-out speeches only:** recall {h['recall']:.0%}, IoU {h['iou']:.2f}, false positives {fp_h / min_h:.2f}/min."]
    (OUT / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
