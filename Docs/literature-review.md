# Literature Review

> **Authoritative version: `Docs/RitikMota_Capstone_LiteratureReview_mk5.pdf`**
> (final, Oct 18, 2026). This file is a working summary for Claude Code. Its
> §1–4 match mk5 §1–4. §4b here is the draft of mk5's **§5
> "Mood-Regulation Interventions and Feedback Delivery"**; mk5 §5 supersedes
> it — it adds [22] Miri et al. (PIV design study, TOCHI 2020) and [23]
> Lowe-Brown et al. (iso principle, no advantage after anxiety induction,
> Musicae Scientiae 2026), replaces [21] with a single thesis (van Oostrum
> 2024), and corrects [8] and [10]. If this file and the PDF disagree, the
> PDF wins.

Ten papers, reviewed across four themes. Each theme ends with an explicit
note on how it shaped MoodBand's design — not just a summary of findings.

## 1. Affective Computing Fundamentals

- **[1] Picard, *Affective Computing* (1997, MIT Press)** — the foundational
  text establishing that computers can be built to recognize and respond to
  emotional states.
- **[2] Conceição et al., "Deep-seeded clustering for emotion recognition
  from wearable physiological sensors"** (arXiv:2308.09013) — grounds mood
  classification in Russell's circumplex model (valence/arousal axes), using
  a wrist-worn device, same form factor as MoodBand's target hardware.

**Why this matters for MoodBand**: together these justify the core premise
(physiological signals → discrete mood categories) and specifically justify
grounding MoodBand's mood labels (happy, sad, stressed, angry, neutral) in
the valence/arousal circumplex model rather than an ad hoc labelling scheme.

## 2. Wearable Physiological Sensing

- **[3] Saganowski et al., systematic review** (IEEE Trans. Affective
  Comput., 2023) — heart rate, HRV, and EDA dominate the literature as the
  go-to signals for everyday emotion recognition; flags that lab-to-real-world
  transfer is hard.
- **[4] Velu et al., "Integrating Fitbit wearables..."** (Appl. Sci., 2025) —
  uses the **LifeSnaps** dataset (Fitbit Sense), predicts anxiety from
  everyday wearable data. Primary evidence that consumer-grade Fitbit data
  carries real signal, not just noise.
- **[5] King et al., "Machine learning-based context aware EMAs"** (arXiv:
  2506.15834, 2025) — documents real Fitbit API data-quality constraints:
  step counts of zero while charging, missing HR when not worn, and
  critically, **HRV is only computed overnight**.

**Why this matters for MoodBand**: [4] and [5] both use Fitbit specifically,
which is directly relevant since Fitbit is the device MoodBand uses. The HRV
constraint in [5] carries directly into the classification design — HR and
motion are the real-time, waking-state features; HRV is a supplementary
overnight-only signal. (Note: this finding was based on the **legacy** Fitbit
Web API, which Google retired in Oct 2026 in favor of the new Google Health
API — worth re-confirming whether this constraint still holds under the new
API before relying on it further.)

## 3. Mood/Emotion Classification Models

- **[6] Pataca et al., systematic review** (Comput. Biol. Med., 2025) —
  Random Forest and SVM dominate wearable-based stress-detection studies;
  Random Forest performs especially well on EDA and HRV features.
- **[7] Irfan et al., "Emotion recognition with minimal wearable sensing"**
  (IEEE BIBM, 2025) — designs classifiers for resource-constrained, on-device
  deployment; finds personalized models can beat generalized ones even with
  limited per-person data.

**Why this matters for MoodBand**: [6] is why **Random Forest is the primary
candidate classifier** — it's the best-performing classical model on this
kind of data, and lighter-weight than a deep-learning approach that would be
harder to justify running on a phone or small backend. [7] is why the
project should evaluate a **personalized model strategy alongside a
generalized one** — MoodBand's own user trial will necessarily be small.

## 4. Accessible Feedback Design

- **[8] iFeeling** (ur Réhman & Liu) — renders detected emotion as a
  distinct phone-vibration pattern, built for visually impaired users. Direct
  precedent for MoodBand's haptic channel.
- **[9] Jiang et al., systematic review of haptic feedback for blind/low-
  vision users** (arXiv:2412.19105, 2024) — 132 papers, 2004–2024. Used to
  check iFeeling's design choices against the wider field.
