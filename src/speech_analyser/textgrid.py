"""Minimal Praat TextGrid writer (long text format), so labels open directly in Praat."""

from __future__ import annotations

from pathlib import Path


def _tier(name: str, intervals: list[tuple[float, float, str]], xmax: float) -> list[str]:
    # Fill gaps with empty intervals so the tier covers [0, xmax] contiguously, as Praat requires.
    filled, t = [], 0.0
    for a, b, text in sorted(intervals):
        a, b = max(a, t), min(b, xmax)
        if b <= a:
            continue
        if a > t:
            filled.append((t, a, ""))
        filled.append((a, b, text))
        t = b
    if t < xmax:
        filled.append((t, xmax, ""))

    lines = [
        '        class = "IntervalTier"',
        f'        name = "{name}"',
        "        xmin = 0",
        f"        xmax = {xmax}",
        f"        intervals: size = {len(filled)}",
    ]
    for i, (a, b, text) in enumerate(filled, 1):
        text = text.replace('"', '""')
        lines += [f"        intervals [{i}]:", f"            xmin = {a}", f"            xmax = {b}", f'            text = "{text}"']
    return lines


def write_textgrid(path: str | Path, duration: float, tiers: dict[str, list[tuple[float, float, str]]]) -> None:
    lines = [
        'File type = "ooTextFile"',
        'Object class = "TextGrid"',
        "",
        "xmin = 0",
        f"xmax = {duration}",
        "tiers? <exists>",
        f"size = {len(tiers)}",
        "item []:",
    ]
    for i, (name, intervals) in enumerate(tiers.items(), 1):
        lines.append(f"    item [{i}]:")
        lines += _tier(name, intervals, duration)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
