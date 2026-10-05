"""Deploy the dashboard as a Hugging Face Docker Space.

  uv run python scripts/deploy_space.py --space <user>/cadence     (needs `hf auth login`)

Uploads the code, labels and Dockerfile; the Space builds the image and, on start-up, downloads the
dataset audio from the Hugging Face dataset repo (DATASET_REPO in the Dockerfile).

Note: as of 2026, hosting Docker Spaces on Hugging Face requires a PRO subscription (only static
Spaces are free). The same Dockerfile runs on any container host.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]

SPACE_README = """---
title: Cadence Speech Delivery Analyser
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Contrastive speech delivery analysis with timed flaws
---

# Cadence: Contrastive Speech Analytics & Temporal Flaw Grounding

Multimodal AI Hackathon 2026, Track C. Compare a spoken delivery with a reference delivery of the
same text: flaw regions with exact timestamps, causal explanations and rubric scores.

Code and documentation: {github}
Dataset: https://huggingface.co/datasets/{dataset}

The first analysis of an uploaded recording downloads the forced-alignment model (about 1.2 GB), so
it takes a minute or two; dataset clips use cached alignments and respond in seconds.
"""

INCLUDE = [
    "Dockerfile",
    ".dockerignore",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "LICENSE",
    "src/**",
    "scripts/**",
    "docs/**",
    "dataset/labels/**",
    "dataset/transcripts/**",
    "dataset/recording_kit/**",
    "dataset/*.csv",
    "dataset/README.md",
    "frontend/**",
]
EXCLUDE = ["**/__pycache__/**", "frontend/node_modules/**", "frontend/dist/**", "**/*.wav"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", required=True, help="e.g. user/cadence")
    ap.add_argument("--dataset", default="milipatel2506/cadence-contrastive-speech")
    ap.add_argument("--github", default="https://github.com/milipatel2506/Speech-Analyser")
    args = ap.parse_args()

    api = HfApi()
    api.create_repo(args.space, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(
        repo_id=args.space,
        repo_type="space",
        folder_path=ROOT,
        allow_patterns=INCLUDE,
        ignore_patterns=EXCLUDE,
        commit_message="Deploy Cadence",
    )
    api.upload_file(
        repo_id=args.space,
        repo_type="space",
        path_in_repo="README.md",
        path_or_fileobj=SPACE_README.format(github=args.github, dataset=args.dataset).encode("utf-8"),
        commit_message="Space card",
    )
    print(f"deployed -> https://huggingface.co/spaces/{args.space}")


if __name__ == "__main__":
    main()
