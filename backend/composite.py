"""
Composite cognitive load index calculator.

Applies theory-derived weights (config.py) to the seven signal scores.
Signals that return 0.0 due to insufficient event density (score == 0.0
AND interpretation contains "excluded from composite") are removed from
the dot product and remaining weights are renormalised to sum to 1.0.

This ensures that a session with, say, no qualifying dwell events does not
have its composite artificially deflated by a zero contribution from a
signal that simply had no data — distinct from a signal that genuinely
measured zero load.
"""

from config import SIGNAL_WEIGHTS
from models import InteractionEvent, SignalBreakdown, SignalScore
from signals import (
    dwell,
    error_recovery,
    hesitation,
    mouse_trajectory,
    scroll_behaviour,
    task_switching,
    input_retry,
)

_LITERATURE_ANCHORS: dict[str, str] = {
    "dwell_time":        "Jiang et al. (2015)",
    "error_recovery":    "Sweller (1988)",
    "hesitation":        "Paas & van Merriënboer (1994)",
    "task_switching":    "Sweller et al. (1998)",
    "mouse_trajectory":  "Guo et al. (2016)",
    "scroll_behaviour":  "Rodrigues et al. (2020)",
    "input_retry":       "Sweller (1988)",
}

_EXCLUDED_MARKER = "excluded from composite"


def _is_excluded(score: float, interpretation: str) -> bool:
    """True when a signal returned insufficient-data sentinel."""
    return score == 0.0 and _EXCLUDED_MARKER in interpretation


def calculate(events: list[InteractionEvent]) -> tuple[float, SignalBreakdown]:
    """
    Run all seven signal calculators, renormalise weights for any signals
    excluded due to insufficient event density, and compute composite index.
    """
    raw_results: dict[str, tuple[float, str]] = {
        "dwell_time":       dwell.calculate(events),
        "error_recovery":   error_recovery.calculate(events),
        "hesitation":       hesitation.calculate(events),
        "task_switching":   task_switching.calculate(events),
        "mouse_trajectory": mouse_trajectory.calculate(events),
        "scroll_behaviour": scroll_behaviour.calculate(events),
        "input_retry":      input_retry.calculate(events),
    }

    # Identify active signals (sufficient event density)
    active = {
        name for name, (score, interp) in raw_results.items()
        if not _is_excluded(score, interp)
    }

    # Renormalise weights across active signals only
    active_weight_sum = sum(SIGNAL_WEIGHTS[name] for name in active)
    renormalised: dict[str, float] = {}
    for name in raw_results:
        if name in active:
            renormalised[name] = SIGNAL_WEIGHTS[name] / active_weight_sum
        else:
            renormalised[name] = 0.0

    # Build signal scores and composite
    signal_scores: dict[str, SignalScore] = {}
    composite = 0.0

    for name, (score, interpretation) in raw_results.items():
        weight = renormalised[name]
        weighted = score * weight
        composite += weighted

        signal_scores[name] = SignalScore(
            signal=name,
            score=score,
            weight=round(weight, 4),
            weighted_contribution=round(weighted, 2),
            interpretation=interpretation,
            literature_anchor=_LITERATURE_ANCHORS[name],
        )

    breakdown = SignalBreakdown(
        dwell_time=signal_scores["dwell_time"],
        error_recovery=signal_scores["error_recovery"],
        hesitation=signal_scores["hesitation"],
        task_switching=signal_scores["task_switching"],
        mouse_trajectory=signal_scores["mouse_trajectory"],
        scroll_behaviour=signal_scores["scroll_behaviour"],
        input_retry=signal_scores["input_retry"],
    )

    return round(composite, 1), breakdown