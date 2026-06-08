"""
Configuration for the Cognitive Load Monitor.

LLM Provider:
Set LLM_PROVIDER in your .env to switch interpretation layer:
  gemini    — Gemini 3.1 Pro (default)
  openai    — GPT-4o
  anthropic — Claude Sonnet

Theory-derived signal weights (v1.1 — recalibrated after validation):
Each weight reflects the documented effect size of that telemetry signal
as a cognitive load proxy in the source literature.

v1.0 → v1.1 change:
  mouse_trajectory reduced from 0.20 → 0.12.
  Rationale: Path efficiency ratio saturated in both low-load and high-load
  sessions during initial validation (scores of 98.5 and 99.9 respectively),
  providing no discriminant signal between conditions. The 0.08 reduction was
  redistributed to task_switching (+0.04) and hesitation (+0.04), both of
  which showed strong discriminant validity in the validation study
  (task_switching: 0.0 vs 44.2; hesitation: 13.6 vs 23.6 across sessions).
  The original weight was based on Guo et al. (2016) r=0.71 with NASA-TLX,
  which remains valid as a general proxy but overstates discriminative power
  in multi-page web application contexts where non-linear cursor movement
  is structurally induced by layout rather than cognitive load alone.

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

# ─── Signal weights v1.1 ──────────────────────────────────────────────────────

SIGNAL_WEIGHTS: dict[str, float] = {
    # Sweller et al. (1998): split-attention effect — strongest discriminant
    # signal in v1.0 validation (0.0 vs 44.2 across sessions). Weight increased
    # from 0.18 to 0.22 to reflect observed discriminant validity.
    "task_switching":   0.22,

    # Paas & van Merriënboer (1994): hesitation duration predicts effort ratings.
    # Weight increased from 0.16 to 0.20 to reflect validation findings.
    "hesitation":       0.20,

    # Sweller (1988): direct working memory overload indicator.
    "error_recovery":   0.18,

    # Jiang et al. (2015): dwell time and perceived task difficulty (r=0.65).
    "dwell_time":       0.14,

    # Guo et al. (2016): mouse trajectory as cognitive load proxy (r=0.71).
    # Weight reduced from 0.20 to 0.12 — see recalibration note above.
    "mouse_trajectory": 0.12,

    # Sweller (1988): retry rate as working memory strain indicator.
    "input_retry":      0.08,

    # Rodrigues et al. (2020): scroll variance and spatial disorientation.
    "scroll_behaviour": 0.06,
}

assert abs(sum(SIGNAL_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

# ─── Thresholds ────────────────────────────────────────────────────────────────
HESITATION_THRESHOLD_MS: int = 2000
LOW_LOAD_THRESHOLD: int      = 40
HIGH_LOAD_THRESHOLD: int     = 70