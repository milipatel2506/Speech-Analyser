"""Turn a detected flaw region's numbers into a structured, human-readable causal explanation.

Every explanation carries the measured value, the reference value, the tolerance it was tested
against and the formula, so the claim can be checked by hand. Text is generated from templates
only (no LLM), which keeps reports reproducible.
"""

from __future__ import annotations

import math

from .compare import Comparison, DetectorConfig, Region
from .flaws.spec import FLAWS


def _quote(words: list[dict], a: int, b: int, max_words: int = 12) -> str:
    ws = [w["word"] for w in words[a : b + 1]]
    text = " ".join(ws if len(ws) <= max_words else ws[:5] + ["…"] + ws[-5:])
    return f"“{text}”"


def explain(region: Region, words: list[dict], comp: Comparison, cfg: DetectorConfig) -> dict:
    m, g = region.measured, comp.globals
    quote = _quote(words, region.w0, region.w1)
    t = f"{region.start:.2f}–{region.end:.2f} s"

    if region.type in ("rushing", "dragging"):
        r = m["duration_ratio"]
        faster = region.type == "rushing"
        what = (
            f"{quote} was delivered {abs(1 - r):.0%} {'faster' if faster else 'slower'} than the reference "
            f"({m['syll_rate_participant']:.1f} vs {m['syll_rate_baseline']:.1f} syllables/s), "
            f"after allowing for your overall pace."
        )
        evidence = [
            {"metric": "Span duration", "participant": f"{m['participant_s']:.2f} s", "reference": f"{m['baseline_s']:.2f} s"},
            {"metric": "Your overall tempo vs reference", "participant": f"×{g['tempo_ratio']:.2f}", "reference": "×1.00"},
            {"metric": "Local tempo ratio (normalised)", "participant": f"{r:.2f}", "reference": f"1.00 ± {cfg.pace_tol:.2f}"},
        ]
        math_ = (
            f"r = (Σd_participant / Σd_reference) / T_global = ({m['participant_s']:.2f} / {m['baseline_s']:.2f}) / "
            f"{g['tempo_ratio']:.2f} = {r:.2f};  |log₂ r| = {abs(math.log2(r)):.2f} > log₂(1+{cfg.pace_tol}) = "
            f"{math.log2(1 + cfg.pace_tol):.2f}"
        )
        why = (
            "Compressing syllables shortens vowels and the micro-pauses listeners use to segment words, "
            "lowering intelligibility and signalling nervousness."
            if faster
            else "Stretching the phrase dilutes stress contrast and lets audience attention drift; it reads as hesitation."
        )
        tip = (
            "Mark this phrase in your script and give each content word its full vowel; breathe at the comma before it."
            if faster
            else "Rehearse this phrase as one breath group; keep momentum through the function words."
        )

    elif region.type == "monotone":
        r = m["pitch_sd_ratio"]
        what = (
            f"Pitch movement over {quote} collapsed to {r:.0%} of the reference's expressive range "
            f"({m['pitch_sd_participant_st']:.1f} vs {m['pitch_sd_baseline_st']:.1f} semitones s.d.)."
        )
        evidence = [
            {"metric": "F0 s.d. (semitones re your median)", "participant": f"{m['pitch_sd_participant_st']:.2f} st", "reference": f"{m['pitch_sd_baseline_st']:.2f} st"},
            {"metric": "F0 90 % range", "participant": f"{m['pitch_range_participant_st']:.1f} st", "reference": f"{m['pitch_range_baseline_st']:.1f} st"},
            {"metric": "Your overall pitch spread vs reference", "participant": f"×{g['pitch_spread_ratio']:.2f}", "reference": "×1.00"},
        ]
        math_ = (
            f"F0 in semitones st = 12·log₂(f0 / f0_median). r = (σ_participant / σ_reference) / S_global = "
            f"({m['pitch_sd_participant_st']:.2f} / {m['pitch_sd_baseline_st']:.2f}) / {g['pitch_spread_ratio']:.2f} = {r:.2f} "
            f"< {cfg.pitch_ratio_tol:.2f}"
        )
        why = "Pitch movement is the main cue for emphasis and phrase structure; a flat contour hides which words matter and sounds disengaged."
        tip = "Pick the one or two key words in this phrase and lift your pitch on their stressed syllable; let the phrase end fall."

    elif region.type == "volume_drop":
        d = m["level_change_db"]
        what = f"Your level dropped {abs(d):.1f} dB below your own typical level relative to the reference over {quote}."
        evidence = [
            {"metric": "Level change vs reference (normalised)", "participant": f"{d:+.1f} dB", "reference": f"0 ± {cfg.energy_tol_db:.0f} dB"},
            {"metric": "Your overall level offset", "participant": f"{g['level_offset_db']:+.1f} dB", "reference": "0 dB"},
        ]
        math_ = (
            f"ΔE = median₃(E_participant − E_reference) − ΔE_global (dB re each speaker's median voiced level) "
            f"= {d:+.1f} dB < −{cfg.energy_tol_db:.0f} dB.  A {abs(d):.0f} dB drop is {10 ** (d / 20):.0%} of the sound pressure."
        )
        why = "Energy carries conviction; trailing off makes the content sound unimportant and is the first thing lost in a large room."
        tip = "Support this phrase from the breath: inhale before it and aim the sound at the back row."

    elif region.type == "mumble":
        d, air = m["hf_balance_change_db"], m["air_balance_change_db"]
        what = (
            f"Articulation over {quote} lost high-frequency detail: the 4–8 kHz fricative band fell {abs(air):.1f} dB "
            f"and the 2–8 kHz consonant band {abs(d):.1f} dB relative to the reference."
        )
        evidence = [
            {"metric": "Balance 4–8 kHz vs 0–4 kHz (normalised)", "participant": f"{air:+.1f} dB", "reference": f"0 ± {cfg.air_tol_db:.0f} dB"},
            {"metric": "Balance 2–8 kHz vs 0–2 kHz (normalised)", "participant": f"{d:+.1f} dB", "reference": f"0 ± {cfg.clarity_tol_db:.0f} dB"},
            {"metric": "Harmonics-to-noise ratio change", "participant": f"{m['hnr_change_db']:+.1f} dB", "reference": "0 dB"},
        ]
        math_ = (
            f"B(f) = 10·log₁₀(P(f–8 kHz) / P(0.08 kHz–f)) from the FFT power spectrum; "
            f"ΔB = median₃(B_participant − B_reference) − ΔB_global.  "
            f"ΔB(4 kHz) = {air:+.1f} dB (tol −{cfg.air_tol_db:.0f}),  ΔB(2 kHz) = {d:+.1f} dB (tol −{cfg.clarity_tol_db:.0f})"
        )
        why = "Consonant bursts and fricatives live above 2 kHz; when that band weakens, words blur together even when loudness is fine."
        tip = "Over-articulate the consonants here (t, k, s, p) and open the jaw a little more on the vowels."

    elif region.type == "long_pause":
        what = (
            f"An unplanned {m['pause_s']:.2f} s pause broke the phrase between "
            f"“{words[region.w0]['word']}” and “{words[region.w1]['word']}” (expected ≈{m['expected_pause_s']:.2f} s)."
        )
        evidence = [
            {"metric": "Pause length", "participant": f"{m['pause_s']:.2f} s", "reference": f"{m['expected_pause_s']:.2f} s (tempo-scaled)"},
            {"metric": "Excess silence", "participant": f"{m['extra_s']:.2f} s", "reference": f"< {cfg.pause_insert_s:.2f} s"},
        ]
        math_ = f"excess = gap_participant − gap_reference × local tempo = {m['pause_s']:.2f} − {m['expected_pause_s']:.2f} = {m['extra_s']:.2f} s > {cfg.pause_insert_s:.2f} s"
        why = "A pause inside a phrase splits a single idea in two; listeners read it as a memory lapse rather than emphasis."
        tip = "Keep this phrase on one breath; if you need a pause, move it to the punctuation before or after."

    elif region.type == "pause_removal":
        what = (
            f"The rhetorical pause after “{words[region.w0]['word']}” was cut to {m['pause_s']:.2f} s "
            f"(reference ≈{m['expected_pause_s']:.2f} s), running two ideas together."
        )
        evidence = [
            {"metric": "Pause length", "participant": f"{m['pause_s']:.2f} s", "reference": f"{m['expected_pause_s']:.2f} s (tempo-scaled)"},
            {"metric": "Fraction of pause kept", "participant": f"{m['pause_kept']:.0%}", "reference": f"≥ {cfg.pause_removed_ratio:.0%}"},
        ]
        math_ = (
            f"kept = (gap_participant − 40 ms) / (gap_reference × local tempo − 40 ms) = {m['pause_kept']:.2f} "
            f"< {cfg.pause_removed_ratio:.2f}"
        )
        why = "Pauses at phrase boundaries give the audience time to absorb a point; skipping them makes the delivery feel rushed and flat."
        tip = "Mark a slash in your script here and hold silence for a full beat before continuing."
    else:  # pragma: no cover
        raise ValueError(region.type)

    spec = FLAWS[region.type]
    return {
        "type": region.type,
        "label": spec.label,
        "rubric": spec.rubric,
        "start": round(region.start, 3),
        "end": round(region.end, 3),
        "word_span": [region.w0, region.w1],
        "text": " ".join(w["word"] for w in words[region.w0 : region.w1 + 1]),
        "severity": region.severity,
        "deviation": round(region.score, 2),
        "headline": f"{spec.label} at {t}",
        "what": what,
        "evidence": evidence,
        "math": math_,
        "why": why,
        "tip": tip,
        "measured": {k: round(v, 4) for k, v in m.items()},
    }
