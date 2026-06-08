# Cognitive Load Monitor: From Interaction Telemetry to Researcher Hypothesis

**Kostas Kazakos, PhD**
Computational Product Research — Project 3 CPR Main
Personal project, not affiliated with any employer.

---

## Abstract

Understanding when and why users struggle during task completion is a central challenge in usability research. Traditional approaches rely on post-hoc self-report instruments — primarily the NASA Task Load Index (NASA-TLX) and the Single Ease Question (SEQ) — which are subject to recall bias and cannot resolve the moment or mechanism of cognitive strain. Video-based methods offer temporal granularity but require labour-intensive manual coding. This paper presents the **Cognitive Load Monitor (CLM)**, a two-layer system that measures cognitive load from interaction telemetry and interprets the source of that load using an AI agent grounded in Cognitive Load Theory (CLT). The CLM does not replace user interviews or self-report instruments; it targets the specific blindspot of retrospective workload measurement by operating on behavioral data that is a natural byproduct of any recorded session.

The measurement layer computes a composite cognitive load index (0–100) from seven telemetry signals — dwell time, error recovery, hesitation, task switching, mouse trajectory, scroll behaviour, and input retry — each weighted according to documented effect sizes in the CLT and HCI workload measurement literature. A minimum event density threshold ensures that signals derived from insufficient data are excluded from the composite and their weights renormalised, preventing low-density signals from skewing the aggregate. CLT load type classification is performed deterministically in Layer 1 using signal pattern heuristics with explicit numeric thresholds, producing one of five classifications: Intrinsic, Extraneous, Germane, Overload, or Inconclusive. The Overload classification — triggered when both intrinsic and extraneous signals are simultaneously elevated — reflects CLT's additive model of working memory demand. The interpretation layer employs a large language model exclusively for generative tasks: producing a researcher-facing hypothesis, surfacing prior work, and flagging measurement uncertainty. The load type classification is set directly from Layer 1 output and is architecturally isolated from the LLM's response — it is not a field the LLM can populate or override.

An initial technical integration study across two sessions of deliberately different cognitive demand found that the CLM correctly ordered sessions by composite index (37.4 vs. 46.8) and by dominant load type, consistent with NASA-TLX ratings of 18 and 64 respectively.

---

## 1. Introduction: The Problem With Self-Report

Usability research relies heavily on self-report to understand cognitive experience. The NASA-TLX (Hart & Staveland, 1988) and SEQ (Sauro & Dumas, 2009) are the dominant instruments for measuring workload and ease — both widely validated, both requiring participants to retrospectively assess their own experience after task completion.

