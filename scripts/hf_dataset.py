"""Publish the dataset to / fetch it from the Hugging Face Hub.

Audio is too large for git, so the full dataset (audio + labels + transcripts + manifest + card)
lives in a Hugging Face dataset repo; labels and transcripts are also tracked in this git repo.

  uv run python scripts/hf_dataset.py upload   --repo <user>/cadence-contrastive-speech   (needs `hf auth login`)
  uv run python scripts/hf_dataset.py download --repo <user>/cadence-contrastive-speech
"""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

DS = Path(__file__).resolve().parents[1] / "dataset"
PATTERNS = ["audio/**", "labels/**", "transcripts/**", "manifest.csv", "sources.csv", "README.md"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["upload", "download"])
    ap.add_argument("--repo", required=True, help="Hugging Face dataset repo id, e.g. user/cadence-contrastive-speech")
    args = ap.parse_args()

    if args.action == "upload":
        api = HfApi()
        api.create_repo(args.repo, repo_type="dataset", exist_ok=True)
        # resumable: uploads in chunks, keeps progress in dataset/.cache, and continues after a
        # dropped connection when re-run
        api.upload_large_folder(repo_id=args.repo, repo_type="dataset", folder_path=DS, allow_patterns=PATTERNS)
        print(f"uploaded -> https://huggingface.co/datasets/{args.repo}")
    else:
        snapshot_download(repo_id=args.repo, repo_type="dataset", local_dir=DS, allow_patterns=PATTERNS)
        print(f"downloaded -> {DS}")


if __name__ == "__main__":
    main()
