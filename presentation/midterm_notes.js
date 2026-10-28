// Presenter notes for the mid-term deck, one entry per slide (slide 1 first).
// Written to glance at while presenting: time, key points, then the link to the next slide.
// Total is about 10 minutes of slides plus a 2-minute live demo on slide 10.
module.exports = [
  // 1 — Title
  `[~20 sec]

- MoodBand: detects mood from a Fitbit and responds with feedback you can see, hear or feel.
- Designed from the start for sighted AND visually impaired users.
- Plan: the problem and the idea, what's built so far, what's left.

NEXT: start with what's wrong with today's mood tools.`,

  // 2 — Problem
  `[~45 sec]

Three gaps:
- SELF-REPORT: most apps rely on people remembering to log their mood. Easy to forget, always after the fact.
- NO CLOSED LOOP: they chart mood but rarely help regulate it in the moment.
- VISUAL-FIRST: dashboards and colour charts exclude visually impaired users. My lit review found screen readers don't reliably fill that gap.

MoodBand targets all three.

NEXT: here's how.`,

  // 3 — Solution / pipeline
  `[~1 min]

Four stages, left to right:
- SENSE: heart rate AND steps (motion) from a Fitbit, through Google's cloud API. That's why it works on both Android and iOS.
- CLASSIFY: a model reads the last 30 minutes: happy, neutral, sad, stressed, angry.
- DECIDE: speaks only when confident, persistent, and not right after exercise.
- FEEDBACK: the phone plays audio, vibration or visual cues to suit the user's profile.

Bottom line: built and tested offline on public data first; live Fitbit and the user trial come last (as advised).

NEXT: what's done so far.`,

  // 4 — Progress
  `[~30 sec, keep it quick]

Six milestones done:
- Literature review (23 references) and the updated proposal.
- First mood model and a benchmark of six models.
- Feedback-decision module, 23 automated tests.
- iPhone prototype, tested end to end.

NEXT: the next slides go through the technical pieces, starting with the model.`,

  // 5 — First model
  `[~1 min]

- Data: LifeSnaps, a public Fitbit study. 71 people over about 4 months; 1,961 in-the-moment mood reports from 61 of them, mapped to 4 moods (no anger label in this dataset).
- For each report: heart rate and steps from the 30 minutes before it, exactly what the app will see live.
- KEY POINT: tested only on people the model never saw in training.
- Result: 0.33 balanced accuracy vs 0.25 chance. A real signal, but a modest one. Be honest about this.
- Tried and dropped: last night's HRV and sleep (hurt accuracy on new people); PMData (labels only once a day).

NEXT: would a more complex model do better?`,

  // 6 — Benchmark
  `[~1.5 min, the key technical slide]

Six models, identical data and splits, 5 seeds.

1. The SVM edges out the Random Forest on plain predictions: 0.351 vs 0.334, on every split, mainly by catching sad.
2. BUT the feedback module needs probabilities to decide when to act. With probabilities the SVM drops to 0.320 and never predicts sad. In the simulation it never suggested a break. So the Random Forest stays.
3. More complex isn't better: gradient boosting and the neural network do worse.

Also tried every extra signal the Google Health API offers (activity-adjusted HR, calories, exercise, sleep, HRV, oxygen, skin temperature): none helped on new people; the overnight ones hurt.

TAKEAWAY: the limit is the signal and the number of people, not the model. Next steps: more data, and learning each user's own patterns.

NEXT: where exactly the errors are.`,

  // 7 — Confusion matrices
  `[~45 sec]

- How to read it: each ROW is a mood people reported; the cells show how often the model predicted each mood. Rows add up to 100%.
- Both models mix up neutral with stressed and happy. Expected: heart rate and steps look similar across those states.
- The sad row is the SVM's advantage: 32% vs 17%. But as the last slide showed, it disappears once the SVM gives probabilities.

NEXT: once we have a mood, what do we do about it?`,

  // 8 — Feedback catalog
  `[~1 min]

Left, one response per mood:
- STRESSED: breathing pacer at 6 breaths a minute, felt as vibration (breathwork and haptic-pacer studies).
- SAD: music that matches a low mood, then brightens (the iso principle; only one small study).
- ANGRY and RECOVERY: marked as design choices to test; no direct evidence yet.
- HAPPY / NEUTRAL: nothing, to avoid alert fatigue.

Right, three accessibility profiles:
- Sighted: visual + vibration.
- Low vision: audio + vibration, optional high contrast.
- Blind: audio + vibration, never visual-only.

NEXT: because the model is modest, the module is deliberately careful about when it speaks.`,

  // 9 — Decision module
  `[~1 min]

Rules:
- Acts only on a confident prediction that persists.
- Ignores "stressed" right after exercise.
- At most 4 a day, 30 minutes apart, never at night.
- Always asks first, then "Was this right?".

Simulated on 1,295 real days (about 101,000 predictions):
- About 1.2 suggestions per person per day.
- 1 in 3 match the person's reported mood (chance: 1 in 4).

KEY INSIGHT: a stricter threshold cuts interruptions, not errors. The model's confidence doesn't track whether it's right. That's why it asks first and learns from "Was this right?".

NEXT: here it is running on a real phone.`,

  // 10 — iPhone prototype + LIVE DEMO
  `[~1 min slide + ~2 min demo]

The flow (left to right):
- A notification: "Want a 1-minute breathing break?"
- Nothing plays until the user taps Start (or Not now / Snooze for an hour).
- The break: vibration, breathing circle and voice.
- Ends with "Was this right?": yes, no or snooze, kept as a label.

React Native, so one codebase for Android and iOS.

Testing changed the design twice:
- Vibration is only felt in the hand, so suggestions arrive as a notification first.
- VoiceOver talked over the app's own voice, so guidance now goes through VoiceOver.

LIVE DEMO (say: "and now with the real model and decision module connected"):
1. BEFORE THE TALK: server running on the laptop (.venv/bin/python -m feedback.server); app shows the days after Load days.
2. Phone: Replay, tap the first day, Start replay.
3. Explain while waiting: one recorded hour per minute; the clock, the model's mood and its reason update live.
4. First suggestion (10:10) arrives about 2 min 10 sec after Start.
5. Open it, tap Start (or Snooze), answer "Was this right?". Point out: the answer is saved on the laptop with the person's real reported mood.
6. Stop replay.
IF WI-FI FAILS: skip it and walk through the four steps on this slide.

NEXT: what's left.`,

  // 11 — What's left
  `[~45 sec]

Three phases, following the proposal's timeline:
- WEEKS 7–10, DATA AND MODEL: anger is required, so I need EmoPhone and TILES-2018. Then train the five-mood model and re-run the benchmark on each dataset.
- WEEKS 11–13, INTEGRATION: partly done early. The app already plays recorded days through the real model and decision module and saves each answer as a label (what you just saw). Left: the live Fitbit through the Google Health API.
- WEEKS 14–16: user trial once consent is in place, then evaluation and the final report.

NEXT: the risks, and where I need support.`,

  // 12 — Risks + Q&A
  `[~45 sec, then questions]

- DATASET ACCESS: EmoPhone request pending; the TILES-2018 agreement needs a Northeastern signature. THIS IS THE ASK.
- MODEST SIGNAL: heart rate and steps carry limited mood information; the plan is to learn each person's patterns from their answers.
- TRIAL PARTICIPANTS: friends only, so no visually impaired users. Stated as a limitation; accessibility checked with VoiceOver.
- CONSENT: confirm the user-trial agreement before recruiting.

"Thank you, happy to take questions."

LIKELY QUESTIONS:
- Is 0.33 good enough? Not on its own. That's why it asks first, acts cautiously, and will learn each user from "Was this right?".
- Only heart rate? No: heart rate + steps live; overnight HRV, sleep, SpO2 and skin temperature were tested and didn't help.
- Why not an Apple Watch? iPhone-only. The app must work on Android and iOS; the Google Health API makes Fitbit cross-platform.
- Where does anger come from? EmoPhone and TILES-2018, which is why dataset access is the main risk.
- Why did calibration hurt the SVM? Turning its scores into probabilities (Platt scaling) undoes its class balancing, so it drifts back to the common moods.
- Why not deep learning? About 2,000 labels; the neural network already did worse. The bottleneck is the data, not the model.
- Where does the model run? On the laptop for now. On the phone is the target, but a laptop or cloud backend is allowed; only the feedback must run on the phone.`,
];
