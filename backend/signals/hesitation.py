"""
Hesitation signature signal calculator.

Literature anchor:
Paas & van Merriënboer (1994) — Pause duration before acting on a clear
affordance predicts subjective effort ratings. Pauses exceeding 2,000ms
before an available action indicate decision bottlenecks — the user is
unable to resolve competing action options or recognise the next step.

Bounds:
  Lower bound: 2,000ms (HESITATION_THRESHOLD_MS) — below this, pauses are
  normal reading/processing time, not decision bottlenecks.
  Upper bound: 15,000ms (HESITATION_UPPER_BOUND_MS) — above this, pauses
  likely reflect external interruption (reading a message, switching tabs,
  attending to something in the environment) rather than cognitive load.
  Pauses exceeding the upper bound are excluded from scoring and flagged
  in the signal interpretation.

This bounding is critical for unmoderated remote sessions, where the
absence of a moderator means external distractions cannot be controlled.
Applying only a lower bound would misclassify distraction as hesitation,
inflating scores in a way that is not reproducible across session contexts.

Score interpretation:
- Low score (0–30): few hesitations — clear recognition of next actions
- Mid score (31–60): moderate hesitations — some decision ambiguity
- High score (61–100): frequent or prolonged hesitations — significant bottlenecks
"""

from config import HESITATION_THRESHOLD_MS
from models import InteractionEvent

HESITATION_UPPER_BOUND_MS: int = 15_000  # pauses above this are noise/distraction


def calculate(events: list[InteractionEvent]) -> tuple[float, str]:
    """
    Compute hesitation score (0–100).

    Method:
    1. Compute inter-event gaps (time between consecutive events)
    2. Gaps in [HESITATION_THRESHOLD_MS, HESITATION_UPPER_BOUND_MS] are hesitations
    3. Gaps above HESITATION_UPPER_BOUND_MS are excluded as likely distraction
    4. Score = hesitation rate (weighted 40%) + mean hesitation duration (weighted 60%)
    """
    if len(events) < 2:
        return 0.0, "Insufficient events to compute inter-event gaps"

    sorted_events = sorted(events, key=lambda e: e.timestamp_ms)
    gaps = [
        sorted_events[i + 1].timestamp_ms - sorted_events[i].timestamp_ms
        for i in range(len(sorted_events) - 1)
    ]

    hesitations = [
        g for g in gaps
        if HESITATION_THRESHOLD_MS <= g <= HESITATION_UPPER_BOUND_MS
    ]
    excluded = [g for g in gaps if g > HESITATION_UPPER_BOUND_MS]
    hesitation_rate = len(hesitations) / len(gaps) if gaps else 0

    mean_hesitation_ms = (
        sum(hesitations) / len(hesitations) if hesitations else 0
    )

    # Normalise: rate capped at 40% = 100; mean duration capped at 10s = 100
    rate_score = min(hesitation_rate / 0.40 * 100, 100)
    duration_score = min(mean_hesitation_ms / 10_000 * 100, 100)

    score = (rate_score * 0.4) + (duration_score * 0.6)

    exclusion_note = (
        f"; {len(excluded)} gap(s) >{HESITATION_UPPER_BOUND_MS/1000:.0f}s excluded as likely distraction"
        if excluded else ""
    )

    interpretation = (
        f"{len(hesitations)} hesitations ({HESITATION_THRESHOLD_MS}–{HESITATION_UPPER_BOUND_MS}ms) "
        f"in {len(gaps)} inter-event gaps ({hesitation_rate:.1%} rate); "
        f"mean hesitation {mean_hesitation_ms:.0f}ms"
        f"{exclusion_note} "
        f"(Paas & van Merriënboer, 1994 decision bottleneck indicator)"
    )

    return round(min(score, 100), 1), interpretation