"""Import every self-recorded take in recordings/ in one go.

File names: <speech>_<take>_<initials>.<ext>, e.g. harris_A_mp.m4a or clinton_good_jd.wav, where
<speech> is the start of a baseline id (harris -> harris_2024) and <take> is good, A or B.
Each file is passed to scripts/import_recording.py; already-imported takes are skipped unless --force.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "dataset"
AUDIO_EXTS = {".m4a", ".wav", ".mp3", ".webm", ".ogg", ".opus", ".flac", ".aac", ".mp4", ".3gp", ".amr"}
NAME = re.compile(r"^(?P<speech>[a-z]+)[_\- ](?P<take>good|a|b)[_\- ](?P<speaker>[a-z0-9]+)$", re.IGNORECASE)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default=str(ROOT / "recordings"))
    ap.add_argument("--force", action="store_true", help="re-import takes that already exist")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"no folder {folder}; put recordings there first")
    baselines = sorted(p.parent.name for p in (DS / "labels").glob("*/baseline.json"))

    done = failed = skipped = 0
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in AUDIO_EXTS:
            continue
        m = NAME.match(f.stem)
        if not m:
            print(f"[skip] {f.name}: name must look like harris_A_mp{f.suffix}")
            skipped += 1
            continue
        speech, speaker = m["speech"].lower(), m["speaker"].lower()
        take = "good" if m["take"].lower() == "good" else m["take"].upper()
        match = [b for b in baselines if b.startswith(speech)]
        if len(match) != 1:
            print(f"[skip] {f.name}: '{speech}' must match one of {', '.join(b.split('_')[0] for b in baselines)}")
            skipped += 1
            continue
        clip = DS / "labels" / match[0] / f"{match[0]}__self_{speaker}_{take}.json"
        if clip.exists() and not args.force:
            print(f"[have] {f.name} (already imported; --force to redo)")
            continue
        print(f"[imp ] {f.name} -> {match[0]}, speaker {speaker}, take {take}", flush=True)
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "import_recording.py"), str(f),
             "--baseline", match[0], "--speaker", speaker, "--take", take],
            cwd=ROOT,
        )
        if r.returncode == 0:
            done += 1
        else:
            failed += 1
    print(f"[done] imported {done}, failed {failed}, skipped {skipped}")


if __name__ == "__main__":
    main()