- **[10] Yeo & Chew, qualitative study of mobile app accessibility among
  Singapore's visually impaired community** — screen readers do not reliably
  work in practice; recommends combining audio *and* haptic feedback, never
  relying on either alone.

**Why this matters for MoodBand**: [8] directly shaped the vibration-pattern
feedback design. [9] broadened it (e.g., graduated/directional vibration
intensity). [10] is the reason **every visual cue has a corresponding audio
or haptic equivalent by default** — a screen-reader-compatible UI alone is
not treated as sufficient.

## 4b. Mood-Regulation Interventions and Delivery Timing (added Oct 15, 2026)

> **Citations verified through LibKey (Oct 15, 2026)** except where marked.
> Effect sizes were taken from abstracts/summaries — confirm against the
> full text before quoting them in a report. Full references at the end of
> this section.

Sections 1-4 cover *how* to deliver feedback accessibly. This section covers
*which* interventions help each mood and *when* to deliver them — evidence
for the feedback-decision module (`Docs/feedback-module-plan.md`).

- **JITAI framework** — Nahum-Shani et al. 2018 [11]. Components: decision points, tailoring
  variables (vulnerability vs. receptivity), intervention options, decision
  rules. The feedback-decision module is a JITAI decision rule.
- **Breathwork for stress** — Fincham et al. 2023 [12]:
  12 RCTs, stress g ≈ −0.35; anxiety g ≈ −0.32; depression g ≈ −0.40.
  Shao et al. 2024 [13]: slow-paced breathing — clear
  cardiovascular effects, perceived stress only marginal (SMD −0.51, p=.06).
- **Vibrotactile breathing pacer** — Miri et al., CHI 2020 [14]:
  wearable vibration-guided slow breathing reduced anxiety under a cognitive
  stressor (d = .33); strong-exhale patterns worked best; personalization
  mattered.
- **Slow false-heartbeat haptics** — EmotionCheck, Costa et al. 2017 [15]: wrist taps slightly slower than actual heart rate reduced
  anxiety (67 participants).
- **Music for stress** — de Witte et al. 2020 [16]: 104 RCTs; physiological d ≈ .38, psychological
  d ≈ .55, largest effect on heart rate.
- **Iso principle for sadness** — Starcke et al. 2021 [17]: after induced sadness, sad-then-happy music ended with more
  positive affect than happy music alone. Small samples.
- **Detection-based stress interventions** — Koh et al., CHI 2026 [18]
  (systematic review, 52 studies): just-in-time delivery is most common but
  causes unwanted-moment interruptions, fatigue, attrition; "perceptual
  mismatch" (exercise flagged as stress) erodes trust; recommends
  human-in-the-loop correction and explaining *why*.
- **User response to stress alerts** — veteran cycling trial [19]: alerts
  felt "overly sensitive"; brief, interpretable notifications preferred.
  Law-enforcement smartwatch study, Jetelina et al. 2022 [20]: a vibration when HR stays high was among the most useful
  features. Twente two-week studies [21]: stress feedback did not raise average
  stress, but individuals varied — some felt more stressed.

**Why this matters for MoodBand**: haptic breathing pacing (PIV++,
EmotionCheck) is evidence-backed *and* inherently non-visual — ideal for
visually impaired users. Sadness audio should follow the iso principle
rather than jump to upbeat music. The module must avoid alert fatigue
(confidence gating, cooldowns), avoid flagging exercise as stress, phrase
feedback as suggestions, and let users confirm/correct detections. No solid
evidence was found for anger-specific interventions or for routine positive
feedback on happy/neutral states.

**References for §4b**

