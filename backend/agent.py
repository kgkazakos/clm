"""
Layer 2: AI interpretation agent — hypothesis generation only.

The CLT load type classification has been moved to Layer 1 (classifier.py)
as a deterministic algorithmic heuristic. This is correct separation of
concerns: deterministic signal-pattern classification does not benefit from
generative AI, and using an LLM for it introduced unnecessary latency, cost,
and hallucination risk.

This agent's role is strictly generative:
1. Receive the pre-classified load type from Layer 1
2. Analyse task context to generate a researcher-facing hypothesis
   about WHY the classified load type is present
3. Surface prior work from the HCI/CLT literature addressing
   the identified load class — framed as hypothesis space, not prescription
4. Flag measurement uncertainty where telemetry may be unreliable

The LLM's generative strengths — contextual reasoning, literature synthesis,
natural language hypothesis generation — are applied here. The classification
itself is deterministic and reproducible.
"""

import json
import re

import google.genai as genai

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

# ─── System prompt ─────────────────────────────────────────────────────────────
# Note: load type classification is NOT requested here.
# It has been determined algorithmically in Layer 1 (classifier.py).
# The agent's task is to reason about WHY the classified load type is present,
# generate a researcher hypothesis, and surface prior work.

_SYSTEM_PROMPT = """You are a cognitive load theorist assisting a UX researcher.

You have received:
1. A composite cognitive load index (0-100)
2. A breakdown of seven telemetry signals with scores and interpretations
3. The dominant load type, already classified algorithmically:
   - INTRINSIC: load from inherent task complexity
   - EXTRANEOUS: load from interface design failures
   - GERMANE: productive schema-building load
   - OVERLOAD: high intrinsic + high extraneous load simultaneously (cognitive overload state)
   - INCONCLUSIVE: no dominant signal pattern detected
4. The algorithmic reasoning behind that classification
5. Session context: task description and interface type

Your task is to:
1. Generate a researcher-facing hypothesis about WHY the classified load type
   is present — what specifically about the task or interface is causing it
2. Surface 2-4 prior work entries from HCI/CLT literature that have addressed
   this load type in comparable contexts
3. Identify specific uncertainty flags where the telemetry measurement may be
   unreliable or ambiguous

You are NOT asked to classify the load type — that has already been done.
Your value is in contextual interpretation and literature synthesis.

Frame all output as hypothesis for researcher evaluation, not as findings.
Interventions should be framed as prior work findings, not prescriptions.

Output ONLY a valid JSON object with this exact structure:
{
  "hypothesis": "One precise sentence stating the researcher hypothesis about WHY this load type is present, given the task context and signal pattern.",
  "hypothesis_space": [
    {
      "intervention": "Description of intervention from prior work",
      "citation": "Author (Year) — brief title or finding",
      "load_type_addressed": "intrinsic" | "extraneous" | "germane"
    }
  ],
  "uncertainty_flags": ["List of specific, actionable uncertainty flags"],
  "confidence": "High" | "Moderate" | "Low"
}

Rules:
- hypothesis must reference the task context if provided — generic hypotheses are not useful
- hypothesis_space entries must be real HCI/CLT literature, not fabricated
- uncertainty_flags must be specific to the observed signal pattern, not generic caveats
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
    load_type: LoadType,
    classification_reasoning: str,
    context: SessionContext,
) -> str:
    return (
        f"Composite cognitive load index: {composite_index}/100\n\n"
        f"Signal breakdown:\n{_format_breakdown(breakdown)}\n\n"
        f"Algorithmically classified load type: {load_type.value.upper()}\n"
        f"Classification reasoning: {classification_reasoning}\n\n"
        f"Session context:\n"
        f"  Task: {context.task_description or 'Not provided'}\n"
        f"  Interface type: {context.interface_type}\n"
        f"  Participant: {context.participant_id or 'Anonymous'}\n\n"
        f"Generate the researcher hypothesis and hypothesis space for this load type."
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _parse_output(
    raw: dict,
    load_type: LoadType,
    classification_reasoning: str,
) -> AgentOutput:
    return AgentOutput(
        dominant_load_type=load_type,
        classification_reasoning=classification_reasoning,
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


_PROVIDERS = {
    "gemini":    _call_gemini,
    "openai":    _call_openai,
    "anthropic": _call_anthropic,
}


def interpret(
    composite_index: float,
    breakdown: SignalBreakdown,
    load_type: LoadType,
    classification_reasoning: str,
    context: SessionContext,
) -> AgentOutput:
    """
    Generate researcher hypothesis and hypothesis space for the
    pre-classified load type. Classification is NOT performed here.
    """
    user_message = _build_user_message(
        composite_index, breakdown, load_type, classification_reasoning, context
    )
    caller = _PROVIDERS[LLM_PROVIDER]
    raw = caller(user_message)
    return _parse_output(raw, load_type, classification_reasoning)