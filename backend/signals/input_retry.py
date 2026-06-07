"""
Input retry rate signal calculator.

Literature anchor:
Sweller (1988) — Repeated input attempts on the same element indicate
working memory strain from element interactivity overload. When users
retry inputs, they are attempting to resolve a schema mismatch between
their mental model and the interface's response — a direct extraneous
load signature.

Score interpretation:
- Low score (0–30): few retries — inputs understood and accepted first time
- Mid score (31–60): moderate retries — some input ambiguity
- High score (61–100): frequent retries — significant input confusion
"""

from models import InteractionEvent

_RETRY_WINDOW_MS = 8000    # retries within 8s on same element counted as a sequence
_MIN_RETRY_COUNT = 2       # minimum repeat count to classify as retry


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    """
    Compute input retry score (0–100).

    Method:
    1. Group input events by element_id
    2. Within each element group, identify retry sequences:
       consecutive inputs within RETRY_WINDOW_MS
    3. Score = retry sequence rate (weighted 60%) + mean retry depth (weighted 40%)
    """
    input_events = [
        e for e in events
        if e.event_type == "input" and e.element_id
    ]

    if not input_events:
        return 0.0, "No input events with element identifiers detected"

    # Group by element_id
    by_element: dict[str, list[InteractionEvent]] = {}
    for e in input_events:
        by_element.setdefault(e.element_id, []).append(e)

    retry_sequences = 0
    retry_depths: list[int] = []

    for element_id, element_events in by_element.items():
        sorted_el = sorted(element_events, key=lambda x: x.timestamp_ms)
        current_sequence = 1

        for i in range(1, len(sorted_el)):
            gap = sorted_el[i].timestamp_ms - sorted_el[i - 1].timestamp_ms
            if gap <= _RETRY_WINDOW_MS:
                current_sequence += 1
            else:
                if current_sequence >= _MIN_RETRY_COUNT:
                    retry_sequences += 1
                    retry_depths.append(current_sequence)
                current_sequence = 1

        if current_sequence >= _MIN_RETRY_COUNT:
            retry_sequences += 1
            retry_depths.append(current_sequence)

    total_elements = len(by_element)
    retry_rate = retry_sequences / total_elements if total_elements > 0 else 0
    mean_depth = sum(retry_depths) / len(retry_depths) if retry_depths else 0

    # Normalise: retry rate capped at 50% = 100; depth capped at 5 = 100
    rate_score = min(retry_rate / 0.50 * 100, 100)
    depth_score = min((mean_depth - 1) / 4 * 100, 100) if mean_depth > 1 else 0

    score = (rate_score * 0.6) + (depth_score * 0.4)

    interpretation = (
        f"{retry_sequences} retry sequences across {total_elements} input elements "
        f"({retry_rate:.1%} retry rate); mean retry depth {mean_depth:.1f} "
        f"(Sweller, 1988 working memory strain indicator)"
    )

    return round(min(score, 100), 1), interpretation
