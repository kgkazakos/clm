"""
Scroll behaviour signal calculator.

Literature anchor:
Rodrigues et al. (2020) — Erratic scroll patterns (high velocity variance,
frequent direction reversals, repeated revisits to same scroll position)
correlate with spatial disorientation under extraneous load from poor
information architecture. Users who cannot locate information scroll
erratically rather than linearly.

Score interpretation:
- Low score (0–30): smooth linear scrolling — clear spatial orientation
- Mid score (31–60): moderate variance — some disorientation
- High score (61–100): erratic scrolling — significant spatial load
"""

import statistics
from models import InteractionEvent


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    """
    Compute scroll behaviour score (0–100).

    Method:
    1. Extract scroll events with value (scroll delta in px)
    2. Compute velocity variance (std deviation of scroll deltas)
    3. Count direction reversals (sign changes in consecutive deltas)
    4. Score = velocity variance score (weighted 50%) + reversal rate (weighted 50%)
    """
    scroll_events = [
        e for e in events
        if e.event_type == "scroll" and e.value is not None
    ]

    if len(scroll_events) < 3:
        return 0.0, "Insufficient scroll data — fewer than 3 scroll events"

    try:
        deltas = [float(e.value) for e in scroll_events]
    except (ValueError, TypeError):
        return 0.0, "Scroll delta values could not be parsed as numeric"

    # Velocity variance
    variance = statistics.stdev(deltas) if len(deltas) > 1 else 0

    # Direction reversals (sign changes)
    reversals = sum(
        1 for i in range(1, len(deltas))
        if deltas[i] != 0 and deltas[i - 1] != 0
        and (deltas[i] > 0) != (deltas[i - 1] > 0)
    )
    reversal_rate = reversals / (len(deltas) - 1) if len(deltas) > 1 else 0

    # Normalise: variance capped at 500px std = 100
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
