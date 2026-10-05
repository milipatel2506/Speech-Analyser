# Detector evaluation (IoU ≥ 0.3, full re-alignment)

| Flaw | Sev 1 | Sev 2 | Sev 3 | Sev 4 | Sev 5 | Recall | IoU | Onset err (ms) | Offset err (ms) | Severity MAE |
|---|---|---|---|---|---|---|---|---|---|---|
| Monotone delivery | 100% | 100% | 100% | 100% | 100% | 100% | 0.84 | 308 | 669 | 0.09 |
| Rushed pacing | 90% | 100% | 89% | 100% | 100% | 95% | 0.89 | 185 | 200 | 0.05 |
| Dragging pacing | 71% | 100% | 100% | 100% | 100% | 95% | 0.95 | 122 | 176 | 0.03 |
| Awkward mid-phrase pause | 100% | 100% | 100% | 92% | 100% | 98% | 0.92 | 34 | 43 | 0.00 |
| Missing rhetorical pause | 0% | 89% | 100% | 100% | 100% | 80% | 0.98 | 6 | 8 | 0.17 |
| Volume drop | 100% | 100% | 100% | 100% | 100% | 100% | 0.98 | 88 | 5 | 0.04 |
| Mumbled articulation | 33% | 100% | 100% | 100% | 100% | 90% | 0.98 | 3 | 61 | 0.42 |

**Overall:** recall 94%, mean IoU 0.93, onset error 114 ms, offset error 180 ms, false positives 0.25/min.

**Score vs quality level (Spearman ρ):** mix clips -0.97, Dragging pacing -0.952, Awkward mid-phrase pause -0.882, Monotone delivery -0.946, Mumbled articulation -0.941, Missing rhetorical pause -0.938, Rushed pacing -0.909, Volume drop -0.907

| Baseline | Set | Recall | IoU | Onset err (ms) | Offset err (ms) | False pos./min |
|---|---|---|---|---|---|---|
| `clinton_1995` | tuning | 94% | 0.93 | 101 | 148 | 0.05 |
| `fdr_1933` | tuning | 92% | 0.96 | 65 | 72 | 0.32 |
| `harris_2024` | held-out | 94% | 0.94 | 152 | 243 | 0.47 |
| `jfk_1961` | held-out | 96% | 0.94 | 137 | 188 | 0.34 |
| `obama_2009` | held-out | 90% | 0.90 | 141 | 158 | 0.24 |
| `reagan_1981` | held-out | 98% | 0.92 | 86 | 264 | 0.11 |

**Held-out speeches only:** recall 94%, IoU 0.93, false positives 0.28/min.
