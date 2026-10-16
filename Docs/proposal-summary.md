# Project Proposal — Summary

Condensed from the full proposal document (`Capstone_Project_Proposal_MoodBand_Revised.docx`,
kept outside this repo / in the course drive). This summary is what Claude
Code needs day-to-day; go to the full doc for formal/submission purposes.

## Aim

Design, develop, and evaluate a mood-detection system that leverages a
Fitbit wearable to sense a user's physiological signals, classifies their
emotional state in real time, and delivers adaptive auditory, haptic, or
visual feedback through a companion mobile app — for both sighted and
visually impaired users, on both Android and iOS.

## Objectives

1. Review literature on affective computing, wearable sensing, and
   accessible feedback (**done** — see `literature-review.md`).
2. Integrate with Fitbit via the Google Health API for real-time
   heart-rate/HRV/motion data, on both Android and iOS.
3. Train a classifier for mood categories: happy, neutral, sad, stressed,
   angry.
4. Design a feedback-decision module mapping mood + accessibility profile →
   intervention.
5. Implement auditory/haptic/visual feedback in the companion app,
   accessible via screen readers.
6. Evaluate classification accuracy and perceived feedback effectiveness
   with sighted and visually impaired participants.

## Scope

**In scope**: Fitbit integration via Google Health API; the
mood-classification pipeline; the companion mobile app delivering
auditory/haptic/visual feedback; a limited set of discrete mood categories
(not a continuous emotional spectrum); evaluation with a small user sample.

**Explicitly flexible**: processing and feedback-decision logic can run on
mobile, laptop, or cloud — see `decisions.md` §4. Only feedback-actuation is
pinned to the phone.

**Out of scope**: custom wearable hardware; long-term clinical validation;
mass-manufacturing; third-party health platforms beyond the Google Health
API; teaching visually impaired users to interpret colour-based cues
directly (a separate, non-trivial idea proposed as a follow-on project, not
part of this one).

## Methodology phases

**Phase 1 (offline)**: build and validate the mood-classification model,
feedback-decision logic, and mobile app end-to-end using public datasets
(`datasets.md`) as a stand-in for live sensor data.

**Phase 2 (live integration)**: once Phase 1 works, integrate the live
Fitbit sensing layer via the Google Health API in place of the offline
dataset.

Data collection protocol (for the project's own small-scale trial, after
Phase 1): volunteer participants exposed to mood-inducing stimuli (calming
music, stressful timed tasks, neutral video) while Fitbit signals are logged
and self-reported mood is collected as ground truth.

## Feedback mapping (illustrative, from the proposal's Table 1/4)

| Mood Detected | Sighted Users | Visually Impaired Users |
|---|---|---|
| Stress / Anxiety | Cool-toned in-app colour pulse + on-screen breathing animation | Slow-paced phone vibration synced with spoken breathing cues |
| Sadness | Warm colour cue + suggested uplifting playlist | Gentle spoken affirmation + calming audio track |
| Anger / Frustration | Red-to-green fading colour cue as a calming timer | Descending vibration intensity + guided calming voice prompt |
| Neutral / Happy | Soft green confirmation banner, no interruption | Brief pleasant chime, no interruption |

## Timeline (16 weeks, revised ordering)

| Phase | Weeks |
|---|---|
| Literature review & requirements | 1–2 |
| Dataset acquisition & preprocessing | 1–6 |
| Mood-classification model training (offline) | 3–10 |
| Feedback module development | 3–10 |
| Mobile companion app development | 7–13 |
| Offline system integration & testing (no live wearable) | 11–13 |
| Fitbit / Google Health API integration & setup | 11–16 |
| End-to-end testing with live wearable data | 14–16 |
| User trials (sighted & visually impaired) | 14–16 |
| Evaluation, documentation & final report | 14–16 |

Note the deliberate ordering: app/model/feedback work happens before live
Fitbit integration (see `decisions.md` §5).

## Budget (minimal — no custom hardware)

Fitbit device ($30–130 if not already owned), Google Health API access
(free), Flutter/React Native + Figma (free), Firebase (free tier), plus a
small contingency (~$55 total software/misc cost).

## Expected outcomes

- Cross-platform mobile app connecting to Fitbit via Google Health API
- Trained mood-classification model (≥4 categories)
- In-app feedback subsystem (auditory, haptic, visual)
- Accessible, screen-reader-compatible interface
- Usability evaluation report
- Documented, extensible architecture
