"""
Pydantic data models for the Cognitive Load Monitor.
These models define the canonical internal representation used
across all layers — adapters, signal calculators, agent, and report.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─── Input schema ─────────────────────────────────────────────────────────────

class InputFormat(str, Enum):
    CANONICAL    = "canonical"
    MAZE         = "maze"
    USERTESTING  = "usertesting"


class InteractionEvent(BaseModel):
    """Single interaction event in canonical internal format."""
    timestamp_ms: float           # milliseconds from session start
    event_type: str               # click, scroll, input, navigation, error, hover
    element_id: Optional[str]     # UI element identifier
    x: Optional[float]            # cursor x coordinate (0–1 normalised)
    y: Optional[float]            # cursor y coordinate (0–1 normalised)
    value: Optional[str]          # input value or scroll delta
    screen_id: Optional[str]      # current screen/page identifier
    duration_ms: Optional[float]  # dwell or hold duration where applicable
    is_error: bool = False        # true if event represents a failed action
    metadata: dict = Field(default_factory=dict)


class SessionContext(BaseModel):
    """Researcher-provided context for the AI interpretation layer."""
    task_description: str = ""
    interface_type: str = "web_app"   # web_app | mobile | desktop
    participant_id: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Full request body sent from the frontend."""
    format: InputFormat
    events: list[InteractionEvent]
    context: SessionContext


# ─── Signal scores ────────────────────────────────────────────────────────────

class SignalScore(BaseModel):
    """Score for a single telemetry signal (0–100)."""
    signal: str
    score: float
    weight: float
    weighted_contribution: float
    interpretation: str           # one-line human-readable interpretation
    literature_anchor: str        # source citation for this signal's proxy claim


class SignalBreakdown(BaseModel):
    """Full breakdown of all seven signal scores."""
    dwell_time: SignalScore
    error_recovery: SignalScore
    hesitation: SignalScore
    task_switching: SignalScore
    mouse_trajectory: SignalScore
    scroll_behaviour: SignalScore
    input_retry: SignalScore


# ─── Load type ────────────────────────────────────────────────────────────────

class LoadType(str, Enum):
    INTRINSIC  = "intrinsic"    # inherent task complexity
    EXTRANEOUS = "extraneous"   # interface design failures
    GERMANE    = "germane"      # productive schema-building
    MIXED      = "mixed"        # no single dominant type


# ─── Agent output ─────────────────────────────────────────────────────────────

class HypothesisSpaceEntry(BaseModel):
    """A single prior-work entry in the hypothesis space."""
    intervention: str
    citation: str
    load_type_addressed: str


class AgentOutput(BaseModel):
    """Output of the Gemini Layer 2 interpretation agent."""
    dominant_load_type: LoadType
    classification_reasoning: str
    hypothesis: str
    hypothesis_space: list[HypothesisSpaceEntry]
    uncertainty_flags: list[str]
    confidence: str               # High | Moderate | Low


# ─── Full analysis result ─────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    """Complete output returned to the frontend and written to reports."""
    session_id: str
    composite_index: float        # 0–100
    signal_breakdown: SignalBreakdown
    agent_output: AgentOutput
    event_count: int
    duration_ms: float
    format_used: InputFormat
    context: SessionContext