11. I. Nahum-Shani, S. N. Smith, B. J. Spring, L. M. Collins, K. Witkiewitz, A. Tewari, and S. A. Murphy, "Just-in-time adaptive interventions (JITAIs) in mobile health: Key components and design principles for ongoing health behavior support," Ann. Behav. Med., vol. 52, no. 6, pp. 446–462, 2018. doi:10.1007/s12160-016-9830-8 (open access)
12. G. W. Fincham, C. Strauss, J. Montero-Marin, and K. Cavanagh, "Effect of breathwork on stress and mental health: A meta-analysis of randomised-controlled trials," Sci. Rep., vol. 13, p. 432, 2023. doi:10.1038/s41598-022-27247-y (open access)
13. R. Shao, I. S. C. Man, and T. M. C. Lee, "The effect of slow-paced breathing on cardiovascular and emotion functions: A meta-analysis and systematic review," Mindfulness, vol. 15, no. 1, pp. 1–18, 2024. doi:10.1007/s12671-023-02294-2 (Northeastern access)
14. P. Miri, E. Jusuf, H. Margarit, R. Flory, A. Uusberg, K. Isbister, K. Marzullo, and J. J. Gross, "Evaluating a personalizable, inconspicuous vibrotactile (PIV) breathing pacer for in-the-moment affect regulation," in Proc. CHI 2020. doi:10.1145/3313831.3376757 — *not indexed in LibKey; DOI confirmed via NSF PAR record 10147095*
15. J. Costa, A. T. Adams, M. F. Jung, F. Guimbretière, and T. Choudhury, "EmotionCheck: A wearable device to regulate anxiety through false heart rate feedback," GetMobile, vol. 21, no. 2, pp. 22–25, 2017. doi:10.1145/3131214.3131222 (open access)
16. M. de Witte, A. Spruit, S. van Hooren, X. Moonen, and G.-J. Stams, "Effects of music interventions on stress-related outcomes: A systematic review and two meta-analyses," Health Psychol. Rev., vol. 14, no. 2, pp. 294–324, 2020. doi:10.1080/17437199.2019.1627897 (Northeastern access)
17. K. Starcke, J. Mayr, and R. von Georgi, "Emotion modulation through music after sadness induction—The iso principle in a controlled experimental study," Int. J. Environ. Res. Public Health, vol. 18, no. 23, p. 12486, 2021. doi:10.3390/ijerph182312486 (open access)
18. Y. Koh, J. Kim, K. Lee, Y. Jung, H. Hong, and U. Lee, "Exploring data-driven approaches to stress management: A systematic review of stress tracking, intervention, and system evaluation methods," in Proc. CHI 2026. doi:10.1145/3772318.3791194 — *not yet indexed in LibKey; DOI from the authors' PDF, confirm in the ACM Digital Library*
19. "Ride, Track, and Recover: Pilot randomized trial of a wearable digital self-management intervention during a veteran endurance-cycling program," arXiv:2606.13529 — *preprint, not peer-reviewed; no DOI*
20. K. K. Jetelina, R. Molsberry, L. Malthaner, A. Beauchamp, M. B. Cannell, T. Hall, E. Fowler, and L. Anderson, "Acceptability of a real-time notification of stress and access to self-help therapies among law enforcement officers," BMC Public Health, vol. 22, p. 32, 2022. doi:10.1186/s12889-021-12423-y (open access)
21. University of Twente bachelor's/master's theses on wearable stress feedback (2024–2025), e.g. essay.utwente.nl/essays/107074 — *student theses, not peer-reviewed; cite with caution*

## 5. Synthesis

Physiological signals can be mapped onto discrete moods [1], [2]. A
consumer wearable like Fitbit is a workable, if imperfect, way to collect
those signals [3]–[5]. Classical, lightweight models are a sensible fit for
the classification step given the deployment constraints [6], [7]. Haptic
feedback has real precedent for communicating affective state to visually
impaired users [8]–[10]. What doesn't exist yet in the literature is a
single system tying all four pieces together into one mobile-first pipeline
— the gap MoodBand aims to fill.

## 6. Sensor Recommendations Across Reviewed Papers

| Paper | Sensors Used / Recommended |
|---|---|
| [1] Picard (1997) | N/A — conceptual/foundational, no specific sensor |
| [2] Conceição et al. | PPG (heart rate/BVP), EDA, skin temperature (Empatica E4) |
| [3] Saganowski et al. (review) | Heart rate, HRV, EDA (dominant signals across the literature) |
| [4] Velu et al. (LifeSnaps/Fitbit) | Heart rate, Fitbit stress score, sleep, steps |
| [5] King et al. | Heart rate, HRV (sleep-only), steps/motion |
| [6] Pataca et al. (review) | EDA, HRV (RF performs best on these two) |
| [7] Irfan et al. | ECG (minimal wearable sensing) |
| [8] iFeeling | N/A — haptic output paper, not sensing |
| [9] Jiang et al. (review) | N/A — haptic feedback review, not sensing |
| [10] Yeo & Chew | N/A — qualitative UX study, not sensing |
| **MoodBand will use** | **Heart rate (continuous) + motion/accelerometer (continuous), HRV as a supplementary overnight-only signal** |

