---
license: other
license_name: us-government-public-domain
license_link: https://www.usa.gov/government-copyright
language: [en]
task_categories: [audio-classification]
tags: [speech, prosody, public-speaking, contrastive, temporal-grounding, forced-alignment]
pretty_name: Cadence Contrastive Speech Delivery Dataset
---

# Cadence Contrastive Speech Delivery Dataset

Paired "good vs. flawed" deliveries of the **same text**, for evaluating spoken delivery. Each of
six landmark public-domain speeches is mirrored by 40 flawed versions spanning a gradient from
*almost perfect* to *egregious*. Every flaw is labelled with its exact start and end time, type,
severity and physical parameter.

| | |
|---|---|
| Baselines | 6 speeches by 6 speakers (4 male, 2 female), recorded 1933–2024 |
| Flawed clips | 240 (7 flaw types × 5 severities = 35 single-flaw clips + 5 mixed-gradient clips per speech) |
| Labelled flaw regions | 300 |
| Total audio | 4.2 h (6.2 min of baselines) |
| Audio | 16 kHz mono 16-bit WAV, loudness-normalised to −23 LUFS (EBU R128) |
| Labels | JSON (machine-readable) and Praat TextGrid (`words` and `flaws` tiers) per clip |
| License | Public domain: all sources are US federal government works |

## Baselines ("good" deliveries)

| Baseline | Speaker | Year | Duration | Words | Mean alignment score |
|---|---|---|---|---|---|
| `clinton_1995` | Hillary Rodham Clinton (F) | 1995 | 61.2 s | 159 | 0.96 |
| `fdr_1933` | Franklin D. Roosevelt (M) | 1933 | 46.5 s | 78 | 0.84 |
| `harris_2024` | Kamala Harris (F) | 2024 | 47.4 s | 82 | 0.94 |
| `jfk_1961` | John F. Kennedy (M) | 1961 | 74.4 s | 126 | 0.94 |
| `obama_2009` | Barack Obama (M) | 2009 | 74.4 s | 174 | 0.93 |
| `reagan_1981` | Ronald Reagan (M) | 1981 | 65.7 s | 139 | 0.96 |

