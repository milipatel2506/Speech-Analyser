# Cadence: Technical Report

**Contrastive Speech Analytics & Temporal Flaw Grounding** · Multimodal AI Hackathon 2026, Track C

## 1. Problem and approach

Judges of competitive speaking (declamation, oratory, interpretive reading) score delivery
inconsistently and give vague feedback. We treat delivery as a set of time series (pitch, energy,
spectral balance, timing) and compare a participant against a strong reference delivery of
**the same text**. Because the words are identical, forced alignment pairs every participant word
with its reference counterpart. A flaw then becomes a *local, measurable deviation between two
aligned time series*, which can be located to the word and explained with the numbers that caused it.

The system has four parts: (§2) a contrastive dataset with exact labels, (§3) feature extraction
on forced-aligned audio, (§4) a contrastive detector that produces timed, explained flaw regions,
and (§5) rubric scoring. §6 reports the stress-test evaluation, §7 describes the dashboard and
§8 covers reproducibility.

## 2. Dataset construction

**Baselines.** Six excerpts (45–75 s) of landmark public-domain speeches by six speakers:
FDR 1933, JFK 1961, Reagan 1981, H. R. Clinton 1995, Obama 2009, Harris 2024 (4 male, 2
female; 1933–2024 recording chains). Excerpts are continuous speech without applause; cut points
are snapped to the quietest 200 ms within ±1.5 s. Audio is converted to 16 kHz mono and
loudness-normalised to −23 LUFS (ITU-R BS.1770). Transcripts are drafted by Whisper and
corrected by hand; word timings come from CTC forced alignment (§3.1).

**Bad-mirror spectrum.** Rather than hand-labelling imperfect re-recordings, we *inject* flaws
into the baseline with signal processing. This makes the labels exact and the gradient
controllable. Seven flaw types each have one physical parameter and a five-rung ladder from
"almost perfect" (1) to "egregious" (5):

| Flaw | Manipulation | Ladder (sev 1 → 5) |
|---|---|---|
| Monotone | TD-PSOLA; F0' = m·(F0/m)^k, m = speaker median | k = 0.70, 0.50, 0.35, 0.20, 0.05 |
| Rushing / dragging | TD-PSOLA time-scaling, pitch preserved | ×0.85 … 0.45 / ×1.2 … 2.2 |
| Awkward pause | room-tone silence inside a phrase | 0.45 … 2.2 s |
| Missing pause | shorten a ≥ 300 ms rhetorical pause | keep 60 % … 0 % |
| Volume drop | gain with 80 ms raised-cosine ramps | −4 … −19 dB |
| Mumbling | 12th-order zero-phase low-pass, −1…−5 dB | 5.0 … 1.4 kHz |

Each baseline yields 35 single-flaw clips (the same word span across all five severities, a
dose-response ladder) and 5 mixed clips forming an overall-quality gradient: L1 has one sev-1 flaw,
and L5 has five flaws of different types at sev 4–5. Spans are cut at word boundaries (mid-gap) and
spliced with 5 ms edge blending.

**Exact temporal labels.** Every edit returns a piecewise-linear time map (original → flawed
timeline). All word times and flaw boundaries in the flawed clip are *computed through this map*,
never re-estimated. Unit tests check label exactness, e.g. an inserted pause's label equals its
inserted length to within 1 ms. Each clip also stores an *independent* forced alignment of the
flawed audio (`aligned_words`), which is what the detector uses during evaluation. Its mean error
against the exact labels is **3.8 ms** (p95 11.3 ms).

**Reproducibility.** All randomness (span placement, room-tone noise) is seeded by a CRC32 hash of
(baseline, variant), so `build_dataset.py` regenerates the dataset byte-for-byte. Totals:
240 flawed clips with 300 labelled flaw regions (4.2 h of audio).

## 3. Feature extraction

### 3.1 Forced alignment

We use torchaudio's MMS_FA bundle, a wav2vec2 acoustic model trained for multilingual forced
alignment, emitting character posteriors every 20 ms. The transcript is normalised to the model
alphabet (NFKD, lower-case a–z and apostrophe), and the CTC Viterbi path gives each character a
frame span; a word's start/end is its first/last character's span and its confidence is the
length-weighted mean posterior. Long inputs are processed in 20 s windows with 1 s of context on
each side, which bounds self-attention memory on CPU.

### 3.2 Frame features (10 ms hop)

