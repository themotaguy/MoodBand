# Project Proposal — Summary

Condensed from the current proposal, **`Docs/Capstone_Project_Proposal_MoodBand_mk3.pdf`**
(Oct 2026; sent to Prof. Zantout Oct 21, 2026 after his request in
decisions.md #14). mk3 embeds the final literature review (mk5) and the
current design. `…_mk2.pdf` is the superseded original. If this file and the
PDF disagree, the PDF wins; if a later decision in `decisions.md` changes
something, record it there and update the proposal at the next revision.

## Aim

Design, develop, and evaluate a mood-detection system that uses a Fitbit to
sense physiological signals, classifies emotional state in near real time,
and delivers adaptive auditory, haptic, or visual feedback through a
companion app — for sighted and visually impaired users, on Android and iOS.

## Objectives (§3.2)

1. Review literature on affective computing, wearable sensing, mood
   classification, accessible feedback, and mood-regulation interventions.
2. Integrate with Fitbit via the Google Health API (heart rate + motion, near
   real time, Android and iOS).
3. **Train and benchmark** models classifying **five** moods: happy, neutral,
   sad, stressed, angry.
4. Feedback-decision module deciding *whether and how* to intervene from
   mood, confidence, recent context, and accessibility profile.
5. Auditory, haptic, and visual feedback in the app, screen-reader accessible.
6. Evaluate classification on public datasets and the project's own data;
   evaluate feedback in a small user trial.

## Scope (§4)

In: Fitbit via Google Health API; classification pipeline; companion app;
discrete mood categories; small user trial (only after the supervisor
confirms the user-trial/consent agreement). Processing and decision stages
may run on phone, laptop, or cloud; feedback actuation (speaker, vibration,
screen, notifications) runs on the phone.
Out: custom hardware; clinical validation; mass manufacturing; platforms
beyond the Google Health API; teaching visually impaired users to decode
colour cues (proposed as a follow-on project).

## Methodology (§7)

- **Two phases**: offline (model + feedback module + app on public datasets)
  first, then live Fitbit integration and the user trial.
- **Data and model** (§7.2): LifeSnaps primary (1,961 reports, 61
  participants; 30-min windows); Random Forest ~0.33 balanced accuracy vs
  0.25 chance; benchmark against an SVM and a small neural network, with
  confusion matrices for every model and dataset. Anger requires more data:
  EmoPhone (wave D-3 anger ratings) requested; TILES-2018 adds stress/affect
  data (anger items unconfirmed), needs a DUA signed for Northeastern.
- **Feedback logic** (§7.3): confidence ≥ 0.45 and 0.10 margin; 2-of-3
  persistence; exercise filter (stressed/angry); 30-min cooldown, 4/day cap,
  quiet hours, snooze; no feedback for continuing happy/neutral; recovery cue.
  Suggestion framing, **explicit go-ahead before any intervention**, "Was
  this right?" labels, on-demand break.
- **App** (§7.4): React Native + Expo; two-step delivery (notification, then
  session after the user agrees), since phone haptics are only felt in the
  hand (decisions.md #13); Fitbit wrist-notification mirroring to be tested.
- **Evaluation** (§7.5): participant-grouped CV, balanced accuracy and
  macro-F1, multi-seed averages, confusion matrices; replay simulation for
  the feedback module; on-device checklist for the app. **User trial with
  friends** — not expected to include visually impaired users (stated
  limitation; VI profiles checked via on-device screen-reader testing).

## Feedback (§8)

Table 3 (mood → intervention): stressed → breathing pacer (~6 breaths/min,
strong-exhale vibration; heartbeat tap and music as alternatives); sad →
iso-principle music; angry → calming timer (design choice); happy/neutral →
nothing; recovery → brief quiet cue. Table 4 (profiles): sighted → visual +
haptic; low vision → audio + haptic, optional high-contrast visuals; blind →
always audio + haptic, deferred audio when silenced, never visual-only.
Detail and evidence: `feedback-module-plan.md`, lit review §5.5.

## Timeline (§11, Table 5)

| Phase | Weeks |
|---|---|
| Literature review & requirements | 1–2 |
| Dataset acquisition (LifeSnaps; EmoPhone D-3; TILES-2018) | 1–10 |
| Model training & benchmarking (offline) | 3–13 |
| Feedback module development | 3–10 |
| Mobile app development | 7–13 |
| Offline integration & testing | 11–13 |
| Fitbit / Google Health API integration | 11–16 |
| End-to-end live testing; user trial; evaluation & report | 14–16 |

## Budget (§12, Table 6)

Fitbit (Inspire 3 recommended) bought by the supervisor; Google Health API,
React Native/Expo, Firebase free tier: $0; **Apple Developer Program $99/year**
(TestFlight for trial participants — free signing expires after 7 days);
miscellaneous $50; contingency $15. **Total ≈ $164** excluding the Fitbit.
