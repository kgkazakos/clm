"""
Dwell time signal calculator.

Literature anchor:
Jiang et al. (2015) — Longer dwell times on interactive elements correlate
with perceived task difficulty (r=0.65 with NASA-TLX effort subscale).

Minimum event density:
Requires MIN_SIGNAL_EVENTS qualifying dwell events. Sessions with fewer
dwell-tagged events return 0.0 and are excluded from the composite.
This prevents two unusually long dwell events from producing a score of
100.0 that skews the aggregate — a vulnerability observed in the
integration study where n=2 dwell events produced a score of 100.0.
"""

from config import MIN_SIGNAL_EVENTS
from models import InteractionEvent

_INSUFFICIENT = (
    0.0,
    f"Insufficient dwell data — fewer than {MIN_SIGNAL_EVENTS} "
    f"duration-tagged events; signal excluded from composite"
)


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    dwell_events = [
        e for e in events
        if e.duration_ms is not None and e.duration_ms > 0
    ]

    if len(dwell_events) < MIN_SIGNAL_EVENTS:
        return _INSUFFICIENT

    mean_dwell = sum(e.duration_ms for e in dwell_events) / len(dwell_events)
    long_dwell_count = sum(1 for e in dwell_events if e.duration_ms > 1000)
    long_dwell_ratio = long_dwell_count / len(dwell_events)

    mean_score = min(mean_dwell / 3000 * 100, 100)
    score = (mean_score * 0.6) + (long_dwell_ratio * 100 * 0.4)

    interpretation = (
        f"Mean dwell {mean_dwell:.0f}ms across {len(dwell_events)} events; "
        f"{long_dwell_ratio:.0%} exceed 1000ms threshold "
        f"(Jiang et al., 2015 deliberation indicator)"
    )

    return round(min(score, 100), 1), interpretation