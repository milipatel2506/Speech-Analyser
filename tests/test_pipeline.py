"""End-to-end detector tests on synthetic audio with oracle word timings (no alignment model needed)."""

import json

import numpy as np
import pytest

from speech_analyser.flaws import Flaw, inject
from speech_analyser.pipeline import analyse_recording, report

from .test_inject import synthetic_baseline


@pytest.fixture(scope="module")
def base():
    b = synthetic_baseline(n_words=60, seed=1)
    return b, analyse_recording(b.y, "", b.words)


def _report(base, flaws):
    b, analysed = base
    res = inject(b, flaws, np.random.default_rng(0))
    return res, report(analysed, analyse_recording(res.audio, "", res.words))


def test_identical_delivery_is_flawless(base):
    _, analysed = base
    rep = report(analysed, analysed)
    assert rep["flaws"] == []
    assert rep["score"]["overall"] == 100.0


def test_report_is_json_serialisable_and_deterministic(base):
    _, a = _report(base, [Flaw("volume_drop", 4, 20, 28)])
    _, b = _report(base, [Flaw("volume_drop", 4, 20, 28)])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


@pytest.mark.parametrize(
    "flaw",
    [Flaw("long_pause", 4, 20, 21), Flaw("volume_drop", 5, 20, 28), Flaw("dragging", 4, 20, 28)],
    ids=lambda f: f.type,
)
def test_injected_flaw_is_grounded_in_time(base, flaw):
    res, rep = _report(base, [flaw])
    (truth,) = res.flaws
    hits = [f for f in rep["flaws"] if f["type"] == flaw.type]
    assert hits, f"{flaw.type} not detected; got {[f['type'] for f in rep['flaws']]}"
    best = max(hits, key=lambda f: min(f["end"], truth["end"]) - max(f["start"], truth["start"]))
    inter = min(best["end"], truth["end"]) - max(best["start"], truth["start"])
    union = max(best["end"], truth["end"]) - min(best["start"], truth["start"])
    assert inter / union > 0.6
    assert rep["score"]["overall"] < 100
    assert best["what"] and best["math"] and best["evidence"]
