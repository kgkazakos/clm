# Cognitive Load Monitor

**Computational Product Research Main — Project 3**
Personal project, not affiliated with any employer.

> "Most usability tools tell you what users did. This one tells you how hard they were working — and why."

---

## What it does

The Cognitive Load Monitor (CLM) measures cognitive load from interaction telemetry and interprets the source of that load using an AI agent grounded in Cognitive Load Theory (Sweller, 1988).

It reads a JSON interaction event log — from Maze, UserTesting, or a custom logger — and produces:

- A **composite cognitive load index** (0–100)
- A **load type classification**: Intrinsic / Extraneous / Germane / Overload / Inconclusive
- A **researcher hypothesis** about why the classified load type is present
- A **hypothesis space** of prior work addressing the identified load class

All output is framed as hypothesis for researcher evaluation, not finding. The researcher is always the analyst.

---

## Architecture

Two layers, separated by design:

```
Interaction event log (JSON)
         │
         ▼
┌─────────────────────────────────────────┐
│  LAYER 1 — Deterministic measurement    │
│                                         │
│  7 signal calculators                   │
│  ├─ dwell_time        (Jiang et al.)    │
│  ├─ error_recovery    (Sweller)         │
│  ├─ hesitation        (Paas & van M.)   │
│  ├─ task_switching    (Sweller et al.)  │
│  ├─ mouse_trajectory  (Guo et al.)      │
│  ├─ scroll_behaviour  (Rodrigues et al.)│
│  └─ input_retry       (Sweller)         │
│                                         │
│  Composite index (weighted dot product) │
│  CLT classifier (deterministic rules)   │
└────────────────────┬────────────────────┘
                     │ composite + load type
                     ▼
┌─────────────────────────────────────────┐
│  LAYER 2 — AI interpretation (Gemini)   │
│                                         │
│  Researcher hypothesis                  │
│  Hypothesis space (prior literature)    │
│  Uncertainty flags                      │
│                                         │
│  Load type is ARCHITECTURALLY ISOLATED  │
│  from LLM output — cannot be overridden │
└────────────────────┬────────────────────┘
                     │
                     ▼
         friction_report.json + .md
```

Layer 1 is fully reproducible from the published specification — any researcher implementing the same signal calculators and weights will produce identical results for the same event log. Layer 2 is generative; the LLM's response schema does not contain a classification field, making it architecturally impossible to override the Layer 1 output.

---

## Signal weights (v1.0 — literature-derived)

| Signal | Weight | Literature anchor |
|---|---|---|
| Mouse trajectory | 0.20 | Guo et al. (2016), r=0.71 with NASA-TLX |
| Error recovery | 0.18 | Sweller (1988) |
| Task switching | 0.18 | Sweller et al. (1998) |
| Hesitation | 0.16 | Paas & van Merriënboer (1994) |
| Dwell time | 0.14 | Jiang et al. (2015), r=0.65 |
| Input retry | 0.08 | Sweller (1988) |
| Scroll behaviour | 0.06 | Rodrigues et al. (2020) |

Signals with fewer than 3 qualifying events are excluded from the composite and remaining weights renormalised.

---

## Load type classification (deterministic)

| Classification | Condition |
|---|---|
| **Overload** | Hesitation ≥ 50 AND Dwell ≥ 50 AND any extraneous signal ≥ 50 |
| **Extraneous** | Any of error_recovery / task_switching / input_retry ≥ 50 |
| **Intrinsic** | Hesitation ≥ 50 AND Dwell ≥ 50, no extraneous signals ≥ 50 |
| **Germane** | Moderate hesitation (25–49), low errors, low retries |
| **Inconclusive** | No signal meets threshold |

Overload reflects CLT's additive model: Total Load = Intrinsic + Extraneous + Germane. Co-elevation of intrinsic and extraneous signals is not ambiguous — it is the highest severity state.

---

## Example output

```
Composite Cognitive Load Index: 46.8 / 100 — Moderate

Signal Breakdown:
  Mouse Trajectory     99.9   weight 0.20
  Error Recovery        0.0   weight 0.18
  Task Switching       44.2   weight 0.18
  Hesitation           23.6   weight 0.16
  Dwell Time           46.2   weight 0.14
  Input Retry          70.0   weight 0.08
  Scroll Behaviour     50.0   weight 0.06

Load Type: EXTRANEOUS — Interface design load
Confidence: Moderate

Researcher Hypothesis:
The physical separation of laptop component options and their
configuration details creates a split-attention effect, driving
erratic cursor trajectories and repeated input adjustments.

Hypothesis Space:
— Chandler & Sweller (1991): integrating mutually referring elements
  reduces split-attention effect and extraneous load
— Bargas-Avila et al. (2010): exposed radio buttons reduce working
  memory strain vs multi-step dropdowns
```

---

## Supported input formats

| Format | Source |
|---|---|
| Canonical | Custom browser extension (included) or any JSON logging |
| Maze | Maze session export JSON |
| UserTesting | UserTesting session export JSON |

---

## Privacy

- Input field values are **never logged** — only element identifier and dwell duration
- Element identifiers are sanitised: email-pattern IDs replaced, all IDs truncated to 40 chars
- The LLM receives only seven numerical scores and the task description — no event-level data

---

## LLM providers

Supports Gemini, OpenAI, and Anthropic via a single environment variable:

```
LLM_PROVIDER=gemini     # default
LLM_PROVIDER=openai
LLM_PROVIDER=anthropic
```

---

## Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env    # add your API key + LLM_PROVIDER
uvicorn main:app --reload

# Frontend
cd frontend
python3 -m http.server 3000
# Open http://localhost:3000
```

---

## Chrome extension (CLM Logger)

The `extension/` folder contains a Chrome Manifest V3 extension for capturing canonical-format interaction logs with integrated NASA-TLX rating.

To install: `chrome://extensions` → Enable Developer Mode → Load unpacked → select `extension/`

Features:
- Records across full multi-page sessions (global session clock)
- SPA navigation detection via `chrome.webNavigation`
- NASA-TLX rating embedded in exported JSON
- PII-safe: no input values logged, element IDs sanitised

---

## Validation

Initial technical integration study (N=1) across two sessions of different cognitive demand:

| | Session 1 (Low) | Session 2 (High) |
|---|---|---|
| CLM composite | 37.4 | 46.8 |
| NASA-TLX | 18 | 64 |
| Load type | Inconclusive | Extraneous |

Correctly ordered by both instruments. Full methodology and limitations in [whitepaper](docs/whitepaper.md).

---

## Whitepaper

[Cognitive Load Monitor: From Interaction Telemetry to Researcher Hypothesis](docs/whitepaper.md)

---

## CPR Portfolio

This is Project 3 of a 7-project Computational Product Research portfolio.

- **P1 — CausalTrack**: Audio-based Say-Do gap detection
- **P2 — Synthetic User Council**: Multi-agent synthetic persona generation
- **P3 — Cognitive Load Monitor**: Telemetry-based cognitive load measurement ← you are here

---

*Personal project. All work is the author's own.*