| Feature | Definition | Purpose |
|---|---|---|
| F0 | Praat autocorrelation; two-pass speaker-adaptive range: floor = min(0.75·Q1, 0.6·median), ceiling = 1.5·Q3 of a 60–700 Hz first pass (after De Looze & Hirst 2008; the median cap stops the floor drifting up when part of a recording is flat); octave-jump removal (> 7 st from the 150 ms local median) | pitch contour |
| Pitch (normalised) | st = 12·log₂(F0 / median F0 of the speaker) | speaker-agnostic intonation |
| Energy | RMS over 25 ms Hann windows in dB, minus the speaker's median voiced level | speaker-agnostic loudness |
| Spectral balance | B₂ = 10·log₁₀(P₂₋₈ₖ / P₀.₀₈₋₂ₖ), B₄ = 10·log₁₀(P₄₋₈ₖ / P₀.₀₈₋₄ₖ) from the 512-point FFT power spectrum | consonant crispness |
| HNR | Praat cross-correlation harmonicity | voice clarity |
| Centroid, flux, MFCC-13 | FFT centroid; positive log-spectral flux; CMVN MFCCs | articulation descriptors |

Word-level features aggregate frames inside each aligned word: duration, syllables (orthographic
vowel-group count), mean and 10–90 % range of pitch (st), power-mean level, speech-frame mean
spectral balance, HNR, and the pause before the next word. Utterance summaries include speech and
articulation rate, pause count/ratio, pitch s.d. and range (st), loudness range and mean HNR.

**Speaker agnosticism.** Pitch is in semitones relative to each speaker's own median and level is
in dB relative to each speaker's own median voiced level. Every comparison (§4) then subtracts the
participant's *global* offset from the reference (overall tempo ratio, pitch-spread ratio, level
and balance offsets). A slower, deeper, quieter or more nasal speaker is therefore not penalised
for being themselves; only local breakdowns relative to their own delivery are flagged. Global
offsets are reported and scored separately (§5).

## 4. Contrastive detection and causal explanation

**Correspondence.** With identical transcripts, participant word *i* ↔ reference word *i*;
otherwise words are matched by longest-common-subsequence alignment of normalised tokens. A
piecewise-linear warp through matched word boundaries maps reference frames onto the participant
timeline for the overlays.

**Per-word deviations** (signed, after removing the global offset):

- **Pace**: d = log₂(Σ dur_p / Σ dur_r) over a 3-word window − global median; flagged if
  |d| > log₂(1.12). Each word's duration includes up to 150 ms of the silence after it: CTC places
  word *onsets* reliably, but where a word *ends* inside trailing silence is ambiguous (identical
  audio aligned as 1.12 s + 0 s gap and as 0.88 s + 0.24 s gap), and raw word durations turn that
  ambiguity into false tempo changes. The reported ratio uses the whole span (first onset to last
  offset), so compressed micro-gaps count.
- **Pitch variety**: robust spread σ = 1.4826·MAD of st over a 5-word window; d = log₂(σ_p/σ_r) −
  global median; flagged if 2^d < 0.78. MAD rather than s.d. makes it immune to residual octave errors.
- **Energy**: 3-word median of (L_p − L_r) − global median; flagged below −3 dB.
- **Clarity**: same construction for B₂ (tolerance 2 dB) and B₄ (4 dB); flagged when *either*
  band is past tolerance. B₄ catches subtle mumbling (a 5 kHz low-pass drops B₄ by ~5 dB but B₂ by
  only ~0.6 dB), while B₂ grades the severe end, where B₄ saturates.
- **Pauses**: expected gap = reference gap × local tempo. *Inserted*: excess > 0.3 s and gap >
  0.4 s. *Missing*: reference gap ≥ 0.3 s and participant keeps < 50 %.

**Temporal grounding.** Flagged words form runs (bridging one-word holes; minimum 3 words for
pace, 4 for pitch, 2 for energy, 3 for clarity). Edge words flagged only through window smoothing are
trimmed. A region spans the first word's onset to the last word's offset, so boundaries inherit
forced-alignment precision. Pause flaws are bounded by the silent gap itself (inserted) or by the
two words that run together (missing). Physically coupled diagnoses are resolved, not double
counted: when mumbling and a volume drop fire on the same span, the one further past its own
tolerance is kept; a pause inside or touching a detected dragging (rushing) span is dropped when
the span's *measured* stretch ratio accounts for the pause's length, because time-scaling also
scales the silences between words.

**Severity** is the nearest rung of the injection ladder to the *measured* physical quantity
(e.g. a measured local tempo ratio of 0.56 maps to rushing severity 4). This makes severity a
statement about the signal, not an opaque score.

