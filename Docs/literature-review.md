# Literature Review

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
