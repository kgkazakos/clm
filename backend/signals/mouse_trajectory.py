"""
Mouse trajectory irregularity signal calculator.

Literature anchor:
Guo et al. (2016) — Path efficiency ratio (straight-line distance /
actual path length) correlates with NASA-TLX mental demand subscale
(r=0.71). Irregular, inefficient mouse paths indicate attentional
switching cost — the user is scanning rather than acting with intent.

Score interpretation:
- Low score (0–30): efficient, direct paths — clear intent and orientation
- Mid score (31–60): moderate inefficiency — some scanning behaviour
- High score (61–100): highly irregular paths — significant attentional load

Note: Requires normalised x/y coordinates (0–1 range). Events without
coordinates are excluded from calculation.
"""

import math
from models import InteractionEvent


def _euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    """
    Compute mouse trajectory irregularity score (0–100).

    Method:
    1. Extract events with x/y coordinates
    2. For each consecutive pair, compute path segment length
    3. Compute straight-line distance from first to last point
    4. Path efficiency ratio = straight-line / actual path length
    5. Score = (1 - efficiency ratio) * 100
    """
    coord_events = [
        e for e in events
        if e.x is not None and e.y is not None
    ]

    if len(coord_events) < 3:
        return 0.0, "Insufficient coordinate data — fewer than 3 positioned events"

    sorted_events = sorted(coord_events, key=lambda e: e.timestamp_ms)

    # Actual path length (sum of all segments)
    actual_length = sum(
        _euclidean(
            sorted_events[i].x, sorted_events[i].y,
            sorted_events[i + 1].x, sorted_events[i + 1].y,
        )
        for i in range(len(sorted_events) - 1)
    )

    # Straight-line distance from first to last
    straight_line = _euclidean(
        sorted_events[0].x, sorted_events[0].y,
        sorted_events[-1].x, sorted_events[-1].y,
    )

    if actual_length == 0:
        return 0.0, "No mouse movement detected"

    efficiency_ratio = min(straight_line / actual_length, 1.0)
    score = (1 - efficiency_ratio) * 100

    interpretation = (
        f"Path efficiency ratio {efficiency_ratio:.2f} "
        f"(straight-line {straight_line:.3f} / actual {actual_length:.3f}) "
        f"across {len(coord_events)} positioned events "
        f"(Guo et al., 2016 attentional switching indicator)"
    )

    return round(score, 1), interpretation
