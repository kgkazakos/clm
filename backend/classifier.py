"""
Deterministic CLT load type classifier — Layer 1.

Classifies dominant cognitive load type using signal pattern heuristics
derived from Sweller's Cognitive Load Theory taxonomy.

EXACT THRESHOLDS (deterministic — no qualitative language):
  HIGH  : score ≥ 50  (upper half of normalised 0–100 range)
  MEDIUM: score 25–49 (lower-middle range)
  LOW   : score < 25  (bottom quarter)

These thresholds are provisional pending the N=20 validation study.
PCA on signal scores against NASA-TLX subscale ratings will determine
whether empirically grounded cutoffs differ from these heuristic values.

CLASSIFICATION RULES:

  OVERLOAD (High Intrinsic + High Extraneous):
  Both intrinsic complexity signals (hesitation ≥ 50 AND dwell ≥ 50)
  AND at least one extraneous interface signal (error_recovery, task_switching,
  or input_retry ≥ 50) are simultaneously elevated. Per CLT's additive model
  (Sweller, 1988), intrinsic and extraneous load sum to total working memory
  demand. Co-elevation of both types represents the most critical failure state:
  the interface is adding unnecessary load on top of an already complex task.
  This is cognitively distinct from "mixed" or "uncertain" — it is Overload.

  EXTRANEOUS (Interface-driven load, no intrinsic co-elevation):
  One or more interface obstruction signals ≥ 50 (error_recovery, task_switching,
  input_retry), with hesitation < 50 OR dwell < 50 (no clear intrinsic signature).

  INTRINSIC (Task complexity, no interface obstruction):
  Deliberation signals both elevated (hesitation ≥ 50 AND dwell ≥ 50) with
  all interface obstruction signals < 50.

  GERMANE (Productive schema-building):
  Moderate hesitation (25 ≤ hesitation < 50), low error recovery (< 25),
  low input retry (< 25), and moderate mouse trajectory (< 50).
  Rare in short sessions; indicates engaged, efficient learning.

  INCONCLUSIVE (No dominant pattern):
  Signal pattern does not meet any of the above thresholds. Composite index
  is low-to-moderate with no specific signals sufficiently elevated to
  support a classification. Researcher interpretation required.

Note on MIXED vs OVERLOAD/INCONCLUSIVE:
The previous MIXED classification conflated two meaningfully different states
that CLT treats as distinct. OVERLOAD is not "uncertain" — it is the state
where total cognitive demand most likely exceeds working memory capacity.
INCONCLUSIVE is the appropriate label when signals are genuinely ambiguous.
"""

from models import LoadType, SignalBreakdown

# ─── Exact numeric thresholds ─────────────────────────────────────────────────

HIGH:   float = 50.0   # score ≥ 50 → High band
MEDIUM: float = 25.0   # score ≥ 25 → Medium band; score < 25 → Low band


def _band(score: float) -> str:
    if score >= HIGH:   return "High"
    if score >= MEDIUM: return "Medium"
    return "Low"


def classify(breakdown: SignalBreakdown) -> tuple[LoadType, str]:
    """
    Classify dominant CLT load type from signal breakdown.
    All threshold comparisons use exact numeric values defined above.

    Returns:
        load_type: the classified LoadType
        reasoning: one-sentence description of the signal pattern
    """
    d  = breakdown.dwell_time.score        # deliberation cost
    er = breakdown.error_recovery.score    # interface obstruction
    h  = breakdown.hesitation.score        # decision bottleneck
    ts = breakdown.task_switching.score    # split-attention
    mt = breakdown.mouse_trajectory.score  # attentional switching
    sb = breakdown.scroll_behaviour.score  # spatial disorientation
    ir = breakdown.input_retry.score       # working memory strain

    # ── Intrinsic signal pattern ──────────────────────────────────────────────
    # Both deliberation signals must be in the High band
    intrinsic_elevated = (h >= HIGH and d >= HIGH)

    # ── Extraneous signal pattern ─────────────────────────────────────────────
    # Any single interface obstruction signal in the High band
    extraneous_signals = {
        "error_recovery": er >= HIGH,
        "task_switching":  ts >= HIGH,
        "input_retry":     ir >= HIGH,
    }
    extraneous_count = sum(extraneous_signals.values())
    extraneous_names = [k for k, v in extraneous_signals.items() if v]

    # ── Germane pattern ───────────────────────────────────────────────────────
    germane = (
        MEDIUM <= h < HIGH and    # moderate hesitation
        er < MEDIUM and           # low error recovery
        ir < MEDIUM and           # low input retry
        mt < HIGH                 # moderate trajectory
    )

    # ── Classification ────────────────────────────────────────────────────────

    # OVERLOAD: intrinsic AND extraneous both elevated simultaneously
    # Per CLT additive model — this is the highest severity state
    if intrinsic_elevated and extraneous_count >= 1:
        return (
            LoadType.OVERLOAD,
            f"Intrinsic load signals (hesitation {h:.0f} ≥ {HIGH:.0f}, "
            f"dwell {d:.0f} ≥ {HIGH:.0f}) and extraneous signal(s) "
            f"({', '.join(f'{n} {breakdown.__dict__[n].score:.0f}' for n in extraneous_names)}) "
            f"are simultaneously in the High band (≥ {HIGH:.0f}). "
            f"Per CLT's additive model, total working memory demand likely "
            f"approaches or exceeds capacity."
        )

    # EXTRANEOUS: interface obstruction without intrinsic co-elevation
    if extraneous_count >= 1 and not intrinsic_elevated:
        return (
            LoadType.EXTRANEOUS,
            f"Interface obstruction signal(s) in the High band (≥ {HIGH:.0f}): "
            f"{', '.join(extraneous_names)}. "
            f"Deliberation signals below High threshold "
            f"(hesitation {h:.0f}, dwell {d:.0f}), "
            f"indicating interface-driven load rather than task complexity."
        )

    # INTRINSIC: deliberation elevated, no interface obstruction
    if intrinsic_elevated and extraneous_count == 0:
        return (
            LoadType.INTRINSIC,
            f"Deliberation signals in the High band: "
            f"hesitation {h:.0f} ≥ {HIGH:.0f}, dwell {d:.0f} ≥ {HIGH:.0f}. "
            f"All interface obstruction signals below High threshold "
            f"(error_recovery {er:.0f}, task_switching {ts:.0f}, "
            f"input_retry {ir:.0f}), indicating task complexity "
            f"rather than interface failure."
        )

    # GERMANE: moderate hesitation, low errors, moderate efficiency
    if germane:
        return (
            LoadType.GERMANE,
            f"Hesitation in the Medium band ({h:.0f}, {MEDIUM:.0f}–{HIGH:.0f}), "
            f"error recovery below Medium ({er:.0f} < {MEDIUM:.0f}), "
            f"and input retry below Medium ({ir:.0f} < {MEDIUM:.0f}). "
            f"Pattern consistent with productive schema-building load."
        )

    # INCONCLUSIVE: no threshold met
    return (
        LoadType.INCONCLUSIVE,
        f"No signal pattern meets the classification thresholds "
        f"(High ≥ {HIGH:.0f}, Medium ≥ {MEDIUM:.0f}). "
        f"Scores: error_recovery {er:.0f}, hesitation {h:.0f}, "
        f"task_switching {ts:.0f}, input_retry {ir:.0f}, dwell {d:.0f}. "
        f"Researcher interpretation required."
    )