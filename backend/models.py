"""
Pydantic data models for the Cognitive Load Monitor.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─── Input schema ─────────────────────────────────────────────────────────────

class InputFormat(str, Enum):
    CANONICAL   = "canonical"
    MAZE        = "maze"
    USERTESTING = "usertesting"


class InteractionEvent(BaseModel):
    """Single interaction event in canonical internal format."""
    timestamp_ms: float
    event_type: str               # click, scroll, input, navigation, error, hover
    element_id: Optional[str]
    x: Optional[float]            # cursor x (0–1 normalised)
    y: Optional[float]            # cursor y (0–1 normalised)
    value: Optional[str]          # scroll delta only — input text is never stored
    screen_id: Optional[str]
    duration_ms: Optional[float]  # dwell or hold duration
    is_error: bool = False
    metadata: dict = Field(default_factory=dict)


class SessionContext(BaseModel):
    task_description: str = ""
    interface_type: str = "web_app"
    participant_id: Optional[str] = None


class AnalysisRequest(BaseModel):
    format: InputFormat
    events: list[InteractionEvent]
    context: SessionContext


# ─── Signal scores ────────────────────────────────────────────────────────────

class SignalScore(BaseModel):
    signal: str
    score: float
    weight: float
    weighted_contribution: float
    interpretation: str
    literature_anchor: str


class SignalBreakdown(BaseModel):
    dwell_time: SignalScore
    error_recovery: SignalScore
    hesitation: SignalScore
    task_switching: SignalScore
    mouse_trajectory: SignalScore
    scroll_behaviour: SignalScore
    input_retry: SignalScore


# ─── Load type ────────────────────────────────────────────────────────────────

class LoadType(str, Enum):
    INTRINSIC    = "intrinsic"
    EXTRANEOUS   = "extraneous"
    GERMANE      = "germane"
    OVERLOAD     = "overload"      # high intrinsic + high extraneous (additive)
    INCONCLUSIVE = "inconclusive"  # no dominant signal pattern


# ─── Agent output ─────────────────────────────────────────────────────────────

class HypothesisSpaceEntry(BaseModel):
    intervention: str
    citation: str
    load_type_addressed: str


class AgentOutput(BaseModel):
    dominant_load_type: LoadType
    classification_reasoning: str
    hypothesis: str
    hypothesis_space: list[HypothesisSpaceEntry]
    uncertainty_flags: list[str]
    confidence: str


# ─── Full analysis result ─────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    session_id: str
    composite_index: float
    signal_breakdown: SignalBreakdown
    agent_output: AgentOutput
    event_count: int
    duration_ms: float
    format_used: InputFormat
    context: SessionContext