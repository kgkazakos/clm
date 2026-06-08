"""
Configuration for the Cognitive Load Monitor.

LLM Provider:
Set LLM_PROVIDER in your .env to switch interpretation layer:
  gemini    — Gemini 3.1 Pro (default)
  openai    — GPT-4o
  anthropic — Claude Sonnet

Theory-derived signal weights (v1.0 — primary published instrument):
Each weight reflects the documented effect size of that telemetry signal
as a cognitive load proxy in the source literature. Weights are normalised
effect sizes, reviewed against NASA-TLX mental demand subscale correlations.

These are the weights used in the published validation study and reported
in the whitepaper. They should not be changed without a formal validation
study (N ≥ 20) justifying the adjustment.

Hypothesised v1.1 recalibration (NOT active — pending N=20 validation):
The initial validation study (N=1) observed mouse_trajectory saturation in
both low-load and high-load sessions (scores 98.5 and 99.9), providing no
discriminant signal. A hypothesised recalibration (mouse_trajectory: 0.20→0.12,
task_switching: 0.18→0.22, hesitation: 0.16→0.20) is documented here but
NOT applied, as adjusting weights based on a single biased trial constitutes
overfitting. This recalibration will be evaluated in the N=20 study.

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
    # Guo et al. (2016): strongest single predictor (r=0.71 with NASA-TLX)
    "mouse_trajectory": 0.20,

    # Sweller (1988): direct working memory overload indicator
    "error_recovery":   0.18,

    # Sweller et al. (1998): split-attention effect
    "task_switching":   0.18,

    # Paas & van Merriënboer (1994): hesitation duration predicts effort ratings
    "hesitation":       0.16,

    # Jiang et al. (2015): dwell time and perceived task difficulty (r=0.65)
    "dwell_time":       0.14,

    # Sweller (1988): working memory strain indicator
    "input_retry":      0.08,

    # Rodrigues et al. (2020): scroll variance and spatial disorientation
    "scroll_behaviour": 0.06,
}

assert abs(sum(SIGNAL_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

# ─── Hypothesised v1.1 weights (NOT active — see docstring above) ─────────────
# HYPOTHESISED_V1_1_WEIGHTS = {
#     "task_switching":   0.22,  # +0.04 — strong discriminant in pilot
#     "hesitation":       0.20,  # +0.04 — strong discriminant in pilot
#     "error_recovery":   0.18,
#     "dwell_time":       0.14,
#     "mouse_trajectory": 0.12,  # -0.08 — saturated in pilot, context boundary
#     "input_retry":      0.08,
#     "scroll_behaviour": 0.06,
# }

# ─── Thresholds ────────────────────────────────────────────────────────────────
HESITATION_THRESHOLD_MS: int = 2_000
LOW_LOAD_THRESHOLD: int      = 40
HIGH_LOAD_THRESHOLD: int     = 70