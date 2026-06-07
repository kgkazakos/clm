"""
Layer 2: AI interpretation agent — multi-provider.

Supports Gemini, OpenAI, and Anthropic as interpretation backends.
Provider is set via LLM_PROVIDER in .env.

The interpretation task is identical across providers:
- Receive composite index + signal breakdown + session context
- Classify dominant CLT load type (intrinsic / extraneous / germane / mixed)
- Generate researcher hypothesis
- Surface hypothesis space from prior literature
- Flag measurement uncertainty

Output is explicitly a hypothesis for researcher evaluation — not a finding.
"""

import json
import re
from typing import Any

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from models import (
    AgentOutput,
    HypothesisSpaceEntry,
    LoadType,
    SessionContext,
    SignalBreakdown,
)

# ─── Shared prompt ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a cognitive load theorist assisting a UX researcher.

You will receive:
1. A composite cognitive load index (0-100)
2. A breakdown of seven telemetry signals, each with a score and interpretation
3. Session context (task description, interface type)

Your task is to reason about which type of cognitive load is dominant,
following Sweller's Cognitive Load Theory taxonomy:

- INTRINSIC: Load from inherent task complexity — the task itself is difficult
  regardless of interface design. Signals: high hesitation + high dwell time
  with low error rate suggests deliberate, careful processing of complex content.

- EXTRANEOUS: Load introduced by interface design failures — the task is being
  made harder than necessary by poor design. Signals: high error recovery +
  high task switching + high input retry suggests the interface is obstructing
  task completion.

- GERMANE: Productive cognitive effort invested in building schemas and
  understanding — this is desirable load. Signals: moderate hesitation with
  low error rate and efficient mouse paths suggests the user is learning and
  building mental models.

- MIXED: No single type clearly dominates — multiple load sources co-present.

Output ONLY a valid JSON object with this exact structure:
{
  "dominant_load_type": "intrinsic" | "extraneous" | "germane" | "mixed",
  "classification_reasoning": "2-3 sentence reasoning citing specific signal values",
  "hypothesis": "One precise sentence stating the researcher hypothesis. Frame as hypothesis, not finding.",
  "hypothesis_space": [
    {
      "intervention": "Description of intervention from prior work",
      "citation": "Author (Year) — brief title or finding",
      "load_type_addressed": "intrinsic" | "extraneous" | "germane"
    }
  ],
  "uncertainty_flags": ["List of specific uncertainty flags where measurement may be unreliable"],
  "confidence": "High" | "Moderate" | "Low"
}

Rules:
- hypothesis_space must contain 2-4 entries from real HCI/CLT literature
- Each entry must address the dominant load type identified
- Frame interventions as prior work findings, not prescriptions
- uncertainty_flags must be specific and actionable for the researcher
- Do NOT use the words "frustration", "Say-Do", or "divergence"
- Return ONLY valid JSON — no markdown fences, no preamble"""


def _format_breakdown(breakdown: SignalBreakdown) -> str:
    signals = [
        breakdown.dwell_time, breakdown.error_recovery, breakdown.hesitation,
        breakdown.task_switching, breakdown.mouse_trajectory,
        breakdown.scroll_behaviour, breakdown.input_retry,
    ]
    return "\n".join(
        f"  {s.signal} (weight={s.weight}): score={s.score}/100\n"
        f"    {s.interpretation}"
        for s in signals
    )


def _build_user_message(
    composite_index: float,
    breakdown: SignalBreakdown,
    context: SessionContext,
) -> str:
    return (
        f"Composite cognitive load index: {composite_index}/100\n\n"
        f"Signal breakdown:\n{_format_breakdown(breakdown)}\n\n"
        f"Session context:\n"
        f"  Task: {context.task_description or 'Not provided'}\n"
        f"  Interface type: {context.interface_type}\n"
        f"  Participant: {context.participant_id or 'Anonymous'}\n\n"
        f"Classify the dominant load type and generate the researcher hypothesis."
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _parse_output(raw: dict) -> AgentOutput:
    load_type_map = {
        "intrinsic":  LoadType.INTRINSIC,
        "extraneous": LoadType.EXTRANEOUS,
        "germane":    LoadType.GERMANE,
        "mixed":      LoadType.MIXED,
    }
    return AgentOutput(
        dominant_load_type=load_type_map.get(
            raw["dominant_load_type"].lower(), LoadType.MIXED
        ),
        classification_reasoning=raw["classification_reasoning"],
        hypothesis=raw["hypothesis"],
        hypothesis_space=[
            HypothesisSpaceEntry(**e) for e in raw.get("hypothesis_space", [])
        ],
        uncertainty_flags=raw.get("uncertainty_flags", []),
        confidence=raw.get("confidence", "Moderate"),
    )


# ─── Provider implementations ─────────────────────────────────────────────────

def _call_gemini(user_message: str) -> dict:
    import google.genai as genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[f"{_SYSTEM_PROMPT}\n\n{user_message}"],
    )
    return _extract_json(response.text)


def _call_openai(user_message: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def _call_anthropic(user_message: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return _extract_json(response.content[0].text)


# ─── Router ───────────────────────────────────────────────────────────────────

_PROVIDERS = {
    "gemini":    _call_gemini,
    "openai":    _call_openai,
    "anthropic": _call_anthropic,
}


def interpret(
    composite_index: float,
    breakdown: SignalBreakdown,
    context: SessionContext,
) -> AgentOutput:
    """
    Run the interpretation agent using the configured LLM provider.
    Returns AgentOutput with load type classification and researcher hypothesis.
    """
    user_message = _build_user_message(composite_index, breakdown, context)
    caller = _PROVIDERS[LLM_PROVIDER]
    raw = caller(user_message)
    return _parse_output(raw)