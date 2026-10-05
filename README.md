# Cadence: Contrastive Speech Analytics & Temporal Flaw Grounding

**Multimodal AI Hackathon 2026, Track C.**

Cadence scores a spoken delivery against a strong reference delivery of the same text. It finds
the exact time spans where delivery breaks down (pace, pausing, pitch variety, vocal energy,
articulation) and explains each one with the measured acoustic difference. Results appear in an
interactive dashboard.

- **Contrastive dataset:** 6 public-domain speeches (4 male, 2 female speakers, 1933–2024),
  each mirrored by 40 flawed versions: 7 flaw types × 5 severity levels, plus a 5-step
  overall-quality gradient. Every flaw label is exact to the sample because the flaws are
  injected by signal processing, not annotated by hand.
- **Pipeline:** forced alignment (wav2vec2 CTC) → speaker-normalised acoustic features (F0,
  RMS energy, FFT spectral balance, HNR, MFCC, speech rate, pauses) → word-anchored comparison
  with the reference → flaw regions with start/end times → explanation templates and rubric scores.
- **Dashboard:** browse the dataset gradient, or upload or record your own delivery. You get a
  waveform with flaw regions, three time-aligned feature overlays, flaw cards with the math behind
  each one, and A/B playback against the reference.

| Deliverable | Link |
|---|---|
| Code & documentation | this repository |
| Dataset (audio + labels) | https://huggingface.co/datasets/milipatel2506/cadence-contrastive-speech |
| Technical documentation | [docs/TECHNICAL.md](docs/TECHNICAL.md) · [PDF](docs/Cadence_Technical_Report.pdf) |
| Dataset card | [dataset/README.md](dataset/README.md) |
| Evaluation results | [docs/results/evaluation.md](docs/results/evaluation.md) |
| Demo video | *(YouTube link: coming soon)* |

## Quick start

Requirements: Python 3.11, [uv](https://docs.astral.sh/uv/), ffmpeg, Node.js 20+.

```bash
# 1. Python environment (exact versions from uv.lock)
uv sync

# 2. Dataset: download the published build...
uv run python scripts/hf_dataset.py download --repo milipatel2506/cadence-contrastive-speech
#    ...or rebuild it from the original public-domain recordings (deterministic)
uv run python scripts/fetch_sources.py       # download source speeches (Wikimedia Commons)
uv run python scripts/prepare_baseline.py    # cut, normalise, transcribe, force-align baselines
uv run python scripts/build_dataset.py       # inject the flaw spectrum + labels (~1 h on CPU)

# 3. Start everything on Windows (opens the dashboard in your browser)
powershell -ExecutionPolicy Bypass -File .\start.ps1

#    ...or start the two parts manually:
# Backend API (http://127.0.0.1:8000)
uv run uvicorn speech_analyser.api.main:app --app-dir src --port 8000

# Dashboard (http://127.0.0.1:5173)
cd frontend && npm ci && npm run dev
```

The first analysis downloads the forced-alignment model (MMS_FA, about 1.2 GB) into the torch cache.

### Docker (single container, API and dashboard on one port)

```bash
docker build -t cadence .
docker run -p 8000:8000 -v cadence-models:/home/user/models cadence    # open http://localhost:8000
```

### Tests and evaluation

```bash
uv run pytest                      # injector label-exactness tests
uv run python scripts/evaluate.py  # stress test -> docs/results/evaluation.{json,md}
```

## How it works

```
participant audio ─┐
                   ├─ decode + loudness-normalise (EBU R128, -23 LUFS, 16 kHz mono)
transcript ────────┤
                   ├─ forced alignment: wav2vec2 MMS_FA + CTC Viterbi → word start/end
                   ├─ frame features (10 ms): F0 (two-pass adaptive Praat AC), RMS dB, FFT spectral
                   │  balance 2–8 kHz vs 0–2 kHz, centroid, flux, HNR, MFCC
                   │  speaker normalisation: F0 in semitones re own median, level in dB re own median
reference ─────────┤  (same steps, cached)
                   ├─ word matching (identical transcript → index; otherwise sequence alignment)
                   ├─ per-word deviations relative to the participant's *global* offset
                   │  (removes stable speaker differences, keeps local breakdowns)
                   ├─ thresholds → runs of words → flaw regions [start, end] + severity (1–5 ladder)
                   ├─ causal explanation per region (measured vs reference vs tolerance + formula)
                   └─ rubric scores: pace, pausing, pitch variety, energy, clarity → overall
```

## Repository layout

```
src/speech_analyser/
  audio_io.py        decoding, loudness normalisation
  alignment.py       forced alignment (torchaudio MMS_FA)
  features.py        frame and word features, speaker normalisation
  compare.py         contrastive detector → flaw regions; time-warped overlay
  explain.py         causal explanation templates
  scoring.py         rubric scoring
  pipeline.py        end-to-end analysis
  flaws/             flaw catalogue, injectors (PSOLA, gain, filters, pause edits), planner
  api/main.py        FastAPI backend
scripts/             dataset build, evaluation, Hugging Face publish/fetch
dataset/             sources, transcripts, labels (+ audio once downloaded)
frontend/            React + TypeScript dashboard (wavesurfer.js, ECharts, Tailwind)
docs/                technical documentation and evaluation results
tests/               unit tests
```

## Licensing

Code: MIT. Source recordings are public-domain US federal government works (Wikimedia
Commons; per-file links in [dataset/sources.csv](dataset/sources.csv)). Derived audio is released
under the same terms.
