"""
Configuration for the Cognitive Load Monitor.

LLM Provider:
Set LLM_PROVIDER in your .env to switch interpretation layer:
  gemini    — Gemini 3.1 Pro (default)
  openai    — GPT-4o
  anthropic — Claude Sonnet

Theory-derived signal weights (v1.0 — primary published instrument):
Each weight reflects the documented effect size of that telemetry signal
as a cognitive load proxy in the source literature.

Minimum event density:
Each signal calculator requires a minimum number of qualifying events
(MIN_SIGNAL_EVENTS) before returning a score. If a signal does not meet
this threshold, it returns 0.0 and is excluded from the composite index
calculation. The remaining signal weights are renormalised to sum to 1.0.

Rationale: A signal derived from n=2 events carries the same mathematical
weight as one derived from n=50 events under a fixed-weight composite.
This creates instability — two unusually long dwell events can produce a
score of 100.0 that dominates the composite. The minimum threshold prevents
low-density signals from skewing the aggregate without representing a
reliable behavioral pattern.

The threshold of 3 qualifying events is a conservative lower bound.
Empirical calibration against the N=20 validation study is planned.

Hypothesised v1.1 recalibration (NOT active — pending N=20 validation):
See commented-out block below for details.

Literature anchors:
- Sweller (1988): Cognitive load during problem solving
- Paas & van Merriënboer (1994): Instructional control of cognitive load
- Hart & Staveland (1988): NASA-TLX development
- Guo et al. (2016): Mouse movement as cognitive load proxy (r=0.71)
- Jiang et al. (2015): Dwell time and perceived task difficulty (r=0.65)
- Sweller et al. (1998): Split-attention effect and task-switching
- Rodrigues et al. (2020): Scroll behaviour and information architecture load
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM Provider ─────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()

GEMINI_API_KEY: str     = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str       = "gemini-3.1-pro-preview"

OPENAI_API_KEY: str     = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str       = "gpt-4o"

ANTHROPIC_API_KEY: str  = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str    = "claude-sonnet-4-5"

_REQUIRED_KEYS = {
    "gemini":    ("GEMINI_API_KEY",    GEMINI_API_KEY),
    "openai":    ("OPENAI_API_KEY",    OPENAI_API_KEY),
    "anthropic": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
}

if LLM_PROVIDER not in _REQUIRED_KEYS:
    raise ValueError(
        f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. "
        f"Must be one of: {', '.join(_REQUIRED_KEYS)}"
    )

_key_name, _key_value = _REQUIRED_KEYS[LLM_PROVIDER]
if not _key_value:
    raise ValueError(
        f"LLM_PROVIDER is set to '{LLM_PROVIDER}' but {_key_name} is missing from .env"
    )

# ─── Signal weights v1.0 (primary — literature-derived) ──────────────────────

SIGNAL_WEIGHTS: dict[str, float] = {
    "mouse_trajectory": 0.20,
    "error_recovery":   0.18,
    "task_switching":   0.18,
    "hesitation":       0.16,
    "dwell_time":       0.14,
    "input_retry":      0.08,
    "scroll_behaviour": 0.06,
}

assert abs(sum(SIGNAL_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

# ─── Minimum qualifying events per signal ────────────────────────────────────
# Signals with fewer than this many qualifying events return 0.0 and are
# excluded from the composite calculation. Prevents n=2 events from
# dominating the composite through the fixed-weight dot product.
MIN_SIGNAL_EVENTS: int = 3

# ─── Hypothesised v1.1 weights (NOT active — see docstring) ──────────────────
# HYPOTHESISED_V1_1_WEIGHTS = {
#     "task_switching":   0.22,
#     "hesitation":       0.20,
#     "error_recovery":   0.18,
#     "dwell_time":       0.14,
#     "mouse_trajectory": 0.12,
#     "input_retry":      0.08,
#     "scroll_behaviour": 0.06,
# }

# ─── Thresholds ────────────────────────────────────────────────────────────────
HESITATION_THRESHOLD_MS: int = 2_000
LOW_LOAD_THRESHOLD: int      = 40
HIGH_LOAD_THRESHOLD: int     = 70