"""Report generation — JSON and Markdown outputs."""

import json
from datetime import datetime
from pathlib import Path

from models import AnalysisResult, LoadType


_LOAD_TYPE_LABELS = {
    LoadType.INTRINSIC:  "INTRINSIC — Inherent task complexity",
    LoadType.EXTRANEOUS: "EXTRANEOUS — Interface design load",
    LoadType.GERMANE:    "GERMANE — Productive schema-building",
    LoadType.MIXED:      "MIXED — Multiple load sources",
}

_INDEX_BAND = [
    (80, "🔴 Very High"),
    (60, "🟠 High"),
    (40, "🟡 Moderate"),
    (20, "🟢 Low"),
    (0,  "🟢 Very Low"),
]


def _band(index: float) -> str:
    for threshold, label in _INDEX_BAND:
        if index >= threshold:
            return label
    return "🟢 Very Low"


def write_json(result: AnalysisResult, output_dir: Path) -> Path:
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "session_id": result.session_id,
        "format_used": result.format_used.value,
        "context": result.context.model_dump(),
        "measurement": {
            "composite_index": result.composite_index,
            "band": _band(result.composite_index),
            "event_count": result.event_count,
            "duration_ms": result.duration_ms,
            "signals": {
                s: {
                    "score": getattr(result.signal_breakdown, s).score,
                    "weight": getattr(result.signal_breakdown, s).weight,
                    "weighted_contribution": getattr(result.signal_breakdown, s).weighted_contribution,
                    "interpretation": getattr(result.signal_breakdown, s).interpretation,
                    "literature_anchor": getattr(result.signal_breakdown, s).literature_anchor,
                }
                for s in [
                    "dwell_time", "error_recovery", "hesitation",
                    "task_switching", "mouse_trajectory",
                    "scroll_behaviour", "input_retry",
                ]
            },
        },
        "interpretation": {
            "dominant_load_type": result.agent_output.dominant_load_type.value,
            "confidence": result.agent_output.confidence,
            "classification_reasoning": result.agent_output.classification_reasoning,
            "hypothesis": result.agent_output.hypothesis,
            "hypothesis_space": [
                h.model_dump() for h in result.agent_output.hypothesis_space
            ],
            "uncertainty_flags": result.agent_output.uncertainty_flags,
        },
    }

    path = output_dir / f"clm_report_{result.session_id}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def write_markdown(result: AnalysisResult, output_dir: Path) -> Path:
    agent = result.agent_output
    breakdown = result.signal_breakdown

    lines = [
        "# Cognitive Load Monitor — Analysis Report",
        "",
        f"**Session:** {result.session_id}  ",
        f"**Format:** {result.format_used.value}  ",
        f"**Task:** {result.context.task_description or 'Not provided'}  ",
        f"**Interface:** {result.context.interface_type}  ",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "---",
        "",
        "## Composite Cognitive Load Index",
        "",
        f"# {result.composite_index} / 100 — {_band(result.composite_index)}",
        "",
        f"Based on {result.event_count} interaction events "
        f"over {result.duration_ms / 1000:.1f}s session",
        "",
        "---",
        "",
        "## Signal Breakdown",
        "",
        "| Signal | Score | Weight | Weighted | Literature Anchor |",
        "|--------|-------|--------|----------|-------------------|",
    ]

    for signal_name in [
        "dwell_time", "error_recovery", "hesitation",
        "task_switching", "mouse_trajectory",
        "scroll_behaviour", "input_retry",
    ]:
        s = getattr(breakdown, signal_name)
        lines.append(
            f"| {signal_name.replace('_', ' ').title()} "
            f"| {s.score} | {s.weight} | {s.weighted_contribution} "
            f"| {s.literature_anchor} |"
        )

    lines += [
        "",
        "---",
        "",
        "## AI Interpretation (Hypothesis — Not a Finding)",
        "",
        f"**Dominant load type:** {_LOAD_TYPE_LABELS[agent.dominant_load_type]}  ",
        f"**Confidence:** {agent.confidence}",
        "",
        f"**Classification reasoning:** {agent.classification_reasoning}",
        "",
        f"**Researcher hypothesis:** _{agent.hypothesis}_",
        "",
        "---",
        "",
        "## Hypothesis Space",
        "",
        "_Prior work addressing the dominant load type. "
        "For researcher evaluation before selecting intervention direction._",
        "",
    ]

    for entry in agent.hypothesis_space:
        lines += [
            f"- **{entry.intervention}**  ",
            f"  _{entry.citation}_",
            "",
        ]

    if agent.uncertainty_flags:
        lines += [
            "---",
            "",
            "## ⚠️ Uncertainty Flags",
            "",
        ]
        for flag in agent.uncertainty_flags:
            lines.append(f"- {flag}")
        lines.append("")

    path = output_dir / f"clm_report_{result.session_id}.md"
    path.write_text("\n".join(lines))
    return path
