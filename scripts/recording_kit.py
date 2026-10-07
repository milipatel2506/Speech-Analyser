"""Generate directed reading scripts for self-recorded flawed deliveries.

For every baseline, writes dataset/recording_kit/<id>.json (machine-readable directions) and
docs/recording_kit/<id>.md (what the reader sees). Each kit has:

  good  - read naturally, as well as you can (cross-speaker control: should score high)
  A, B  - read naturally *except* inside the marked spans, where you perform the named flaw

Directed spans are chosen with the same deterministic planner as the synthetic dataset, so labels
for a recording come from its forced alignment: the flaw region is the aligned onset of the first
marked word to the offset of the last (see scripts/import_recording.py).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from speech_analyser.alignment import normalize_word  # noqa: E402
from speech_analyser.audio_io import load_audio  # noqa: E402
from speech_analyser.flaws import Baseline  # noqa: E402
from speech_analyser.flaws.plan import place, rng_for  # noqa: E402

DS = ROOT / "dataset"
SCRIPTS = {"A": ["rushing", "long_pause", "monotone"], "B": ["volume_drop", "dragging", "pause_removal", "mumble"]}

CUES = {
    "rushing": ("RUSH", "Speed through this part noticeably faster than the rest, without stopping."),
    "dragging": ("DRAG", "Slow right down here: stretch the words and lose momentum."),
    "monotone": ("FLAT", "Say this on one flat note, with no rise or fall in pitch, like reading a list."),
    "volume_drop": ("QUIET", "Drop your volume sharply here, as if trailing off, then recover after."),
    "mumble": ("MUMBLE", "Barely move your lips or jaw here; soften every consonant."),
    "long_pause": ("PAUSE", "Stop mid-phrase here for about 1–2 seconds, as if you lost your place."),
    "pause_removal": ("NO-PAUSE", "Do NOT pause at this boundary; run straight into the next words."),
}


POINT_FLAWS = ("long_pause", "pause_removal")  # cue sits at the boundary after word w0


def mark(transcript: str, flaws) -> str:
    """Punctuated transcript with ⟦CUE⟧ … ⟦/CUE⟧ around span flaws and ⟦CUE⟧ at pause boundaries.

    Word k here is the k-th alignable token, exactly as numbered by speech_analyser.alignment."""
    by_start = {f.w0: f for f in flaws}
    by_end = {f.w1: f for f in flaws if f.type not in POINT_FLAWS}
    out, cursor, k = [], 0, 0
    for m in re.finditer(r"[\w'’\-]+", transcript):
        if not re.search(r"\w", m.group()) or not normalize_word(m.group()):
            continue
        out.append(transcript[cursor : m.start()])
        tok = m.group()
        if (f := by_start.get(k)) is not None:
            tok = f"{tok} ⟦{CUES[f.type][0]}⟧" if f.type in POINT_FLAWS else f"⟦{CUES[f.type][0]}⟧ {tok}"
        if (g := by_end.get(k)) is not None:
            tok = f"{tok} ⟦/{CUES[g.type][0]}⟧"
        out.append(tok)
        cursor, k = m.end(), k + 1
    out.append(transcript[cursor:])
    return "".join(out)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    (DS / "recording_kit").mkdir(exist_ok=True)
    md_dir = ROOT / "docs" / "recording_kit"
    md_dir.mkdir(parents=True, exist_ok=True)
    for mpath in sorted((DS / "labels").glob("*/baseline.json")):
        meta = json.loads(mpath.read_text(encoding="utf-8"))
        sid = meta["id"]
        base = Baseline(load_audio(DS / meta["audio"], normalize=False), meta["words"], meta["sample_rate"])
        kit = {"baseline_id": sid, "scripts": {"good": []}}
        md = [f"# Recording kit: {meta['speaker']}, {meta['title']} ({meta['year']})", ""]
        md += [
            "Record in a quiet room, phone or laptop mic ~20 cm from your mouth. Start recording, stay silent for "
            "1 second, read the text, stay silent for 1 second, stop. **Say nothing except the text**: no take name, "
            "no \"okay\". Forced alignment expects exactly these words, so extra speech shifts every timestamp. "
            "Any format works (M4A, WAV, MP3, WebM).",
            "",
            f"Save each take as `recordings/{sid.split('_')[0]}_<take>_<your initials>.<ext>` "
            f"(e.g. `recordings/{sid.split('_')[0]}_A_mp.m4a`), then run "
            "`uv run python scripts/import_recordings.py`.",
            "",
            "## Take `good`: read naturally, as well as you can",
            "",
            f"> {meta['transcript']}",
            "",
        ]
        for name, types in SCRIPTS.items():
            occupied: set[int] = set()
            flaws = []
            rng = rng_for(sid, "kit", name)
            for t in types:
                f = place(base, t, 4, rng, occupied)
                if f is not None:
                    flaws.append(f)
            flaws.sort(key=lambda f: f.w0)
            kit["scripts"][name] = [{"type": f.type, "w0": f.w0, "w1": f.w1} for f in flaws]
            md += [f"## Take `{name}`: natural, except at the marked spans", ""]
            md += [f"- **⟦{CUES[f.type][0]}⟧** {CUES[f.type][1]}" for f in flaws]
            md += ["", f"> {mark(meta['transcript'], flaws)}", ""]
        md += [
            "## Import",
            "",
            "```bash",
            "uv run python scripts/import_recordings.py          # every file in recordings/ named <speech>_<take>_<initials>.<ext>",
            f"uv run python scripts/import_recording.py --baseline {sid} --speaker <initials> --take A  path/to/file.m4a   # one file",
            "```",
        ]
        (DS / "recording_kit" / f"{sid}.json").write_text(json.dumps(kit, indent=1), encoding="utf-8")
        (md_dir / f"{sid}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        print(f"[kit ] {sid}: " + ", ".join(f"{k}={len(v)} flaws" for k, v in kit["scripts"].items() if k != "good"))


if __name__ == "__main__":
    main()
