"""Label-exactness tests for the flaw injector, on a synthetic voiced signal with known word times."""

import numpy as np
import pytest

from speech_analyser.flaws import FLAWS, Baseline, Flaw, inject
from speech_analyser.flaws.plan import plan_variants

SR = 16_000


def synthetic_baseline(n_words: int = 30, word_s: float = 0.35, gap_s: float = 0.08, seed: int = 0):
    """Harmonic 'words' (gliding 110-160 Hz pulse train) separated by quiet gaps; every 6th gap is long."""
    rng = np.random.default_rng(seed)
    pieces, words, t = [rng.standard_normal(int(0.3 * SR)) * 1e-3], [], 0.3
    for i in range(n_words):
        n = int(word_s * SR)
        f0 = np.linspace(110, 160, n) if i % 2 else np.linspace(160, 110, n)
        phase = 2 * np.pi * np.cumsum(f0) / SR
        voiced = sum(np.sin(k * phase) / k for k in range(1, 12)) * 0.2 * np.hanning(n)
        pieces.append(voiced.astype(np.float32))
        words.append({"word": f"w{i}", "start": t, "end": t + word_s})
        t += word_s
        gap = 0.5 if i % 6 == 5 else gap_s
        pieces.append(rng.standard_normal(int(gap * SR)) * 1e-3)
        t += gap
    y = np.concatenate(pieces).astype(np.float32)
    return Baseline(y, words, SR)


@pytest.fixture(scope="module")
def base():
    return synthetic_baseline()


def test_long_pause_label_matches_inserted_silence(base):
    res = inject(base, [Flaw("long_pause", 4, 10, 11)], np.random.default_rng(0))
    pause = FLAWS["long_pause"].value(4)
    (lab,) = res.flaws
    assert lab["end"] - lab["start"] == pytest.approx(pause, abs=1e-3)
    assert len(res.audio) == pytest.approx(len(base.y) + pause * SR, abs=2)
    # words before are untouched, words after shift by exactly the pause
    assert res.words[10]["end"] == pytest.approx(base.words[10]["end"], abs=1e-3)
    assert res.words[11]["start"] == pytest.approx(base.words[11]["start"] + pause, abs=1e-3)
    # the label sits inside the gap between the two words
    assert res.words[10]["end"] <= lab["start"] and lab["end"] <= res.words[11]["start"]


@pytest.mark.parametrize("ftype", ["rushing", "dragging"])
def test_tempo_changes_span_duration_by_factor(base, ftype):
    sev = 3
    res = inject(base, [Flaw(ftype, sev, 5, 12)], np.random.default_rng(0))
    factor = FLAWS[ftype].value(sev)
    orig = base.words[12]["end"] - base.words[5]["start"]
    new = res.words[12]["end"] - res.words[5]["start"]
    assert new / orig == pytest.approx(factor, rel=0.03)
    shift = res.words[20]["start"] - base.words[20]["start"]
    assert len(res.audio) / SR - len(base.y) / SR == pytest.approx(shift, abs=0.01)


def test_amplitude_and_pitch_flaws_preserve_timing(base):
    flaws = [Flaw("volume_drop", 5, 3, 8), Flaw("mumble", 5, 13, 18), Flaw("monotone", 5, 22, 27)]
    res = inject(base, flaws, np.random.default_rng(0))
    assert len(res.audio) == len(base.y)
    for w0, w1 in zip(base.words, res.words):
        assert w1["start"] == pytest.approx(w0["start"], abs=1e-4)
    i0, i1 = int(base.words[4]["start"] * SR), int(base.words[7]["end"] * SR)
    drop_db = 20 * np.log10(np.std(res.audio[i0:i1]) / np.std(base.y[i0:i1]))
    assert drop_db == pytest.approx(FLAWS["volume_drop"].value(5), abs=1.0)


def test_pause_removal_shortens_gap(base):
    i = 5  # word 5 is followed by a 0.5 s pause
    res = inject(base, [Flaw("pause_removal", 5, i, i + 1)], np.random.default_rng(0))
    new_gap = res.words[i + 1]["start"] - res.words[i]["end"]
    assert new_gap == pytest.approx(0.04, abs=0.005)


def test_overlapping_flaws_rejected(base):
    with pytest.raises(ValueError):
        inject(base, [Flaw("volume_drop", 1, 3, 9), Flaw("mumble", 1, 8, 12)], np.random.default_rng(0))


def test_plan_is_deterministic_and_non_overlapping():
    base = synthetic_baseline(n_words=90)  # real excerpts have 100-200 words
    a, b = plan_variants(base, "synthetic"), plan_variants(base, "synthetic")
    assert [(v["clip_id"], v["flaws"]) for v in a] == [(v["clip_id"], v["flaws"]) for v in b]
    for v in a:
        spans = sorted((f.w0, f.w1) for f in v["flaws"])
        assert all(s1[1] < s2[0] for s1, s2 in zip(spans, spans[1:]))
    mix = {v["level"]: len(v["flaws"]) for v in a if v["kind"] == "mix"}
    assert mix == {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
