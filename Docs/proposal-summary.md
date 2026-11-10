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

## Changes since mk3 (for the next proposal revision)

What has happened since mk3 was sent (Oct 21, 2026). The next revision of
the proposal should take these in; detail is in `decisions.md`.

- **Model benchmark done** (§7.2; #15): six models compared on identical
  participant-grouped splits. RBF SVM 0.351, Random Forest 0.334, logistic
  regression 0.316, small neural network 0.311, gradient boosting 0.297,
  majority class 0.250 (balanced accuracy, 5 seeds). Confusion matrices for
  every model.
- **Extra Fitbit signals don't help** (#16): activity-adjusted heart rate,
  calories, exercise, longer context and last night's sleep, HRV, SpO2 and
  skin temperature don't beat the 12 heart-rate-and-steps features for
  unseen people; the overnight ones lower accuracy by 0.02–0.05. Heart rate
  + motion stays the real-time input.
- **The Random Forest stays the model** (#17): the SVM's lead disappears once
  it gives the probabilities the feedback module needs (0.320; never predicts
  sad), and in the feedback replay it suggests no breaks at all.
- **Combining models and personalization** (#19), answering Prof. Zantout's
  mid-term question: voting and stacking don't raise usable accuracy. Using
  a person's past moods would (~0.33 → 0.40–0.43), but mostly by learning
  their usual moods rather than reading their body, so it is **ruled out**.
- **Project aim stated as a proof of concept** (#20): MoodBand tests whether
  mood can be reliably predicted from physiological signals; if it can, the
  next step after the capstone is a custom wearable. The model therefore
  uses physiological and motion signals only, never past mood reports, and
  is evaluated on unseen people. The proposal's aim and objectives should
  say this explicitly.
- **Offline integration done ahead of the timeline** (Table 5, weeks 11–13;
  #18): the app's Replay mode plays recorded LifeSnaps days through the real
  model and decision module (running on the laptop), delivers each
  suggestion as a notification, and saves every answer. Tested on iPhone.
  The session's first screen now offers **Start / Not now / Snooze for an
  hour** (§7.3–7.4).
- **Mid-term presentation** given Oct 28, 2026 (well received).
- **Fitbit arrived** (by Nov 9): next are the Google Health API prototype
  (heart-rate resolution, whether HRV is overnight-only, sign-in on Android
  and iOS) and the wrist-alert test.
- **Data access** (§7.2): EmoPhone still pending (follow-up email being
  sent); TILES-2018 data-use agreement still with Prof. Zantout. Anger
  remains required, so the five-mood model waits on these.
- **User trial**: starts once the consent agreement is in place
  (unchanged).