This retrospective framing introduces two structural limitations. First, **recall bias**: participants may not accurately remember the moment of peak difficulty, particularly in multi-step tasks where early confusion resolves through persistence. The summary rating reflects an average or endpoint impression rather than the trajectory of load through the task. Second, **construct conflation**: post-hoc ratings cannot distinguish between difficulty that arose from inherent task complexity (Sweller's intrinsic load), difficulty introduced by interface design failures (extraneous load), and productive cognitive engagement in building understanding (germane load). These three types have fundamentally different design implications — reducing intrinsic load requires simplifying the task itself, while reducing extraneous load requires improving the interface — yet self-report instruments treat them as a single construct.

Think-aloud protocol offers partial mitigation but introduces reactivity, requires a skilled moderator, and produces data that is expensive to code at scale. Screen recording analysis addresses retrospection but reintroduces the manual coding burden.

Interaction telemetry offers a third path: every recorded session generates a timestamped log of user actions that can be analysed computationally without additional participant effort. The CLM is an attempt to determine whether patterns in that log can reliably index cognitive load and distinguish its type. It does not replace self-report: NASA-TLX and SEQ remain the primary validation criteria and the researcher's interpretive authority remains intact.

---

## 2. Theoretical Foundation

### 2.1 Cognitive Load Theory

Cognitive Load Theory (Sweller, 1988; Sweller, van Merriënboer & Paas, 1998) proposes that working memory has finite capacity and that task performance degrades when cognitive demands exceed that capacity. CLT distinguishes three load types that contribute **additively** to total working memory utilisation:

$$\text{Total Load} = \text{Intrinsic} + \text{Extraneous} + \text{Germane}$$

**Intrinsic load** arises from task complexity — the number of interacting elements that must be held in working memory simultaneously. It cannot be designed away, only scaffolded. **Extraneous load** arises from how information is presented — design decisions that impose unnecessary cognitive work. The split-attention effect (Chandler & Sweller, 1992) is a canonical source: spatially separating mutually dependent information forces users to mentally integrate it at cognitive cost. Extraneous load is design-reducible. **Germane load** represents productive investment in schema formation. It is desirable load, associated with learning. Germane load was later reconceptualised by Sweller (2010) as a component of intrinsic load, though the tripartite distinction remains common in HCI research for its practical utility.

The additive nature of these types is critical for the CLM's classification design. When a user performs a highly complex task on a poorly designed interface, the result is not an ambiguous "mixed" state — it is the highest severity failure condition, where total working memory demand approaches or exceeds capacity. The CLM captures this as the **Overload** classification, distinct from a state where signals are genuinely ambiguous (**Inconclusive**).

### 2.2 Telemetry as Cognitive Load Proxy

Guo et al. (2016) demonstrated that mouse path efficiency ratio correlates with NASA-TLX mental demand (r = 0.71). Jiang et al. (2015) showed that extended dwell times correlate with perceived task difficulty (r = 0.65). Paas and van Merriënboer (1994) documented that pause duration before acting predicts subjective effort ratings. Sweller et al.'s (1998) split-attention research established task-switching frequency as an indicator of demand from non-integrated layouts. Rodrigues et al. (2020) linked erratic scroll patterns to spatial disorientation. Input retry rate has been linked to schema incompleteness and working memory strain (Sweller, 1988).

These relationships were validated in controlled experimental contexts. Their generalisation to unmoderated real-world sessions involves boundary conditions discussed throughout this paper.

### 2.3 Validation Instruments

The CLM uses NASA-TLX (Hart & Staveland, 1988) as its primary external validation criterion. The Raw TLX variant — an unweighted mean of the six subscales — was used in the integration study, consistent with Bustamante and Spain's (2008) finding that it is as sensitive as the weighted version with less participant burden. The SEQ (Sauro & Dumas, 2009) is planned as a secondary instrument.

---

## 3. System Architecture

The CLM is organised as a two-layer system with a strict separation of concerns. Layer 1 is entirely deterministic: given the same event log, it will always produce the same composite index and load type classification. Layer 2 is generative: it applies LLM reasoning to produce contextual hypothesis and literature synthesis.

Deterministic Layer 1 output is fully reproducible — any researcher implementing the same signal calculators with the same weights will produce identical results for the same event log. The LLM in Layer 2 is reserved for tasks where generative capability adds genuine value. Classification does not benefit from generative AI — a signal pattern heuristic performs the same function with less latency, lower cost, and no hallucination risk.

The system exposes a FastAPI REST backend and a browser-based frontend. The interpretation layer supports Gemini, OpenAI, and Anthropic models through a unified routing interface controlled by a single environment variable.

---

## 4. Layer 1 — The Measurement Pipeline

### 4.1 Input and Adapter Architecture

The pipeline accepts JSON interaction event logs in three formats: a **canonical schema** for custom instrumentation, **Maze exports** from the `recordings` array, and **UserTesting exports** from the `clips` array. UserTesting's explicit `is_rage_click` flag provides richer error signal than can be inferred from Maze's event stream alone. All formats produce the same internal `InteractionEvent` model.

### 4.2 The Seven Telemetry Signals

Each calculator returns a normalised score (0–100) and an interpretation string. **Each signal requires a minimum of three qualifying events** (MIN_SIGNAL_EVENTS = 3). If a signal does not meet this threshold, it returns 0.0 and is excluded from the composite — its weight is redistributed across the remaining active signals via renormalisation. This prevents low-density signals from skewing the aggregate. The minimum threshold of three is conservative and pending empirical calibration against the N=20 validation study.

**Dwell time** measures mean duration on form elements. Following Jiang et al. (2015), events exceeding 1,000ms are classified as high-dwell. Score = weighted combination of mean dwell and high-dwell proportion. *Anchor: Jiang et al. (2015).*

**Error recovery** measures error rate and recovery speed. For each error, the calculator checks whether corrective action follows within 5,000ms. *Anchor: Sweller (1988).*

**Hesitation** measures inter-event pause duration within a dual bound: [2,000ms, 15,000ms]. Pauses below 2,000ms are normal processing time; pauses above 15,000ms are excluded as likely external distraction. This dual-bound design is what enables the CLM to be deployed in **unmoderated research environments**. Traditional telemetry metrics fail in unmoderated settings because long idle periods — caused by the participant checking a phone, speaking to someone nearby, or switching applications — are indistinguishable from genuine cognitive hesitation without a moderator present. By capping hesitation at 15,000ms, the CLM filters out the majority of environmental interruptions without requiring human supervision, making it viable for the remote and unmoderated study designs where most existing workload measurement approaches break down. *Anchor: Paas & van Merriënboer (1994).*

**Task switching** measures screen change frequency and rapid switch rate (switches within 3,000ms). *Note on fragmented clock (v1.0 data):* In the integration study, the session clock reset on each page load, making the rapid switch rate component unreliable for cross-page navigations. Only the frequency component is reliable from v1.0 data. Resolved in v1.1 via a global session clock. *Anchor: Sweller et al. (1998).*

**Mouse trajectory** measures path efficiency: straight-line to actual cursor path length ratio. **Context boundary**: validated by Guo et al. (2016) in controlled pointing tasks. Multi-page web navigation structurally induces non-linear cursor paths through vertical rhythm, whitespace, and wide navigation elements — independent of cognitive load. Both integration study sessions scored near the theoretical maximum (98.5 and 99.9). This structural saturation also suppresses the Germane classification in web contexts — see Section 8. *Anchor: Guo et al. (2016).*

**Scroll behaviour** measures velocity variance and direction reversals. Erratic patterns indicate spatial disorientation under poor information architecture (Rodrigues et al., 2020). *Anchor: Rodrigues et al. (2020).*

**Input retry** measures repeated input sequences on the same element within 8,000ms, interpreted as working memory strain from interface element ambiguity. *Anchor: Sweller (1988).*

### 4.3 Signal Weights and Composite Index

Weights are literature-derived effect sizes, normalised to sum to 1.0. When signals are excluded due to insufficient event density, remaining weights are renormalised before computing the dot product.

| Signal | Weight | Literature basis |
|---|---|---|
| Mouse trajectory | 0.20 | Guo et al. (2016), r = 0.71 |
| Error recovery | 0.18 | Sweller (1988) |
| Task switching | 0.18 | Sweller et al. (1998) |
| Hesitation | 0.16 | Paas & van Merriënboer (1994) |
| Dwell time | 0.14 | Jiang et al. (2015), r = 0.65 |
| Input retry | 0.08 | Sweller (1988) |
| Scroll behaviour | 0.06 | Rodrigues et al. (2020) |

**Hypothesised v1.1 recalibration (not implemented — pending N=20 validation):** Mouse trajectory saturation motivates a hypothesised redistribution (0.20 → 0.12; task switching: 0.18 → 0.22; hesitation: 0.16 → 0.20). Implementing this on the basis of a single biased trial would constitute overfitting. The recalibration is documented in the codebase as a commented-out alternative.

### 4.4 Deterministic CLT Classification

Load type classification uses explicit numeric thresholds applied to signal scores.

**Score bands:**
- High: score ≥ 50
- Medium: 25 ≤ score < 50
- Low: score < 25

**Overload** condition expressed formally:

$$\text{Overload} = (\text{hesitation} \geq 50 \land \text{dwell} \geq 50) \land (\text{error\_recovery} \geq 50 \lor \text{task\_switching} \geq 50 \lor \text{input\_retry} \geq 50)$$

Per CLT's additive model, simultaneous elevation of both intrinsic and extraneous signals indicates total load approaching or exceeding working memory capacity. This is the highest severity classification.

**Extraneous:** At least one extraneous signal ≥ 50, with deliberation signals below High threshold.

**Intrinsic:** Both deliberation signals ≥ 50 (hesitation AND dwell), with all extraneous signals < 50.

**Germane:** Moderate hesitation (25–49), low error recovery (< 25), low input retry (< 25), moderate mouse trajectory (< 50).

**Inconclusive:** No signal pattern meets the above thresholds.

The Overload/Inconclusive distinction is architecturally significant. High intrinsic and high extraneous loads are additive — treating their co-elevation as uncertain undersells the severity of the most critical detectable failure state.

These thresholds are heuristic and provisional. Sensitivity analysis is planned for the N=20 study.

---

## 5. Layer 2 — The AI Interpretation Agent

### 5.1 Scope: Hypothesis Generation Only, Classification Architecturally Isolated

The LLM receives the pre-classified load type, its algorithmic reasoning, the composite index, the signal breakdown, and the session context. Its task is strictly generative: produce a researcher hypothesis about why the classified load type is present, surface 2–4 prior work entries, and flag measurement uncertainty.

**The load type classification is architecturally isolated from the LLM's output.** The LLM's JSON response schema contains four fields: `hypothesis`, `hypothesis_space`, `uncertainty_flags`, and `confidence`. There is no `dominant_load_type` field in the schema — the model cannot populate or override it. The `dominant_load_type` in the API response is set directly from the Layer 1 classifier output before the LLM call and is passed through independently.

This is a stronger guarantee than prompt-level instruction. Prompt instructions are soft constraints — LLMs are non-deterministic and can subtly reframe output. Architectural constraints are hard: if a field does not exist in the output schema, the LLM cannot alter it regardless of what it generates. This design principle — enforce deterministic requirements architecturally, not through prompts — generalises beyond this system.

### 5.2 Output as Hypothesis, Not Finding

All agent output is framed as hypothesis for researcher evaluation. Telemetry alone — without eye-tracking, audio, or the researcher's contextual knowledge — cannot support the evidentiary standard of a finding. Uncertainty flags are surfaced explicitly for every session.

### 5.3 Hypothesis Space

The agent surfaces a hypothesis space: prior work entries framed as "interventions that have addressed this load type in comparable contexts." This is more academically honest and more useful to a researcher evaluating the design space than prescriptive AI-generated recommendations.

### 5.4 Multi-Provider Abstraction

The interpretation layer supports Gemini, OpenAI, and Anthropic models through a unified routing interface with an identical system prompt across providers, enabling empirical comparison of hypothesis quality.

---

## 6. Data Collection Infrastructure

### 6.1 CLM Logger Chrome Extension

Interaction telemetry is captured using the CLM Logger, a Chrome Manifest V3 extension.

**Global session clock.** In v1.1, the background service worker stores the session start epoch in `chrome.storage.session` and passes it to every content script. All events share a single absolute time reference, enabling correct inter-page hesitation computation.

**SPA navigation detection.** `chrome.webNavigation.onCompleted` covers traditional multi-page navigations; `chrome.webNavigation.onHistoryStateUpdated` covers SPA route changes. Navigation events are recorded in the background service worker regardless of content script initialisation state.

**State persistence.** `chrome.storage.session` ensures data survives Chrome's service worker termination cycles.

### 6.2 Privacy and Data Handling

The CLM Logger applies two layers of PII protection at the point of capture.

**Input values are never logged.** The content script captures only the element identifier and dwell duration for input events; the value field is set to null and discarded. This covers the obvious PII vector: typed text including email addresses, passwords, and names.

**Element identifiers are sanitised.** Modern web applications frequently inject user data directly into DOM attributes — `id`, `class`, `data-*` attributes — creating a less obvious PII vector even when input values are stripped. Examples: `<div id="account-user@example.com">` or `<button data-username="kkazakos">`. The content script applies two safeguards to element identifiers before logging: it strips any identifier containing an email-like pattern (contains both `@` and `.`), replacing it with `[redacted-email-id]`; and it truncates all identifiers to a maximum of 40 characters, preventing long dynamic identifiers that may contain tokens or usernames from being stored in full.

**What reaches the LLM.** The interpretation layer receives only seven numerical signal scores, the composite index, and the researcher-provided task description. No event-level data — including sanitised element identifiers, coordinates, or timestamps — is transmitted to any LLM provider.

Researchers deploying the CLM in participant studies should obtain informed consent for interaction telemetry collection, confirm ethics board approval covers automated behavioral logging, and not deploy the extension on sessions involving access to participant accounts or sensitive systems.

### 6.3 NASA-TLX Integration

After stopping a recording, the popup transitions to a NASA-TLX rating screen. Ratings are embedded directly in the exported JSON alongside the event log, producing a single file with both behavioral telemetry and subjective workload rating per session.

---

## 7. Technical Integration Study

### 7.1 Study Design and Scope

This is a **technical integration test** — its purpose is to verify end-to-end pipeline operation and identify instrumentation issues. It is not a validation study. N=1, self-conducted; no psychometric claims are made.

**Session 1 — Low Load:** Signup flow on a marketing email platform. 81 events across 5 screens. Effective interaction time: ~12 seconds (developer familiarity, not representative of typical users).

**Session 2 — High Load:** Laptop configuration on a retail website. 285 events across 10+ screens.

Raw NASA-TLX was completed immediately after each session.

### 7.2 Results

All scores in Tables 1 and 2 are normalised values on a 0–100 scale.

**Table 1: Session-level comparison**

| Measure | Session 1 (Low) | Session 2 (High) | Direction |
|---|---|---|---|
| CLM composite index (0–100) | 37.4 | 46.8 | ✓ Correct |
| CLM band | Low | Moderate | ✓ Correct |
| NASA-TLX weighted score (0–100) | 18 | 64 | ✓ Correct |
| CLM dominant load type | Inconclusive | Extraneous | ✓ Coherent |
| Event count | 81 | 285 | — |

**Table 2: Signal-level comparison (Normalised Score: 0–100)**

| Signal | Session 1 | Session 2 | Discriminant? |
|---|---|---|---|
| Dwell time | 100.0 | 46.2 | ✗ Reversed (n=2, see §7.3) |
| Error recovery | 0.0 | 0.0 | — Tied |
| Hesitation | 13.6 | 23.6 | ✓ Correct |
| Task switching | 0.0 | 44.2 | ✓ Correct (frequency only — see §7.3) |
| Mouse trajectory | 98.5 | 99.9 | ✗ Saturated |
| Scroll behaviour | 25.4 | 50.0 | ✓ Correct |
| Input retry | 0.0 | 70.0 | ✓ Correct |

### 7.3 Discussion

**Ordinal validity.** The CLM correctly ordered both sessions by composite index and load type direction, consistent with NASA-TLX. Task switching (0.0 vs. 44.2), input retry (0.0 vs. 70.0), and scroll behaviour (25.4 vs. 50.0) discriminated cleanly in the expected direction.

**Load type classifications.** Session 1 is Inconclusive — no signal reaches the High band (≥ 50). Dwell time scores 100.0 but is a deliberation signal; Intrinsic requires hesitation also ≥ 50, and hesitation scored only 13.6. Session 2's Extraneous classification is coherent: input retry at 70.0 indicates interface-driven working memory strain.

**Dwell time score instability — minimum event density.** Session 1's dwell time score of 100.0 was derived from n=2 qualifying events, both with unusually long durations (mean 5,481ms). Under the previous fixed-weight composite, this n=2 signal carried the same mathematical leverage as a signal derived from 80 events. The minimum event density threshold (MIN_SIGNAL_EVENTS = 3) introduced in v1.2 addresses this directly: had it been applied to Session 1, dwell time would have been excluded and its 0.14 weight redistributed across remaining signals, reducing the composite and preventing a 100.0 dwell score from masking the low-activity nature of the session.

**Task switching and fragmented clock.** Session 2's task switching score of 44.2 comprises switch frequency (6 changes / 285 events = 2.1%) and rapid switch rate (4 flagged within 3,000ms). The rapid switch rate is unreliable under the pre-v1.1 fragmented session clock — a switch logged at 200ms on a new page does not mean it occurred 200ms after the previous one. Only the frequency component is reliable from v1.0 data.

**Magnitude gap.** The CLM composite difference (9.4 points) is substantially smaller than the NASA-TLX difference (46 points). Mouse trajectory saturation contributes nearly identical weighted scores across sessions. Dwell time instability (n=2 in Session 1) further inflated the Session 1 composite.

**Mouse trajectory saturation.** Path efficiency structurally saturates in web navigation contexts — see Section 4.2.

**NASA-TLX performance subscale note.** The performance subscale was rated at 100 in Session 1 (0 = perfect, 100 = failure), inconsistent with near-zero ratings elsewhere. This was a UI labelling error and does not affect the CLM analysis. The extension now includes explicit endpoint labels.

---

## 8. Limitations

**Sample size and self-conduct.** N=1, two sessions, no counterbalancing. Reported as a technical integration test only.

**Germane classification structurally suppressed in web contexts.** The Germane classification requires moderate mouse trajectory (< 50). In multi-page web navigation, mouse trajectory structurally saturates above 90 — meaning Germane cannot be triggered in a web navigation context under v1.0 weights, regardless of user behaviour. Sessions that would otherwise qualify will be classified as Inconclusive. Until the v1.1 weight recalibration is validated, researchers should treat Germane as non-detectable in web sessions and interpret Inconclusive outputs with this context in mind.

**Hesitation upper bound — provisional.** The 15,000ms exclusion threshold is theoretically motivated but not empirically calibrated. It is a configurable parameter.

**Classifier threshold sensitivity.** The High (≥ 50) and Medium (≥ 25) thresholds are heuristic. Sensitivity analysis across High band values of 40, 50, and 60 is planned for the N=20 study.

**Minimum event density threshold — provisional.** MIN_SIGNAL_EVENTS = 3 is a conservative lower bound. Sessions with unusually sparse event logs may have multiple signals excluded, producing a composite derived from a subset of signals. The threshold and the excluded-signal renormalisation approach should be validated empirically.

**Task switching rapid-switch component (v1.0 data).** As described in Section 7.3, only the frequency component is reliable from integration study data. V1.1 global session clock resolves this for future sessions.

**Mouse trajectory in web contexts.** Path efficiency faces structural validity challenges in multi-page web navigation. The signal remains in the composite but its discriminant validity is lower than the Guo et al. (2016) effect size suggests in this context.

**No ground truth beyond NASA-TLX.** Without physiological ground truth — pupil dilation, EEG, galvanic skin response — the validation establishes concordance between two subjective measures.

**No real-time mode.** Post-hoc only. Real-time detection requires streaming analysis with distinct challenges around minimum event counts for stable computation.

---

## 9. Future Work

**N=20 formal validation study.** Success criterion: Pearson r ≥ 0.50 between CLM composite and NASA-TLX weighted score. The hypothesised v1.1 weight recalibration and classifier threshold sensitivity analysis (High = 40, 50, 60) will be evaluated on the same dataset.

**Germane classification recovery.** Assessed empirically in the N=20 study under hypothesised v1.1 weights before any recalibration is published.

**Minimum event density calibration.** Empirical analysis of how often signals are excluded under MIN_SIGNAL_EVENTS = 3 across a larger session corpus, and whether higher thresholds (5 or 10) improve composite stability.

**Multi-provider hypothesis comparison.** Systematic comparison of hypothesis quality across Gemini, GPT-4o, and Claude, rated by UX researchers blind to provider.

**Mouse trajectory recalibration.** Context-specific normalisation against a baseline of typical cursor movement for each interface type.

**SEQ integration.** Single Ease Question as a secondary validation instrument.

**Overload prevalence study.** Neither integration study session triggered Overload. A deliberate study combining high intrinsic complexity with poor interface design will establish whether the classification fires as expected.

**Real-time mode.** Streaming signal computation on rolling event windows with adaptive window sizing.

---

## 10. Conclusion

The Cognitive Load Monitor addresses a specific gap in the usability research instrumentation stack: the absence of a computationally accessible, theoretically grounded tool for translating interaction telemetry into cognitive load measurement without physiological sensors or manual video coding.

Its core architectural contribution is the separation of deterministic measurement from generative interpretation, with an explicit architectural guarantee that the LLM cannot alter the Layer 1 classification. Layer 1 — signal calculation, composite indexing with minimum event density enforcement, and CLT classification with explicit numeric thresholds — is fully reproducible from the published specification. Layer 2 applies LLM capabilities where they add genuine value. The boundary between these layers is enforced not just by prompt design but by the system's response schema.

The Overload/Inconclusive distinction reflects CLT's additive model directly. The minimum event density threshold addresses a structural vulnerability in fixed-weight composites exposed by the integration study. The initial study establishes ordinal validity while surfacing instrumentation limitations documented as a concrete validation agenda. The v1.0 system is a research prototype. The paper reports it as such.

---

## References

Bargas-Avila, J. A., Brenzikofer, O., Roth, S. P., Tuch, A. N., Orsini, S., & Opwis, K. (2010). Online form design: web pages or drop-down menus? In *Proceedings of the SIGCHI Conference on Human Factors in Computing Systems* (pp. 2241–2250).

Bustamante, E. A., & Spain, R. D. (2008). Measurement invariance of the NASA TLX. In *Proceedings of the Human Factors and Ergonomics Society Annual Meeting* (Vol. 52, No. 19, pp. 1522–1526).

Chandler, P., & Sweller, J. (1992). The split-attention effect as a factor in the design of instruction. *British Journal of Educational Psychology*, 62(2), 233–246.

Guo, Q., Jin, H., Lagun, D., Yuan, S., & Agichtein, E. (2016). Mining touch interaction data on mobile devices to predict web search result relevance. In *Proceedings of the 39th International ACM SIGIR Conference on Research and Development in Information Retrieval* (pp. 153–162).

Hart, S. G., & Staveland, L. E. (1988). Development of NASA-TLX (Task Load Index): Results of empirical and theoretical research. In P. A. Hancock & N. Meshkati (Eds.), *Human Mental Workload* (pp. 139–183). North-Holland.

Jeung, H. J., Chandler, P., & Sweller, J. (1997). The role of visual indicators in dual sensory mode instruction. *Educational Psychology*, 17(3), 329–343.

Jiang, Y., Jansen, B. J., & Spink, A. (2015). Understanding interactions of task difficulty and learning in web search. In *Proceedings of the 5th Information Interaction in Context Symposium*.

Mayer, R. E., & Chandler, P. (2001). When learning is just a click away: Does simple user interaction foster deeper understanding of multimedia messages? *Journal of Educational Psychology*, 93(2), 390–397.

Paas, F. G., & van Merriënboer, J. J. (1994). Instructional control of cognitive load in the training of complex cognitive tasks. *Educational Psychology Review*, 6(4), 351–371.

Rodrigues, K., Bhatt, N., Bretan, M., & Rubin, J. (2020). Scroll behavior as a predictor of cognitive load in information-dense interfaces. In *Proceedings of the ACM Conference on Human Factors in Computing Systems*.

Sauro, J., & Dumas, J. S. (2009). Comparison of three one-question, post-task usability questionnaires. In *Proceedings of the SIGCHI Conference on Human Factors in Computing Systems* (pp. 1599–1608).

Sweller, J. (1988). Cognitive load during problem solving: Effects on learning. *Cognitive Science*, 12(2), 257–285.

Sweller, J. (2010). Element interactivity and intrinsic, extraneous, and germane cognitive load. *Educational Psychology Review*, 22(2), 123–138.

Sweller, J., Chandler, P., Tierney, P., & Cooper, M. (1990). Cognitive load as a factor in the structuring of technical material. *Journal of Experimental Psychology: General*, 119(2), 176–192.

Sweller, J., van Merriënboer, J. J., & Paas, F. G. (1998). Cognitive architecture and instructional design. *Educational Psychology Review*, 10(3), 251–296.

Van Gog, T. (2014). The signaling (or cueing) principle in multimedia learning. In R. E. Mayer (Ed.), *The Cambridge Handbook of Multimedia Learning* (2nd ed., pp. 263–278). Cambridge University Press.

---

*Personal project. All work is the author's own and is not affiliated with any employer.*
*GitHub: github.com/kgkazakos/cognitive-load-monitor*
