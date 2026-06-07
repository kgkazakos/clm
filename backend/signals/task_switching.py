"""
Task-switching frequency signal calculator.

Literature anchor:
Sweller et al. (1998) — The split-attention effect demonstrates that
switching between information sources increases extraneous cognitive load.
High task-switching frequency (rapid screen-to-screen navigation)
indicates interrupted processing — the user cannot maintain context
within a single screen and must constantly re-orient.

Score interpretation:
- Low score (0–30): linear navigation — low split-attention load
- Mid score (31–60): moderate switching — some context fragmentation
- High score (61–100): rapid frequent switching — high split-attention load
"""

from models import InteractionEvent

_RAPID_SWITCH_THRESHOLD_MS = 3000  # switches within 3s classified as rapid


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    """
    Compute task-switching score (0–100).

    Method:
    1. Identify navigation events that change screen_id
    2. Compute switch rate (navigation events / total events)
    3. Identify rapid switches (screen change within 3s of previous switch)
    4. Score = switch rate (weighted 40%) + rapid switch rate (weighted 60%)
    """
    if not events:
        return 0.0, "No events to analyse"

    navigation_events = [
        e for e in events
        if e.event_type == "navigation" and e.screen_id
    ]

    if not navigation_events:
        return 0.0, "No navigation events detected — cannot compute task-switching"

    # Count actual screen changes
    screen_changes: list[InteractionEvent] = []
    prev_screen = None
    for e in sorted(navigation_events, key=lambda x: x.timestamp_ms):
        if e.screen_id != prev_screen:
            screen_changes.append(e)
            prev_screen = e.screen_id

    switch_rate = len(screen_changes) / len(events)

    # Identify rapid switches
    rapid_switches = 0
    for i in range(1, len(screen_changes)):
        gap = screen_changes[i].timestamp_ms - screen_changes[i - 1].timestamp_ms
        if gap < _RAPID_SWITCH_THRESHOLD_MS:
            rapid_switches += 1

    rapid_switch_rate = rapid_switches / len(screen_changes) if screen_changes else 0

    # Normalise: switch rate capped at 20% = 100
    rate_score = min(switch_rate / 0.20 * 100, 100)
    rapid_score = rapid_switch_rate * 100

    score = (rate_score * 0.4) + (rapid_score * 0.6)

    interpretation = (
        f"{len(screen_changes)} screen changes ({switch_rate:.1%} of events); "
        f"{rapid_switches} rapid switches (<{_RAPID_SWITCH_THRESHOLD_MS/1000:.0f}s) "
        f"(Sweller et al., 1998 split-attention effect indicator)"
    )

    return round(min(score, 100), 1), interpretation
