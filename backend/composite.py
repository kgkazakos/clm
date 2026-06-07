"""
Composite cognitive load index calculator.

Applies theory-derived weights (defined in config.py) to the seven
signal scores to produce a single composite index (0–100).

The weighting rationale is documented in config.py with full literature
citations. This module is intentionally simple — the intellectual
contribution is in the signal calculators and the weight derivation,
not in the aggregation arithmetic.
"""

from config import SIGNAL_WEIGHTS
from models import (
    InteractionEvent,
    SignalBreakdown,
    SignalScore,
)
from signals import (
    dwell,
    error_recovery,
    hesitation,
    task_switching,
    mouse_trajectory,
    scroll_behaviour,
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


def calculate(events: list[InteractionEvent]) -> tuple[float, SignalBreakdown]:
    """
    Run all seven signal calculators and produce the composite index.

    Returns:
        composite_index: float (0–100)
        breakdown: SignalBreakdown with per-signal scores and metadata
    """
    results: dict[str, tuple[float, str]] = {
        "dwell_time":       dwell.calculate(events),
        "error_recovery":   error_recovery.calculate(events),
        "hesitation":       hesitation.calculate(events),
        "task_switching":   task_switching.calculate(events),
        "mouse_trajectory": mouse_trajectory.calculate(events),
        "scroll_behaviour": scroll_behaviour.calculate(events),
        "input_retry":      input_retry.calculate(events),
    }

    signal_scores: dict[str, SignalScore] = {}
    composite = 0.0

    for signal_name, (score, interpretation) in results.items():
        weight = SIGNAL_WEIGHTS[signal_name]
        weighted = score * weight
        composite += weighted

        signal_scores[signal_name] = SignalScore(
            signal=signal_name,
            score=score,
            weight=weight,
            weighted_contribution=round(weighted, 2),
            interpretation=interpretation,
            literature_anchor=_LITERATURE_ANCHORS[signal_name],
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
