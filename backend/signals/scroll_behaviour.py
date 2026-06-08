"""
Scroll behaviour signal calculator.

Literature anchor:
Rodrigues et al. (2020) — Erratic scroll patterns (high velocity variance,
frequent direction reversals) correlate with spatial disorientation under
extraneous load from poor information architecture.

Minimum event density:
Requires MIN_SIGNAL_EVENTS qualifying scroll events. Sessions with fewer
scroll events return 0.0 and are excluded from the composite.
"""

import statistics

from config import MIN_SIGNAL_EVENTS
from models import InteractionEvent

_INSUFFICIENT = (
    0.0,
    f"Insufficient scroll data — fewer than {MIN_SIGNAL_EVENTS} "
    f"scroll events; signal excluded from composite"
)


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    scroll_events = [
        e for e in events
        if e.event_type == "scroll" and e.value is not None
    ]

    if len(scroll_events) < MIN_SIGNAL_EVENTS:
        return _INSUFFICIENT

    try:
        deltas = [float(e.value) for e in scroll_events]
    except (ValueError, TypeError):
        return 0.0, "Scroll delta values could not be parsed as numeric"

    variance = statistics.stdev(deltas) if len(deltas) > 1 else 0
    reversals = sum(
        1 for i in range(1, len(deltas))
        if deltas[i] != 0 and deltas[i - 1] != 0
        and (deltas[i] > 0) != (deltas[i - 1] > 0)
    )
    reversal_rate = reversals / (len(deltas) - 1) if len(deltas) > 1 else 0

    variance_score = min(variance / 500 * 100, 100)
    reversal_score = min(reversal_rate * 100, 100)
    score = (variance_score * 0.5) + (reversal_score * 0.5)

    interpretation = (
        f"{len(scroll_events)} scroll events; "
        f"velocity std {variance:.1f}px; "
        f"{reversals} direction reversals ({reversal_rate:.1%} rate) "
        f"(Rodrigues et al., 2020 spatial disorientation indicator)"
    )

    return round(min(score, 100), 1), interpretation