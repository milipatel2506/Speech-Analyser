"""Catalogue of injectable delivery flaws and their severity ladders.

Severity 1 is "almost perfect" (a subtle slip a strong speaker might make) and severity 5 is
egregious. Each ladder is a single physical parameter so the gradient is monotonic and measurable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlawSpec:
    name: str
    label: str
    param: str  # name of the physical parameter that the ladder controls
    unit: str
    ladder: tuple[float, float, float, float, float]  # severity 1..5
    words: tuple[int, int]  # min/max words in the affected span
    rubric: str  # rubric dimension this flaw penalises
    describe: str  # ground-truth description template, formatted with {value}

    def value(self, severity: int) -> float:
        if not 1 <= severity <= 5:
            raise ValueError(f"severity must be 1..5, got {severity}")
        return self.ladder[severity - 1]


FLAWS: dict[str, FlawSpec] = {
    spec.name: spec
    for spec in [
        FlawSpec(
            name="monotone",
            label="Monotone delivery",
            param="pitch_range_kept",
            unit="ratio",
            ladder=(0.70, 0.50, 0.35, 0.20, 0.05),
            words=(8, 16),
            rubric="pitch_variety",
            describe="Pitch excursions around the speaker's median compressed to {value:.0%} of natural range",
        ),
        FlawSpec(
            name="rushing",
            label="Rushed pacing",
            param="duration_factor",
            unit="ratio",
            ladder=(0.85, 0.75, 0.65, 0.55, 0.45),
            words=(6, 14),
            rubric="pace",
            describe="Span compressed to {value:.0%} of original duration (pitch preserved)",
        ),
        FlawSpec(
            name="dragging",
            label="Dragging pacing",
            param="duration_factor",
            unit="ratio",
            ladder=(1.20, 1.40, 1.65, 1.90, 2.20),
            words=(6, 14),
            rubric="pace",
            describe="Span stretched to {value:.0%} of original duration (pitch preserved)",
        ),
        FlawSpec(
            name="long_pause",
            label="Awkward mid-phrase pause",
            param="pause_s",
            unit="s",
            ladder=(0.45, 0.70, 1.00, 1.50, 2.20),
            words=(2, 2),
            rubric="pausing",
            describe="{value:.2f} s of silence inserted inside a phrase",
        ),
        FlawSpec(
            name="pause_removal",
            label="Missing rhetorical pause",
            param="pause_kept",
            unit="ratio",
            ladder=(0.60, 0.45, 0.30, 0.15, 0.00),
            words=(2, 2),
            rubric="pausing",
            describe="Phrase-boundary pause shortened to {value:.0%} of its original length",
        ),
        FlawSpec(
            name="volume_drop",
            label="Volume drop",
            param="gain_db",
            unit="dB",
            ladder=(-4.0, -7.0, -10.0, -14.0, -19.0),
            words=(5, 12),
            rubric="energy",
            describe="Level attenuated by {value:.0f} dB over the span",
        ),
        FlawSpec(
            name="mumble",
            label="Mumbled articulation",
            param="lowpass_hz",
            unit="Hz",
            ladder=(5000.0, 3800.0, 2800.0, 2000.0, 1400.0),
            words=(4, 10),
            rubric="clarity",
            describe="High-frequency articulation energy removed above {value:.0f} Hz",
        ),
    ]
}

# Extra gain applied with mumbling so it also sounds less projected.
MUMBLE_GAIN_DB = (-1.0, -2.0, -3.0, -4.0, -5.0)
