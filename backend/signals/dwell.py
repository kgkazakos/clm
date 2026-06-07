"""
Dwell time signal calculator.

Literature anchor:
Jiang et al. (2015) — Longer dwell times on interactive elements correlate
with perceived task difficulty (r=0.65 with NASA-TLX effort subscale).
Interpretation: extended dwell indicates deliberation cost under intrinsic
or extraneous load — the user is pausing to process before acting.

Score interpretation:
- Low score (0–30): short, confident interactions — low deliberation cost
- Mid score (31–60): moderate dwell — some deliberation present
- High score (61–100): extended dwell — high deliberation cost
"""

from models import InteractionEvent


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    """
    Compute dwell time score (0–100) from interaction events.

    Method:
    1. Extract all events with a duration_ms value (clicks with hold, hovers)
    2. Compute mean dwell time across the session
    3. Normalise against a reference scale derived from Jiang et al. (2015):
       - <300ms: low load (confident, automatic interaction)
       - 300–1000ms: moderate load (deliberate but manageable)
       - >1000ms: high load (extended deliberation)
    """
    dwell_events = [e for e in events if e.duration_ms is not None and e.duration_ms > 0]

    if not dwell_events:
        return 0.0, "Insufficient dwell data — no duration-tagged events in log"

    mean_dwell = sum(e.duration_ms for e in dwell_events) / len(dwell_events)
    long_dwell_count = sum(1 for e in dwell_events if e.duration_ms > 1000)
    long_dwell_ratio = long_dwell_count / len(dwell_events)

    # Normalise mean dwell to 0–100 (cap at 3000ms = 100)
    mean_score = min(mean_dwell / 3000 * 100, 100)

    # Weight: 60% mean dwell, 40% proportion of long dwells
    score = (mean_score * 0.6) + (long_dwell_ratio * 100 * 0.4)

    interpretation = (
        f"Mean dwell {mean_dwell:.0f}ms across {len(dwell_events)} events; "
        f"{long_dwell_ratio:.0%} exceed 1000ms threshold "
        f"(Jiang et al., 2015 deliberation indicator)"
    )

    return round(min(score, 100), 1), interpretation