**Rationale**: these are the signals consistently available through a
consumer-grade, cross-platform-friendly wearable API (Fitbit via Google
Health API). EDA and skin temperature (used in the lab-grade Empatica E4 in
[2], recommended generally in [3] and [6]) are not exposed by any mainstream
consumer wearable's public API. ECG ([7]) requires dedicated hardware not
available through Fitbit's consumer API. MoodBand's sensor set reflects the
intersection of what the literature recommends and what a consumer,
cross-platform wearable API actually exposes.

## 7. Device Selection Summary

Four candidates were compared: Fitbit, Apple Watch, Samsung Galaxy Watch,
WHOOP. Full reasoning in `decisions.md`; condensed comparison:

| Criterion | Fitbit | Apple Watch | Samsung Galaxy Watch | WHOOP |
|---|---|---|---|---|
| Price (new/used) | $70–130 / $30–80 | $220–250 / $120–180 | $170–310 / $100–150 | Bundled w/ membership |
| Works on Android? | Yes | **No** (iPhone-only) | Yes | Yes |
| Works on iOS? | Yes | Yes | **No** (continuous streaming is Android-only) | Yes |
| API approval needed? | No (new Google Health API) | No (HealthKit) | Only for cloud API (1–2 wks) | Free API, but needs paid membership to return data |
| Real-time daytime HR? | Yes, 5-sec resolution | Yes (workout mode) | Yes (on-device SDK) | **No** — no continuous/raw HR via API |
| Matches lit. review? | Yes — [4],[5] used Fitbit directly | No | No | No |

**Decision: Fitbit, via the Google Health API.** Deciding factor: the app
must support both Android and iOS, which structurally rules out Apple Watch
and Samsung regardless of their other merits. WHOOP is ruled out
independently (no continuous HR via API at all, subscription-gated).

## References

1. R. W. Picard, *Affective Computing*. Cambridge, MA, USA: MIT Press, 1997.
2. M. A. Conceição, A. Dubois, S. Haustein, B. Miranda, and C. L. Azevedo, "Deep-seeded clustering for emotion recognition from wearable physiological sensors," arXiv:2308.09013, 2023 (revised 2025).
3. S. Saganowski, B. Perz, A. G. Polak, and P. Kazienko, "Emotion recognition for everyday life using physiological signals from wearables: A systematic literature review," IEEE Trans. Affective Comput., vol. 14, no. 3, pp. 1876–1897, 2023.
4. A. Velu, J. Ramesh, A. Ahmed, S. Ganguly, R. Aburukba, A. Sagahyroon, and F. Aloul, "Integrating Fitbit wearables and self-reported surveys for machine learning-based state–trait anxiety prediction," Appl. Sci., vol. 15, no. 19, p. 10519, 2025.
5. Z. D. King, M. Khalid, H. Yu, K. Shibuya, K. Zanna, M. Majd, R. L. Brown, Y. Shen, G. Kypriotakis, T. Vaessen, C. P. Fagundes, and A. Sano, "Machine learning-based context aware EMAs: An offline feasibility study," arXiv:2506.15834, 2025.
6. A. O. Pataca, E. Zdravevski, P. J. Coelho, N. M. Garcia, M. Deryuck, C. Albuquerque, and I. M. Pires, "Use of machine learning for predicting stress episodes based on wearable sensor data: A systematic review," Comput. Biol. Med., vol. 198, pt. A, p. 111166, 2025.
7. M. Irfan, A. Nawaz, A. K. Bulbul, R. Klén, A. Subasi, T. Westerlund, and W. Chen, "Emotion recognition with minimal wearable sensing: Multi-domain feature, hybrid feature selection, and personalized vs. generalized ensemble model analysis," in Proc. 2025 IEEE Int. Conf. Bioinformatics and Biomedicine (BIBM), 2025, pp. 5447–5453.
8. S. ur Réhman and L. Liu, "iFeeling: Vibrotactile rendering of human emotions on mobile phones."
9. C. Jiang, E. Kuang, and M. Fan, "How can haptic feedback assist people with blind and low vision (BLV): A systematic literature review," arXiv:2412.19105, 2024.
10. Y. P. H. Jesvin and C. K. Hao, "A framework for inclusive mobile application design: Insights from Singapore's visually impaired community," ADADA, vol. 29, suppl. 1, pp. 46–XX, 2024.