**Causal explanation.** Each region is rendered from a template into: what happened (with the
quoted words and time span), an evidence table (participant vs reference vs tolerance), the formula
with the actual numbers substituted, why it matters perceptually, and a concrete practice tip. For example:

> *Rushed pacing at 25.77–28.89 s* (JFK 1961, held-out; injected 25.76–28.87 s, severity 4).
> “in planned or accidental self-destruction We dare not tempt them with” was delivered 45 % faster
> than the reference (5.8 vs 3.2 syllables/s), after allowing for your overall pace.
> r = (Σd_participant / Σd_reference) / T_global = (3.12 / 5.65) / 1.00 = 0.55; |log₂ r| = 0.85 > log₂(1.12) = 0.16 → severity 4

Explanations are template-generated (no LLM), so reports are deterministic.

## 5. Scoring methodology (rubric)

Five dimensions (pace, pausing, pitch variety, vocal energy, clarity), each scored out of 100 and
weighted equally:

score_d = 100 − Σ_regions P(sev)·c − G_d, clipped to [0, 100]

with P = {8, 16, 28, 42, 58} for severities 1–5. The coverage factor c = clip(T_ref/5 s, 0.6, 1.5)
uses the region's *reference* duration (rushing shortens its own span). G_d is a global penalty
when the whole delivery deviates beyond tolerance (tempo ±15 %, pitch spread < 75 % of the
reference). Bands: ≥ 90 Excellent, ≥ 75 Strong, ≥ 60 Developing, ≥ 40 Weak, else Poor.
Every deduction is itemised in the report, and the dashboard shows it per rubric bar.

## 6. Evaluation: stress testing across the gradient

**Protocol.** For each of the 240 flawed clips, the flawed audio is re-aligned from scratch, the
detector is run against its baseline, and predicted regions are matched to injected ones (same
type, temporal IoU ≥ 0.3, greedy one-to-one). Detector thresholds were set on two baselines (FDR,
Clinton); the other four were held out.

**Per flaw type and injected severity** (recall; boundary errors and severity MAE over matched regions):

| Flaw | Sev 1 | Sev 2 | Sev 3 | Sev 4 | Sev 5 | Recall | IoU | Onset err (ms) | Offset err (ms) | Severity MAE |
|---|---|---|---|---|---|---|---|---|---|---|
| Monotone delivery | 100% | 100% | 100% | 100% | 100% | 100% | 0.84 | 308 | 643 | 0.11 |
| Rushed pacing | 70% | 100% | 100% | 100% | 100% | 93% | 0.90 | 107 | 189 | 0.05 |
| Dragging pacing | 100% | 100% | 100% | 100% | 100% | 100% | 0.94 | 178 | 201 | 0.05 |
| Awkward mid-phrase pause | 100% | 100% | 100% | 92% | 100% | 98% | 0.92 | 34 | 43 | 0.00 |
| Missing rhetorical pause | 0% | 89% | 100% | 100% | 100% | 80% | 0.98 | 6 | 8 | 0.17 |
| Volume drop | 100% | 100% | 100% | 100% | 100% | 100% | 0.98 | 88 | 5 | 0.04 |
| Mumbled articulation | 33% | 100% | 100% | 100% | 100% | 90% | 0.98 | 3 | 61 | 0.42 |

**Overall:** recall **94 %**, mean temporal IoU **0.93**, mean onset / offset error 110 / 177 ms,
**0.14 false positives per minute of audio**, severity MAE ≤ 0.17 for every type except mumbling
(0.42). Overall score vs gradient level L1–L5: Spearman ρ = **−0.96** (single-flaw ladders −0.88 to −0.95).

**Per speech: tuning vs held-out:**

| Baseline | Set | Recall | IoU | Onset err (ms) | Offset err (ms) | False pos./min |
|---|---|---|---|---|---|---|
| `clinton_1995` | tuning | 94% | 0.94 | 127 | 98 | 0.05 |
| `fdr_1933` | tuning | 92% | 0.95 | 71 | 104 | 0.23 |
| `harris_2024` | held-out | 96% | 0.93 | 146 | 290 | 0.25 |
| `jfk_1961` | held-out | 92% | 0.96 | 53 | 189 | 0.08 |
| `obama_2009` | held-out | 94% | 0.90 | 172 | 163 | 0.22 |
| `reagan_1981` | held-out | 98% | 0.93 | 92 | 214 | 0.07 |

Held-out speeches only: recall 95 %, IoU 0.93, 0.15 false positives/min, the same as the tuning set.

