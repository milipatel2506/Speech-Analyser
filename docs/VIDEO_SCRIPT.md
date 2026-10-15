# Demo video script: final version (7 clips, ~7 minutes)

Record **7 short clips** (one per section below) and join them in Clipchamp. If you make a mistake,
redo only that clip. Everything happens in the **browser**: no VS Code or other apps on screen.

The brief asks the video to show **(1)** how the dataset was collected, **(2)** stress testing across
different speech qualities, and **(3)** the dashboard catching specific delivery deviations, including
**audio upload**. Clips 2, 4, 5 and 6 cover those.

## Before recording

1. Start the app in the VS Code terminal: `powershell -ExecutionPolicy Bypass -File .\start.ps1`
2. Open three browser tabs, in this order, and close all others. Zoom 110 % (**Ctrl + +**).
   1. GitHub: https://github.com/milipatel2506/Speech-Analyser
   2. Dataset: https://huggingface.co/datasets/milipatel2506/cadence-contrastive-speech
   3. Dashboard: http://127.0.0.1:5173
3. **Warm up** (the first click on a clip takes a few seconds; after that it is instant). Click
   Kennedy **L1 → L5** once, and the Kamala Harris **self-recorded** takes once.
4. **Win + N → Do not disturb.** Close WhatsApp, email and other apps that make sounds.
5. Use earphones with a mic in a quiet room. Keep this script open on your phone to read from.
6. Record each clip with **Win + Shift + R** (Snipping Tool): select the browser window, **turn
   the microphone ON**, Start, then Stop and Save as `clip1.mp4` … `clip7.mp4`. Do a 10-second test
   first and check that your voice is audible.

---

## Clip 1 · Introduction (~30 s)

**Show:** the dashboard home page.

> "Speech judges score delivery inconsistently and give vague feedback like 'work on your pacing'.
> Our project, Cadence, compares a delivery with a strong reference of the same text, finds the
> exact seconds where delivery breaks down, and explains why, with numbers."

## Clip 2 · How we built the dataset (~1.5 min)

**Show:** the Hugging Face dataset tab. Scroll slowly through the dataset card (the baselines table
and the flaw ladder table). If an audio player is visible, play 3 seconds of a clip.

> "No public dataset of good versus bad deliveries of the same text existed, so we built one. We
> took six famous public-domain speeches, from Roosevelt in 1933 to Kamala Harris in 2024, and
> transcribed them with Whisper. Then we created bad versions with audio processing: seven kinds
> of mistakes (monotone, rushing, dragging, awkward pauses, missing pauses, volume drops and
> mumbling), each at five severity levels, from barely noticeable to egregious. That gives 240
> flawed clips with 300 labelled mistakes. Because we created each mistake ourselves, we know its
> exact start and end time to the millisecond."

## Clip 3 · How it works (~45 s)

**Show:** the GitHub tab, scrolled to the "How it works" diagram in the README.

> "First, a wav2vec2 AI model finds the exact timing of every word. Then we measure pitch,
> loudness, FFT spectral balance and voice clarity every 10 milliseconds, normalised for each
> speaker's voice. Because both recordings say the same words, we compare them word by word, and
> wherever the delivery deviates past a tolerance, that becomes a flaw region with exact
> timestamps and an explanation."

## Clip 4 · The dashboard catching specific deviations (~2 min) ⭐ most important

**Show:** Dashboard → **Contrastive dataset** → **John F. Kennedy** → **L4 Poor**.

1. Point at the score and hover a rubric bar:
   > "This delivery scores __ out of 100" *(say the number on screen)* "and each bar shows exactly
   > where points were lost."
2. Point at the **Injected vs Detected** strip:
   > "The top row is where we planted mistakes; the bottom row is what the AI found. They line up."
3. Click a **Rushed pacing** flaw card. Click **Play yours**, then **Play reference**, and let both
   play. Then click **Why this was flagged**:
   > "This part was much faster than the reference, and here are the measured numbers and the exact
   > formula behind the decision."
4. Click a **Monotone** card. The charts zoom in; point at the blue line versus the grey line:
   > "Here the pitch line goes flat compared with the reference."
5. Click a word in the **transcript**:
   > "Everything is synced to the audio."

## Clip 5 · Stress testing across speech qualities (~1 min)

**Show:** for Kennedy, click **L1 → L2 → L3 → L4 → L5** quickly, then the **Stress test** tab.

> "As the delivery gets worse, from near-perfect to botched, the score drops step by step."

On the Stress test page:

> "Across all 240 clips, with every clip re-aligned from scratch, the system finds 94 % of planted
> mistakes, with 0.93 timing overlap and only 0.14 false alarms per minute. On four speeches it
> never saw during tuning, it scores the same. It misses mostly at level 1, the barely noticeable
> mistakes."

## Clip 6 · Uploading your own audio (~1 min)

**Show:** Dashboard → **Analyse your delivery** tab.

1. Click **Kamala Harris** as the reference (her text appears).
2. Click **Upload audio** and choose `D:\Multimodel speech analyser\recordings\harris_A_mp.m4a`.
3. Click **Analyse delivery**.

> "Anyone can upload or record their own reading. The system decodes the audio, aligns every word
> and extracts the features."

The analysis takes about 20–40 seconds. Keep talking or pause the recording; you can cut the wait
in Clipchamp. When the result appears, scroll through the score, waveform and flaw cards:

> "Here are the results for my own reading."

## Clip 7 · Honest limits and closing (~1 min)

**Show:** while still on the results from clip 6 (or a Harris *Self-recorded* take in the
Contrastive dataset tab):

> "Our planted mistakes were caught, but the system also flags parts of our natural reading,
> because two different people never sound exactly like Kamala Harris. We tried adapting the
> tolerances to each speaker. It cut false alarms by 75 %, but it missed real mistakes, so we
> kept the original model and documented this as future work."

Switch to the **GitHub** tab:

> "Everything is open: the code, the dataset on Hugging Face, and a technical report with the full
> evaluation. Thank you!"

---

## Editing and upload

1. **Clipchamp** (Windows key → type *Clipchamp*): Create a new video → Import media (clip1–clip7) →
   drag them to the timeline in order → trim the silent starts and ends → optionally add a title
   text → **Export 1080p**. Target 6–8 minutes (the allowed range is 3–10).
2. **YouTube**: Create (+) → Upload video → *Not made for kids* → Visibility **Unlisted** or
   **Public** → Publish → copy the link and test it in a private window (Ctrl + Shift + N).

**Title:** `Cadence: Contrastive Speech Analytics & Temporal Flaw Grounding | Multimodal AI Hackathon 2026 (Track C)`

**Description:**

```
Cadence compares a speech delivery against a reference reading of the same text, finds the exact time regions where delivery breaks down (pace, pauses, pitch, energy, clarity), and explains each flaw with the measured acoustic numbers.

Code: https://github.com/milipatel2506/Speech-Analyser
Dataset: https://huggingface.co/datasets/milipatel2506/cadence-contrastive-speech

Multimodal AI Hackathon 2026, Track C
```

**Backup recorder:** if Snipping Tool doesn't capture your voice, use **Win + Alt + R** (Xbox Game
Bar; press again to stop, files go to `Videos\Captures`). It records only the browser window, which
is fine because everything above happens in the browser.

**Tips:** speak slowly, move the mouse calmly to what you're describing, and redo a clip if you
stumble. It only takes a minute.
