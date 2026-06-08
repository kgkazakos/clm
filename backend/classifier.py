"""
Deterministic CLT load type classifier — Layer 1.

Classifies dominant cognitive load type using signal pattern heuristics
derived from Sweller's Cognitive Load Theory taxonomy. This is an
algorithmic decision tree, not an LLM call.

Rationale for moving classification to Layer 1:
If the classification logic maps directly from observable telemetry
patterns to CLT load types — as it does here — a deterministic heuristic
is preferable to an LLM for this task. It is faster, cheaper, reproducible,
and eliminates hallucination risk. The LLM's generative strengths are
reserved for Layer 2: producing the researcher hypothesis, analysing task
context, and surfacing relevant prior literature.

Classification rules:
These rules encode the signal-to-load-type mappings from CLT literature.
They are heuristic, not exhaustive — real sessions often present mixed
signals. The MIXED type is the correct classification when no single type
clearly dominates.

  INTRINSIC: Load from task complexity, not interface failure.
  Signature: high hesitation AND high dwell, with low error rate.
  Interpretation: user is deliberating carefully on complex content,
  not struggling with the interface.

  EXTRANEOUS: Load from interface design failures.
  Signature: high error_recovery OR high task_switching OR high input_retry.
  Interpretation: interface is obstructing task completion — errors,
  repeated navigation, or repeated inputs signal schema mismatch with UI.

  GERMANE: Productive schema-building load.
  Signature: moderate hesitation, low errors, moderate mouse efficiency.
  Interpretation: user is engaged and building understanding, not struggling.
  This is the rarest classification in short sessions.

  MIXED: Multiple load sources co-present, no single type dominates.
  Signature: signals from multiple categories above threshold simultaneously,
  or no signals sufficiently elevated to classify.
"""

from models import LoadType, SignalBreakdown


# ─── Classification thresholds ────────────────────────────────────────────────
# These are heuristic thresholds, not empirically derived cutoffs.
# They should be treated as provisional pending the N=20 validation study.

_HIGH   = 50.0   # signal score above this is considered elevated
_MEDIUM = 30.0   # signal score above this is considered moderate
_LOW    = 20.0   # signal score below this is considered low


def classify(breakdown: SignalBreakdown) -> tuple[LoadType, str]:
    """
    Classify dominant CLT load type from signal breakdown.

    Returns:
        load_type: the classified LoadType
        reasoning: a one-sentence description of the signal pattern rationale
    """
    d  = breakdown.dwell_time.score
    er = breakdown.error_recovery.score
    h  = breakdown.hesitation.score
    ts = breakdown.task_switching.score
    mt = breakdown.mouse_trajectory.score
    sb = breakdown.scroll_behaviour.score
    ir = breakdown.input_retry.score

    # ── Extraneous indicators: interface obstruction ───────────────────────────
    # Any of these signals being highly elevated suggests extraneous load.
    extraneous_signals = [
        ("error_recovery", er >= _HIGH),
        ("task_switching",  ts >= _HIGH),
        ("input_retry",     ir >= _HIGH),
    ]
    extraneous_count = sum(1 for _, v in extraneous_signals if v)
    extraneous_names = [name for name, v in extraneous_signals if v]

    # ── Intrinsic indicators: task complexity ─────────────────────────────────
    # High deliberation (dwell + hesitation) with low error rate suggests
    # the user is carefully processing complex content, not fighting the UI.
    intrinsic = (
        h >= _MEDIUM and
        d >= _HIGH and
        er < _LOW
    )

    # ── Germane indicators: productive schema-building ────────────────────────
    # Moderate hesitation with low errors and moderate mouse efficiency.
    # Germane load is desirable — user is actively learning/building models.
    germane = (
        _LOW <= h < _HIGH and
        er < _LOW and
        mt < _HIGH and
        ir < _LOW
    )

    # ── Classification decision ────────────────────────────────────────────────

    if extraneous_count >= 2:
        return (
            LoadType.EXTRANEOUS,
            f"Multiple interface obstruction signals elevated "
            f"({', '.join(extraneous_names)}), indicating extraneous load "
            f"from design failures rather than task complexity."
        )

    if extraneous_count == 1 and not intrinsic:
        return (
            LoadType.EXTRANEOUS,
            f"{extraneous_names[0].replace('_', ' ').title()} is elevated "
            f"with no clear intrinsic load signature, suggesting "
            f"interface-driven extraneous load."
        )

    if intrinsic and extraneous_count == 0:
        return (
            LoadType.INTRINSIC,
            f"High deliberation signals (dwell: {d:.0f}, hesitation: {h:.0f}) "
            f"with low error rate ({er:.0f}) indicate intrinsic load "
            f"from task complexity rather than interface failure."
        )

    if germane and extraneous_count == 0 and not intrinsic:
        return (
            LoadType.GERMANE,
            f"Moderate hesitation ({h:.0f}) with low errors ({er:.0f}) "
            f"and moderate trajectory ({mt:.0f}) indicates productive "
            f"schema-building load."
        )

    if extraneous_count >= 1 and intrinsic:
        return (
            LoadType.MIXED,
            f"Both intrinsic (dwell: {d:.0f}, hesitation: {h:.0f}) and "
            f"extraneous ({', '.join(extraneous_names)}) signals are elevated, "
            f"indicating co-present load sources."
        )

    return (
        LoadType.MIXED,
        f"No single load type clearly dominates the signal pattern "
        f"(error_recovery: {er:.0f}, hesitation: {h:.0f}, "
        f"task_switching: {ts:.0f}, input_retry: {ir:.0f}). "
        f"Researcher interpretation recommended."
    )