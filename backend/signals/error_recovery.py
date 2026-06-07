"""
Error and recovery sequence signal calculator.

Literature anchor:
Sweller (1988) — Errors during problem solving indicate working memory
overload from poorly organised interface elements. Error recovery sequences
(error followed by corrective action within a short window) are a direct
indicator of schema incompleteness under extraneous cognitive load.

Score interpretation:
- Low score (0–30): few errors, quick recovery — manageable load
- Mid score (31–60): moderate error rate — some schema strain
- High score (61–100): frequent errors or slow recovery — significant load
"""

from models import InteractionEvent

_RECOVERY_WINDOW_MS = 5000  # 5s window after error to identify recovery attempts


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    """
    Compute error and recovery score (0–100).

    Method:
    1. Identify all error events (is_error=True or event_type='error')
    2. For each error, check if a corrective action follows within 5s
    3. Score = error rate (weighted 50%) + slow recovery rate (weighted 50%)
    """
    if not events:
        return 0.0, "No events to analyse"

    error_events = [e for e in events if e.is_error or e.event_type == "error"]
    error_rate = len(error_events) / len(events)

    # Identify slow recoveries (no corrective action within recovery window)
    slow_recoveries = 0
    for error in error_events:
        window_end = error.timestamp_ms + _RECOVERY_WINDOW_MS
        recovery_actions = [
            e for e in events
            if e.timestamp_ms > error.timestamp_ms
            and e.timestamp_ms <= window_end
            and not e.is_error
            and e.event_type in ("click", "input", "navigation")
        ]
        if not recovery_actions:
            slow_recoveries += 1

    slow_recovery_rate = slow_recoveries / len(error_events) if error_events else 0

    # Normalise: error rate capped at 30% = 100 (Sweller, 1988 threshold)
    error_score = min(error_rate / 0.30 * 100, 100)
    recovery_score = slow_recovery_rate * 100

    score = (error_score * 0.5) + (recovery_score * 0.5)

    interpretation = (
        f"{len(error_events)} error events ({error_rate:.1%} of total); "
        f"{slow_recoveries} slow recoveries (>{_RECOVERY_WINDOW_MS/1000:.0f}s) "
        f"(Sweller, 1988 schema incompleteness indicator)"
    )

    return round(min(score, 100), 1), interpretation
