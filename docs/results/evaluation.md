# Detector evaluation (IoU ≥ 0.3, full re-alignment)

| Flaw | Sev 1 | Sev 2 | Sev 3 | Sev 4 | Sev 5 | Recall | IoU | Onset err (ms) | Offset err (ms) | Severity MAE |
|---|---|---|---|---|---|---|---|---|---|---|
| Monotone delivery | 100% | 100% | 100% | 100% | 100% | 100% | 0.84 | 308 | 643 | 0.11 |
| Rushed pacing | 70% | 100% | 100% | 100% | 100% | 93% | 0.90 | 107 | 189 | 0.05 |
| Dragging pacing | 100% | 100% | 100% | 100% | 100% | 100% | 0.94 | 178 | 201 | 0.05 |
| Awkward mid-phrase pause | 100% | 100% | 100% | 92% | 100% | 98% | 0.92 | 34 | 43 | 0.00 |
| Missing rhetorical pause | 0% | 89% | 100% | 100% | 100% | 80% | 0.98 | 6 | 8 | 0.17 |
| Volume drop | 100% | 100% | 100% | 100% | 100% | 100% | 0.98 | 88 | 5 | 0.04 |
| Mumbled articulation | 33% | 100% | 100% | 100% | 100% | 90% | 0.98 | 3 | 61 | 0.42 |

**Overall:** recall 94%, mean IoU 0.93, onset error 110 ms, offset error 177 ms, false positives 0.14/min.

**Score vs quality level (Spearman ρ):** mix clips -0.961, Dragging pacing -0.943, Awkward mid-phrase pause -0.882, Monotone delivery -0.949, Mumbled articulation -0.936, Missing rhetorical pause -0.943, Rushed pacing -0.893, Volume drop -0.904

| Baseline | Set | Recall | IoU | Onset err (ms) | Offset err (ms) | False pos./min |
|---|---|---|---|---|---|---|
| `clinton_1995` | tuning | 94% | 0.94 | 127 | 98 | 0.05 |
| `fdr_1933` | tuning | 92% | 0.95 | 71 | 104 | 0.23 |
| `harris_2024` | held-out | 96% | 0.93 | 146 | 290 | 0.25 |
| `jfk_1961` | held-out | 92% | 0.96 | 53 | 189 | 0.08 |
| `obama_2009` | held-out | 94% | 0.90 | 172 | 163 | 0.22 |
| `reagan_1981` | held-out | 98% | 0.93 | 92 | 214 | 0.07 |

**Held-out speeches only:** recall 95%, IoU 0.93, false positives 0.15/min.
