"""Download the raw source speeches listed in dataset/sources.csv into dataset/raw/."""

from __future__ import annotations

import csv
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "dataset" / "raw"
UA = {"User-Agent": "SpeechAnalyserHackathon/0.1 (contrastive speech dataset build)"}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with open(ROOT / "dataset" / "sources.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        ext = Path(row["url"]).suffix
        out = RAW / f"{row['id']}{ext}"
        if out.exists():
            print(f"[skip] {out.name}")
            continue
        print(f"[get ] {row['id']} <- {row['url']}")
        out.write_bytes(download(row["url"]))
        time.sleep(5.0)


def download(url: str, attempts: int = 6) -> bytes:
    """GET with exponential backoff on HTTP 429 (Wikimedia rate limiting)."""
    for i in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == attempts - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 15 * 2**i)
            print(f"       rate limited, retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


if __name__ == "__main__":
    main()
