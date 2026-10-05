"""Deterministic planning of which flaws go where in each dataset variant.

Two families of variants are generated per baseline:

* single  - one flaw type at one severity. For a given type the *same* word span is used at every
            severity, so the five clips form a clean dose-response ladder.
* mix     - an overall-quality gradient, L1 ("almost perfect", one mild flaw) to L5 ("botched",
            five severe flaws of different types).

All randomness comes from a generator seeded by a stable hash of (baseline id, variant), so the
dataset is byte-for-byte reproducible.
"""

from __future__ import annotations

import zlib

import numpy as np

from .inject import Baseline, Flaw
from .spec import FLAWS

EDGE_WORDS = 2  # never touch the first/last words of a clip
BUFFER_WORDS = 2  # minimum distance between two flaw regions
MIX_SEVERITIES = {1: (1, 1), 2: (1, 2), 3: (2, 3), 4: (3, 4), 5: (4, 5)}

MID_PHRASE_GAP = (0.0, 0.15)  # long_pause is inserted where the speaker did *not* pause
PHRASE_PAUSE_MIN = 0.30  # pause_removal targets a real rhetorical pause


def rng_for(*key: object) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(":".join(map(str, key)).encode()))


def _free(w0: int, w1: int, occupied: set[int]) -> bool:
    return not any(i in occupied for i in range(w0 - BUFFER_WORDS, w1 + BUFFER_WORDS + 1))


def place(base: Baseline, ftype: str, severity: int, rng: np.random.Generator, occupied: set[int]) -> Flaw | None:
    """Choose a word span for one flaw, avoiding `occupied` word indices. Returns None if impossible."""
    n = len(base.words)
    lo, hi = EDGE_WORDS, n - EDGE_WORDS - 1

    if ftype in ("long_pause", "pause_removal"):
        cands = []
        for i in range(lo, hi):
            g0, g1 = base.gap(i)
            gap = g1 - g0
            ok = (
                MID_PHRASE_GAP[0] < gap <= MID_PHRASE_GAP[1]
                if ftype == "long_pause"
                else gap >= PHRASE_PAUSE_MIN
            )
            if ok and _free(i, i + 1, occupied):
                cands.append(i)
        if not cands:
            return None
        i = int(rng.choice(cands))
        flaw = Flaw(ftype, severity, i, i + 1)
    else:
        kmin, kmax = FLAWS[ftype].words
        for attempt in range(300):
            # random length first; fall back to the shortest allowed span when space is tight
            k = int(rng.integers(kmin, kmax + 1)) if attempt < 150 else kmin
            if hi - k < lo:
                continue
            w0 = int(rng.integers(lo, hi - k + 1))
            if _free(w0, w0 + k - 1, occupied):
                flaw = Flaw(ftype, severity, w0, w0 + k - 1)
                break
        else:
            return None

    occupied.update(range(flaw.w0, flaw.w1 + 1))
    return flaw


def plan_variants(base: Baseline, baseline_id: str) -> list[dict]:
    """Return [{clip_id, kind, level, flaws: [Flaw]}] for one baseline."""
    variants = []
    for ftype in FLAWS:
        flaw = place(base, ftype, 1, rng_for(baseline_id, "single", ftype), set())
        if flaw is None:
            continue
        for sev in range(1, 6):
            variants.append(
                {
                    "clip_id": f"{baseline_id}__{ftype}_s{sev}",
                    "kind": "single",
                    "level": sev,
                    "flaws": [Flaw(ftype, sev, flaw.w0, flaw.w1)],
                }
            )

    types = list(FLAWS)
    for level in range(1, 6):
        rng = rng_for(baseline_id, "mix", level)
        occupied: set[int] = set()
        flaws = []
        for ftype in rng.permutation(types):
            if len(flaws) == level:
                break
            if {ftype, *(f.type for f in flaws)} >= {"rushing", "dragging"}:
                continue  # keep each mix clip's pacing story unambiguous
            lo, hi = MIX_SEVERITIES[level]
            flaw = place(base, str(ftype), int(rng.integers(lo, hi + 1)), rng, occupied)
            if flaw is not None:
                flaws.append(flaw)
        variants.append({"clip_id": f"{baseline_id}__mix_L{level}", "kind": "mix", "level": level, "flaws": flaws})
    return variants