**Selection.** Recognised, highly effective orators; recording eras spanning 90 years (a stress
test in itself: FDR's 1933 broadcast is band-limited and noisy); both sexes, so pitch normalisation
is exercised across a ~2× F0 range. Excerpts are 45–75 s passages of continuous speech, chosen to
avoid applause, with cut points snapped to the quietest 200 ms within ±1.5 s so no word is split
(`scripts/prepare_baseline.py`).

**Transcripts** were drafted with Whisper (`small.en`) on each excerpt and checked by hand against
the official texts; for example, "Quezon" was corrected to "Khe Sanh" in Obama 2009. Wording
follows what was *spoken* (e.g. FDR's "And I am convinced"), since alignment must match the audio.

**Alignment.** Word boundaries come from CTC forced alignment with torchaudio's MMS_FA wav2vec2
model. Words with a confidence score below 0.5 are counted in each baseline's metadata.

## The bad-mirror spectrum

Flaws are injected with signal processing into a span of the baseline cut at word boundaries.
Each flaw type has a single physical control parameter with a five-rung ladder, so the gradient is
monotonic and measurable:

| Flaw | Rubric dimension | Manipulation | Sev 1 (subtle) | 2 | 3 | 4 | Sev 5 (egregious) |
|---|---|---|---|---|---|---|---|
| `monotone` | Pitch variety | PSOLA: compress log-F0 excursions around the speaker median to *k*× | 0.70 | 0.50 | 0.35 | 0.20 | 0.05 |
| `rushing` | Pace | PSOLA time-scale (pitch preserved), duration × | 0.85 | 0.75 | 0.65 | 0.55 | 0.45 |
| `dragging` | Pace | PSOLA time-scale, duration × | 1.20 | 1.40 | 1.65 | 1.90 | 2.20 |
| `long_pause` | Pausing | Insert room-tone silence inside a phrase (gap < 150 ms), seconds | 0.45 | 0.70 | 1.00 | 1.50 | 2.20 |
| `pause_removal` | Pausing | Shorten a rhetorical pause (≥ 300 ms) to fraction kept | 0.60 | 0.45 | 0.30 | 0.15 | 0.00 |
| `volume_drop` | Vocal energy | Gain with 80 ms raised ramps, dB | −4 | −7 | −10 | −14 | −19 |
| `mumble` | Clarity | 12th-order zero-phase low-pass, cutoff Hz (+1–5 dB attenuation) | 5000 | 3800 | 2800 | 2000 | 1400 |

PSOLA uses Praat (via parselmouth) with the speaker-adaptive two-pass pitch range of De Looze &
Hirst (2008), so pitch manipulation does not inherit octave errors. Inserted silence is Gaussian
room tone at the recording's 5th-percentile frame RMS, so pauses do not become digital silence
that would be trivially detectable.

**Variants per baseline**

- `<id>__<flaw>_s<1-5>`: one flaw at one severity. The *same* word span is used at all five
  severities, giving a clean dose-response ladder.
- `<id>__mix_L<1-5>`: overall-quality gradient. L1 has one severity-1 flaw ("near-perfect");
  L*k* has *k* flaws of different types at severities drawn from {1}, {1,2}, {2,3}, {3,4}, {4,5}.
  L5 is "botched".

Span placement is random but **seeded by a stable hash of (baseline, variant)**, so the dataset
rebuilds byte-for-byte. Flaw regions never overlap and keep ≥ 2 words apart.

## Why the labels are exact

Each injection replaces one region and returns a piecewise-linear **time map** from the original
timeline to the flawed one. All word timestamps and flaw boundaries in a flawed clip are derived
from that map, never re-estimated, and `tests/test_inject.py` checks this (e.g. an inserted
pause's label equals the inserted duration to < 1 ms).

Each flawed clip also carries `aligned_words`, an **independent** forced alignment of the flawed
audio. This is what the detector sees at evaluation time. Its error against the exact labels is
stored per clip in `alignment_error_ms` (mean 3.8 ms, p95 11.3 ms; see `docs/results/dataset_stats.json`).

## Files

```
sources.csv                      provenance: speaker, year, source URL, license, excerpt window
transcripts/<id>.txt             verified transcript
audio/baseline/<id>.wav          good delivery
audio/flawed/<id>/<clip>.wav     flawed deliveries
labels/<id>/baseline.json        baseline metadata + word alignment
labels/<id>/<clip>.json          flawed-clip labels (schema below)
labels/<id>/*.TextGrid           same labels for Praat
manifest.csv                     one row per clip: kind, level, flaw types, duration, paths
```

**Label schema (`labels/<id>/<clip>.json`)**

```jsonc
{
  "clip_id": "jfk_1961__mix_L3", "baseline_id": "jfk_1961", "kind": "mix", "level": 3,
  "audio": "audio/flawed/jfk_1961/jfk_1961__mix_L3.wav", "duration": 75.31, "sample_rate": 16000,
  "transcript": "Finally, to those nations ...",
  "flaws": [{
    "type": "rushing", "label": "Rushed pacing", "rubric": "pace", "severity": 3,
    "start": 21.402, "end": 25.118,            // seconds in this clip
    "word_span": [52, 61], "text": "both sides begin anew ...",
    "params": {"duration_factor": 0.65},
    "description": "Span compressed to 65% of original duration (pitch preserved)"
  }],
  "words": [{"word": "Finally", "start": 0.31, "end": 0.83}],          // exact (from time map)
  "aligned_words": [{"word": "Finally", "start": 0.32, "end": 0.84, "score": 0.97}],  // forced alignment
  "alignment_error_ms": {"mean": 4.1, "max": 40.0},
  "time_map": [[0.0, 0.0], [20.1, 20.1], [24.9, 23.2]]                 // original -> clip time
}
```

## Rebuilding

```bash
uv run python scripts/fetch_sources.py      # original recordings from Wikimedia Commons
uv run python scripts/prepare_baseline.py   # excerpt, normalise, transcribe, align
uv run python scripts/build_dataset.py      # flawed spectrum + labels (+ independent alignment)
uv run python scripts/dataset_stats.py      # summary statistics
```

## Limitations

- Flaws are synthetic manipulations of one speaker's own delivery. They are perfectly controlled
  and exactly labelled, but not identical to how people actually rush or mumble (rushing also
  slurs articulation, for example). Self-recorded flawed readings complement them; see the
  technical report.
- `pause_removal` severity 1 keeps 60 % of a pause, which listeners often accept as stylistic.
- The mumble ladder's lowest rungs (5.0 / 3.8 kHz cut-offs) are physically invisible on
  band-limited recordings such as FDR 1933, which carry little energy above 4 kHz.
