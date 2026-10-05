# Demo video script (target 6–7 minutes)

The brief asks the video to show three things: **(1)** how the dataset was collected, **(2)** stress
testing across different speech qualities, and **(3)** the dashboard catching specific delivery
deviations. The script follows that order.

**Setup before recording**
- Start the app (`powershell -ExecutionPolicy Bypass -File .\start.ps1`) or open the live demo.
- Open each clip once before recording, so it is cached and loads instantly on camera.
- Recorder: OBS Studio (free), or the Windows Game Bar (**Win + G**, then record). Use 1920×1080 with
  the browser full screen and zoom at 110–125 %.
- Use a headset microphone, and record the narration in a quiet room.
- Keep the files `docs/TECHNICAL.md`, `dataset/README.md` and one `dataset/labels/.../*.TextGrid` ready
  to show.

---

## 0:00–0:30 · Hook and problem

**Screen:** dashboard home page.

> "Speech judges score delivery inconsistently, and speakers get vague feedback like 'work on your
> pacing'. Cadence compares a delivery against a strong reference of the *same* text, finds the
> exact seconds where delivery breaks down, and explains *why*, with numbers."

## 0:30–2:00 · How we built the dataset

**Screen:** `dataset/sources.csv`, then `dataset/README.md` (the flaw ladder table), then a TextGrid
opened in Praat if available (or the JSON label).

> "There is no public dataset of good versus bad deliveries of the same text, so we built one."

1. **Good baselines:** "Six landmark public-domain speeches: FDR 1933, Kennedy 1961, Reagan 1981,
   Clinton 1995, Obama 2009 and Harris 2024, spanning ninety years of recording technology. We cut
   45–75 second passages without applause, transcribed them with Whisper and checked the transcripts by hand."
2. **The bad mirror:** "We injected seven kinds of delivery flaws with signal processing:
   monotone, rushing, dragging, awkward pauses, missing pauses, volume drops and mumbling. Each has
   five severity levels, from almost unnoticeable to egregious."
3. **Exact labels:** "Because we create the flaw ourselves, we know its exact start and end to
   the millisecond. That gave us 240 flawed clips and 300 labelled flaw regions."

**Optional:** play 3 seconds of the original, then the same words at monotone severity 5.

## 2:00–3:00 · How it works (keep it short)

**Screen:** README "How it works" diagram, or the TECHNICAL.md feature table.

> "Forced alignment with a wav2vec2 model maps every word to its timestamps. We extract pitch,
> loudness, FFT spectral balance and voice clarity every 10 milliseconds, normalised per speaker,
> so a deep voice or a quiet speaker is not penalised. Because both recordings say the same words,
> we compare them word by word, and any word that deviates past a tolerance becomes a flaw region."

## 3:00–4:45 · The dashboard catching specific deviations

**Screen:** Analyse tab, then Contrastive dataset, then **Kennedy**.

1. Click **L4 Poor**. Show the **score** and the **rubric bars**, and hover a bar to show its deductions.
2. Point at the **"Injected vs Detected"** strip: "Top is the truth we injected, bottom is what the
   system found. They line up."
3. Click a flaw card, for example **Rushed pacing**:
   - Click **Play yours**, then **Play reference**, so viewers hear the difference.
   - Expand **"Why this was flagged"**: "45 % faster, 5.8 versus 3.2 syllables per second, and here
     is the exact formula with the numbers."
   - The charts zoom to that moment; point at the blue line versus the grey reference.
4. Click a **Monotone** card: "the pitch line goes flat. It kept only 38 % of the speaker's natural
   pitch movement."
5. Click a word in the **transcript** to show that everything is synced to the audio.

## 4:45–5:45 · Stress testing across speech qualities

**Screen:** for the same speech, click **L1 → L2 → L3 → L4 → L5** quickly (cached), then open the
**Stress test** tab.

> "As delivery gets worse, from near-perfect to botched, the score falls step by step."

On the Stress test page:

> "Across all 240 flawed clips, with every clip re-aligned from scratch, the system finds 94 % of
> injected flaws, with 0.93 overlap with the true timestamps and only 0.14 false alarms per minute.
> Four of the six speeches were held out from tuning and score the same, 95 % recall."

Point at the heat-map: "The only misses are at severity 1, the barely noticeable level, which is
what we expect."

## 5:45–6:30 · Your own delivery (+ self-recordings when available)

**Screen:** "Analyse your delivery" tab. Pick Harris, click **Record**, read two sentences (rush one
part), then click **Analyse**.

> "Anyone can record or upload their own reading. Here I rushed the middle on purpose, and it is
> caught."

(If the team's self-recordings have been imported, show the "Self-recorded readings" row instead:
a teammate's natural reading scores high and their directed flawed take is caught.)

## 6:30–7:00 · Close

**Screen:** GitHub README.

> "Everything is open: the code, the dataset on Hugging Face, and a technical report with the full
> evaluation. The results are reproducible with three commands. Thank you."

---

**Tips:** speak slowly, and pause the recording between sections and cut later. Highlight the mouse
cursor (OBS has an option for this). Upload to YouTube as *Unlisted* or *Public* and paste the link
into the README.