**Development history (for transparency).** The first full run with frozen thresholds gave recall
94 %, IoU 0.93 and **0.25 false positives/min** (held-out 0.28/min; archived in
`docs/results/evaluation_before_silence_fix.*`). Inspecting the held-out false positives exposed
three systematic measurement errors, which we fixed. None of the fixes changed a threshold:
(1) word-end ambiguity inflating tempo deviations (16 of 20 spurious "rushing" flags sat on one JFK
phrase), fixed by the 150 ms silence allowance in §4; (2) pauses stretched by a detected dragging
span reported a second time, fixed by the coupling rule in §4; (3) the adaptive pitch floor rising
when a long span was flattened, deleting genuine low notes elsewhere (a recurring Harris
"monotone" flag), fixed by the median-capped floor in §3.2. Because these fixes were found on the
held-out speeches, the post-fix held-out numbers are not strictly blind; the pre-fix run is the
blind result.

**Reading the results.** Detection is near-complete from severity 2 upward for every flaw type, and
severity is recovered almost exactly because the detector measures the same physical quantity the
injector controls (a rushed span measured at ratio 0.55 against an injected 0.55). The misses
cluster at the subtlest rungs, by design: a *missing pause* at severity 1 keeps 60 % of the pause,
above the 50 % tolerance a listener would also accept, and *mumbling* with a 5 kHz low-pass is
physically invisible on recordings with little energy above 4 kHz (FDR 1933). Pause regions are
the most precise (≈ 5–45 ms boundary error) because they are bounded by aligned silence; monotone
regions are the loosest (onset 0.3 s, offset 0.6 s) because pitch spread is measured over a 5-word
window, which spreads the evidence into neighbouring words. An identical delivery produces no flaws
(unit test), and forced alignment of the flawed audio stays within 3.8 ms of the exact labels on
average, so alignment is not the limiting factor.

## 7. Dashboard

React + TypeScript (Vite), wavesurfer.js and ECharts, served by a FastAPI backend.

- **Contrastive dataset explorer**: pick a speech, then any rung of the overall gradient (L1–L5) or
  any cell of the 7 × 5 single-flaw matrix. The *injected vs detected* strip shows ground truth and
  predictions on one timeline.
- **Analyse your delivery**: choose a reference (dataset speech or your own upload plus
  transcript), then record in the browser or upload any audio/video file (decoded by ffmpeg).
- **Results**: overall score with itemised rubric bars; waveform with severity-shaded flaw regions
  (click to replay); three small-multiple overlays (pitch st, loudness dB, spectral balance dB) of
  participant vs time-warped reference with a linked crosshair, zoom, and playhead; flaw cards with
  *Play yours* / *Play reference* A/B audio, the evidence table and the formula; a forced-aligned
  transcript that follows playback.
- **Stress test** page: the §6 recall heat-map and summary tiles.

## 8. Reproducibility and engineering

- Exact Python dependencies in `uv.lock` (CPU-only torch on all platforms); Node dependencies in
  `package-lock.json`; a single Dockerfile builds the dashboard and serves both on port 8000.
- Deterministic dataset build (seeded), deterministic analysis (no sampling; templates instead of
  generation); unit tests for label exactness and end-to-end detection on synthetic audio.
- The full dataset is rebuildable from the original public-domain sources with three commands.

## 9. Limitations and next steps

Injected flaws are perfectly controlled but simplified: real rushing also slurs consonants, and
real nerves add pitch tremor. Self-recorded flawed readings (§2) test transfer. Thresholds are
literature- and data-calibrated constants, not learned. With a larger set of human recordings,
a learned per-dimension classifier on the same word-level deviation features would be a natural
extension. Fillers ("um", "uh") and mispronunciations are not yet modelled. A transcript
mismatch is handled by sequence alignment, but unmatched words are excluded from comparison.

## References

- De Looze, C., & Hirst, D. (2008). Detecting changes in key and range for the automatic modelling and coding of intonation. *Speech Prosody*.
- Moulines, E., & Charpentier, F. (1990). Pitch-synchronous waveform processing techniques for text-to-speech synthesis using diphones. *Speech Communication*, 9(5–6).
- Pratap, V., et al. (2023). Scaling speech technology to 1,000+ languages (MMS). *arXiv:2305.13516*.
- Boersma, P. (1993). Accurate short-term analysis of the fundamental frequency and the harmonics-to-noise ratio of a sampled sound. *IFA Proceedings 17*.
- ITU-R BS.1770-4 (2015). Algorithms to measure audio programme loudness and true-peak audio level.
- Jadoul, Y., Thompson, B., & de Boer, B. (2018). Introducing Parselmouth: A Python interface to Praat. *Journal of Phonetics*, 71.
