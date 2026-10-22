# Decisions Log

Chronological record of the major decisions made during planning, and why.
Update this file (don't just overwrite history) when a documented decision
changes.

---

## 1. Scope pivot: custom hardware → existing consumer wearable

**Original plan**: build a custom wearable prototype (microcontroller,
PPG/GSR sensors, vibration motor, custom housing).

**Decision**: descope the custom hardware. MoodBand integrates with an
**existing consumer wearable** instead, with the mood-detection and feedback
intervention implemented entirely through a companion mobile app.

**Why**: single student, 16-week timeline. Custom hardware design,
fabrication, and power management were not feasible at that scope.

---

## 2. Device selection: Fitbit (via the Google Health API)

**Candidates considered**: Fitbit, Apple Watch (SE 3), Samsung Galaxy Watch,
WHOOP. Full comparison in `literature-review.md` §7.

**Decision**: Fitbit, integrated via the **Google Health API**.

**Why**: the companion app has a **hard requirement to support both Android
and iOS**. This structurally eliminates:
- **Apple Watch** — can only ever pair with an iPhone. HealthKit is
  excellent (more mature API, HRV sampled throughout the day rather than
  only overnight) but this is irrelevant given the platform constraint.
- **Samsung Galaxy Watch** — continuous real-time streaming requires the
  Samsung Health Sensor SDK, which is Android-only.
- **WHOOP** — ruled out independently of the platform question: its API
  exposes no continuous or raw heart-rate data under any circumstance (only
  post-hoc recovery/strain summaries), and requires an active paid
  membership just to return any data at all, even on a used device.

Fitbit's API is cloud-based (not tied to a phone OS), so the same API calls
return data whether the app runs on Android or iOS — the only shortlisted
device that satisfies the cross-platform requirement.

**Context that shaped timing**: the legacy Fitbit Web API (the one used by
papers [4] and [5] in the lit review) was retired by Google — developer
support ended Sept 30, 2026, full shutdown Oct 30, 2026 — replaced by the
new **Google Health API** (launched March 2026). This is a net positive: the
legacy API required a justification request to unlock sub-daily heart-rate
data; the new API provides 5-second-resolution heart rate by default with no
special approval step. Trade-off: the new API was ~7 months old at decision
time, so some documentation/parity gaps vs. the legacy API should be
expected — **this needs direct testing, see Open Item below.**

---

## 3. Sensor selection: heart rate + motion (continuous), HRV (overnight only)

**Decision**: the classifier's real-time features are heart rate and
motion/accelerometer data. HRV is incorporated only as a supplementary
overnight signal.

**Why**: per paper [5], Fitbit only computes HRV while the user is asleep
and relatively still — it cannot be a live, daytime signal. EDA and skin
temperature (used in lab-grade devices in the literature) are not exposed by
Fitbit's consumer API at all, so they're out of reach regardless of whether
they'd help.

**Open item**: this finding is based on the **legacy** Fitbit Web API. It
needs re-confirming against the new Google Health API specifically — it's
possible (though not yet confirmed) that the new API changes this
constraint. See `CLAUDE.md` outstanding task #2.

---

## 4. Architecture: flexible deployment, not mandatory full on-device

**Decision**: the sense → process → classify → feedback loop is a *logical*
pipeline, not a mandated physical one. Processing (mood classification) and
the feedback-decision logic may run on the mobile device, a connected
laptop, or a cloud backend (e.g., a Firebase Cloud Function) — whichever is
most practical given on-device performance constraints encountered during
development. Full on-device mobile execution is the *target end-state* and
default aim, not a hard requirement.

**Exception**: the feedback-actuation layer (speaker, vibration motor,
screen) necessarily runs on the phone, since that's the hardware the user
directly experiences.

**Why**: came directly from supervisor feedback (Oct 13, 2026 meeting) —
don't over-constrain the architecture to "everything must be on the phone"
when the actual requirement is just that the full loop works end-to-end in
near real time.

---

## 5. Build ordering: offline-first, then live integration

**Decision**: build and validate the mood-classification model,
feedback-decision logic, and mobile app **first**, using publicly available
datasets (see `datasets.md`) as a stand-in for live sensor data. Only once
that offline version works end-to-end does live Fitbit/Google Health API
integration begin.

**Why**: supervisor-directed (Oct 13, 2026 meeting) — de-risks the project
by validating the harder, more novel parts (classification accuracy,
feedback design, accessibility) before spending time on API plumbing, and
avoids blocking all downstream work on API access/approval issues.

**Timeline implication**: in the project proposal's 16-week timeline,
"Fitbit / Google Health API integration & setup" was moved to **after**
"Mobile companion app development," not before it.

---

## 6. Classifier: Random Forest as primary candidate

**Decision**: Random Forest is the primary candidate classifier, with SVM
and a small neural network as alternatives to benchmark against.

**Why**: paper [6] found Random Forest to be the best-performing classical
model specifically on EDA/HRV-style wearable features across the reviewed
literature. It's also far lighter-weight than a deep-learning approach,
which matters given inference may need to run on a phone or a lightweight
backend rather than a full server.

**Also consider**: paper [7] found personalized models can outperform
generalized ones even with limited per-person data — worth evaluating a
personalized-model variant alongside a generalized one, given MoodBand's own
user trial will necessarily be small.

---

## 7. "Angry" mood class deferred; classifier trained 4-class for now

> **Superseded Oct 21, 2026** (Decision #14): anger is required in the final
> classifier; deferral holds only until EmoPhone/TILES data is available.

**Decision** (Oct 15, 2026): the classifier is trained on four classes —
happy, neutral, sad, stressed. "Angry" stays in MoodBand's target set and
feedback mapping but is **deferred**: no model work on it until the
supervisor has weighed in (see open items).

**Why**: LifeSnaps, the primary dataset, has no anger label. Confirmed by
`model/explore_lifesnaps.py` on the real hourly CSV — SEMA3 mood options
(one selected per response) are Alert 344, Happy 790, Neutral 822,
Rested/Relaxed 1,178, Sad 149, Tense/Anxious 620, Tired 1,126.
`model/lifesnaps.py` maps Happy/Neutral/Sad → same, Tense/Anxious →
stressed, and drops the rest. The proposal's expected outcome requires ≥4
categories, so 4-class still meets it; Objective 3's five-class target is
the open question.

**First Random Forest baseline** (HR + steps + time of day only; 2,040
labelled hours with a heart-rate reading, 61 participants, "sad" only ~6%):
participant-grouped CV macro-F1 0.30 / balanced acc 0.31 vs. 0.25 chance;
personalized per-participant models balanced acc ~0.39 (33 participants).

---

## 8. Overnight HRV/sleep: not in the generalized model; optional for personalized

**Decision** (Oct 15, 2026): the default (generalized) classifier uses only
real-time features — heart rate, steps, time of day, and HR relative to the
person's own average. Last night's HRV and sleep (from LifeSnaps' daily CSV)
are kept in the code as an optional feature set
(`FEATURE_SETS["realtime+overnight"]` in `model/lifesnaps.py`), in
person-relative form only, for personalized models.

**Why**: tested on LifeSnaps (2,040 labelled hours, 61 participants; last
night's HRV available for 59% of them, sleep for 89%):
- *Generalized* (participant-grouped 5-fold CV, repeated over 5 seeds,
  balanced accuracy): real-time only **0.322** ± 0.007; + raw overnight
  features 0.270; + person-relative overnight features 0.295. Overnight
  features consistently *hurt* on unseen participants — absolute sleep/HRV
  values mostly encode who the person is, not their mood.
- *Personalized* (per-participant chronological 70/30, 33 participants,
  5 seeds): real-time 0.384 → + overnight 0.419 (+0.035; 17 improved, 10
  worse, Wilcoxon p ≈ 0.10). Suggestive, not conclusive.

This refines rather than contradicts §3 (HRV as a supplementary overnight
signal): the signal may matter per person, but not across people. Revisit
with MoodBand's own trial data, where each user's baseline is available.

---

## 9. Classify from the 30 minutes before each mood report (minute-level HR)

**Decision** (Oct 15, 2026): the model is trained on heart-rate and step
features from the **30 minutes before each mood report**, built from the
LifeSnaps MongoDB dump, instead of the hourly CSV. Pipeline:
`model/extract_lifesnaps_mongo.py` (one-off, streams the 9.7 GB
`fitbit.bson` into minute-level files) → `model/windows.py` (features) →
`model/train_baseline.py`.

**Why**:
- *Matches deployment*: the app will classify from the user's last N minutes
  of Fitbit data (Google Health API, 5-second HR), not from hourly averages.
- *Exact timing*: the dump has each SEMA3 response's completion minute and
  heart rate every few seconds (~49M readings → 5.5M minutes; readings with
  confidence 0 dropped). The hourly CSV only knows the report's hour.
- *Verified alignment*: minute HR re-aggregated to hours reproduces the CSV's
  `bpm` exactly (median diff 0.00 bpm), and SEMA3 completion hours match the
  CSV's labelled hours for 99.7% of responses — same local clock, no offset.
- *Slightly better*: participant-grouped CV, 5 seeds, balanced accuracy:
  hourly CSV 0.322 ± 0.011; 10-min window 0.330; **30-min 0.334 ± 0.005**;
  60-min 0.315; 120-min 0.314. "Sad" F1 rises from ~0.08 to ~0.13.

**Caveat**: the gain is real but small — heart rate + steps carry limited
mood signal across people, whatever the resolution. Single-run numbers
(especially personalized, 33 participants with few test labels each) move
by several points between seeds and scikit-learn versions; compare
multi-seed averages.

---

## 10. PMData: cross-dataset check inconclusive; not used for training

**Finding** (Oct 15, 2026): PMData cannot confirm or refute that the
LifeSnaps model generalizes. Its labels are a **daily** PMSys wellness
report (mood and stress, 1-5, 5 = best), mostly filled in right after
waking (6-10 am) and heavily concentrated at 3 — not in-the-moment mood
categories. `model/evaluate_pmdata.py` applies the LifeSnaps 30-min model
to the 30 min before each report (1,504 reports, 16 participants) and
measures Spearman correlation:
- P(stressed) vs stress: pooled 0.00, within-person +0.05 (wrong
  direction), expected sign in 5/16 participants.
- P(happy) − P(sad) vs mood: pooled +0.11, within-person +0.03, expected
  sign in 11/16 (Wilcoxon p = 0.32) — the pooled effect is between-person,
  not mood.
- Reference: a Random Forest trained *on PMData itself*
  (leave-one-participant-out) also finds nothing (within-person ρ ≈ 0
  for both stress and mood).

Because PMData's own labels show no detectable link to pre-report HR/steps,
the failed transfer says more about PMData's label type than about the
LifeSnaps model. **Decision**: PMData is not used for training or as the
generalization check. Out-of-sample validation will come from MoodBand's
own trial (in-the-moment labels with the same SEMA-style protocol).

PMSys timestamps are UTC; Fitbit's are local. Converting reports to
Europe/Oslo was verified against Fitbit sleep logs: 4% of reports fall
inside logged main sleep vs. 35% if left in UTC.

---

## 11. Feedback-decision module built; default confidence threshold 0.45

**Decision** (Oct 18, 2026): the feedback-decision module is implemented in
`feedback/` as designed in `feedback-module-plan.md` (JITAI-style rule:
confidence gate → exercise filter → persistence → snooze / quiet hours /
daily cap / cooldown; no feedback for continuing happy/neutral; recovery cue
on negative → positive; three accessibility profiles enforced on the
catalog). Default `min_confidence` = **0.45** (margin 0.10, 2-of-3
persistence, 30-min cooldown, cap 4/day).

**Why 0.45** — `feedback/simulate.py` replays held-out predictions
(participant-grouped 5-fold CV) every 10 min from 08:00–22:00 on 1,295
LifeSnaps report days (~101k predictions):

| min_confidence | interventions / person-day | days with any | stressed precision (n) |
|---|---|---|---|
| 0.40 | 2.09 | 79% | 0.36 (290) |
| 0.45 | 1.18 | 57% | 0.32 (168) |
| 0.50 | 0.45 | 29% | 0.36 (59) |
| 0.55 | 0.11 | 9% | 0.31 (16) |

Chance precision for "stressed" is 0.26 (its share of reports). Precision
(an intervention within 30 min of a report of the same mood) stays ~0.31–0.37
at every threshold: **the classifier's confidence does not track
correctness**, so the threshold controls how often MoodBand speaks up, not
how often it is right. 0.45 gives about one intervention a day, under the
daily cap. "Sad" has too few matched cases (≤42) to judge; recall is low
(≤21% for stressed). With roughly two in three interventions not matching
the reported mood, suggestion framing and the "Was this right?" prompt are
essential, and those answers (personalized labels) are the main route to
improving precision.

---

## 12. Mobile app: React Native (Expo development build), tested on iPhone

**Decision** (Oct 19, 2026): the companion app uses **React Native with Expo**,
built as a *development build* (not Expo Go, which can't load custom native
modules). Haptics via **react-native-haptic-feedback** (`triggerPattern` with
continuous events of set duration and intensity; Core Haptics on iOS,
`VibrationEffect.createWaveform` amplitudes on Android). All device testing
is on the user's **iPhone**.

**Why**: accessibility is the core requirement and the user trial includes
blind and low-vision VoiceOver users. React Native renders native UIKit
controls, so VoiceOver behaves as in any iPhone app; Flutter draws its own
widgets behind a synthetic accessibility tree. A comparison of both
(Perinello & Gaggi, Univ. of Padua) found neither accessible by default but
React Native's accessible code more concise. Haptics are feasible in both
(Flutter: `haptic_kit`); React Native's library is more established. Close
call; Flutter's main advantage was a simpler toolchain.

**Risk to check in the prototype**: whether `triggerPattern` renders
*intensity* changes within continuous events on iPhone (the breathing
pacer's gentle-inhale / strong-exhale contrast). Fallback: a small Swift
Expo module calling Core Haptics directly.

---

## 13. Phone haptics only work in the hand: interventions start with a notification

**Finding** (Oct 19, 2026, iPhone 15 Pro Max test, `haptics-prototype-test.md`
A4): the breathing pacer is clear and calming **while the phone is held**,
barely noticeable on a table (quiet room, no case), and **not noticeable in a
pocket**. This confirms the caveat in lit review §5: the vibrotactile
evidence ([14], [15], [22]) used body-worn devices, and a phone's motor does
not carry the same patterns through a pocket. Separately, iOS stops an app's
custom Core Haptics when it is in the background, so the app could not play
a pattern unprompted anyway.

**Decision**: automatic interventions are delivered in two steps.
1. **Prompt**: a notification carrying the suggestion text ("Want a 1-minute
   breathing break?") with the system notification sound/vibration. VoiceOver
   reads notifications aloud, so this works for blind and low-vision users.
2. **Session**: the haptic pattern (and audio/visual cues) plays only once
   the user opens the notification, i.e. with the phone in hand.
Silent haptic-only nudges (e.g. the recovery cue's double tap) can't rely on
being felt; the recovery cue becomes a quiet notification or is shown the
next time the app is opened.

**Open**: whether the Fitbit itself could vibrate on the wrist (where the
evidence says haptics work best) through the Google Health API. Not
supported as far as known; check during the API prototype (Open items).

---

## 14. Supervisor meeting, Oct 21, 2026 — outcomes

- **Proposal must be updated** (reverses the Oct 18 plan to keep mk2 as a
  historical record): produce an updated proposal containing the final
  literature review (mk5) and current design, and share it with Prof.
  Zantout. **Done Oct 21**: `Capstone_Project_Proposal_MoodBand_mk3.pdf`
  (adds a stated limitation that the friends trial won't include visually
  impaired users, and the Apple Developer Program at $99/yr for TestFlight).
- **Benchmark a more complex model** on the same data to see whether
  accuracy improves over the Random Forest baseline (decisions.md #6 already
  named SVM and a small neural network as alternatives).
- **Ask before starting feedback**: the feedback module must get the user's
  explicit go-ahead before an intervention plays — not start automatically
  when a suggestion is opened (refines Decision #13).
- **Mid-term presentation next week** — needs a deck.
- **User trial confirmed**: data collection with friends as participants.
  Prof. Zantout is buying a Fitbit for the project and checking the user
  trial agreement (human-subjects / consent).
- **"Angry" is required** — supersedes the deferral in Decision #7. The
  final classifier must detect all five moods, so access to **EmoPhone**
  (wave D-3 has 0–6 *Angry* ratings) and **TILES-2018** is now necessary,
  not optional. (Check which TILES affect items, if any, capture anger.)
- **Confusion matrices** for every model compared, and for the same model
  across datasets (LifeSnaps vs. EmoPhone vs. TILES) once access arrives.

**Action items — student**: ~~share the updated proposal~~ (done); share the TILES-2018
data-use agreement; send Prof. Zantout a Fitbit link to buy; remind him to
check the user trial agreement.

---

## Open items / things to verify before trusting the above

- [ ] **Confirm the new Google Health API's actual behavior** — does it
  really provide 5-second HR resolution with no approval step? Is HRV still
  overnight-only, or has that changed? (Ties to Decision #2 and #3.)
- [ ] **Wrist alerts via Fitbit notification mirroring** (Decision #13) — when
  the Fitbit (Inspire 3 recommended, Oct 21) arrives: enable MoodBand under
  Fitbit app → device → Notifications → App Notifications, then check that a
  MoodBand suggestion buzzes on the wrist with the phone in a pocket, how
  reliably it arrives, and how strong the buzz feels. This would carry the
  *alert* to the wrist; the breathing session itself still plays on the
  phone (the band can't play custom patterns). Also confirm whether the
  Google Health API offers any direct way to vibrate the device (not known).
- [ ] Confirm OAuth/auth flow end-to-end for the Google Health API works
  from both an Android and an iOS client.
- [x] ~~**Ask Prof. Zantout**: is
  deferring "angry" (Decision #7) acceptable given Objective 3 lists five
  classes? If anger must be in scope, which source — PMData, MoodBand's own
  trial (with an anger-inducing stimulus added to the protocol), or merging
  it into "stressed"? Note: the raw SEMA3 data contains **2 "ANGER"**
  responses (plus 2 Surprise, 2 Sadness, 1 Fear, 1 Joy — apparently a
  different survey version), far too few to train on.~~ **Resolved Oct 21: anger is required** (Decision #14); EmoPhone and TILES access now necessary.
- [ ] **TILES-2018 data-use agreement** — Oct 21: student to share the DUA
  with Prof. Zantout for review and signature (was: ask at the meeting). Review
  and sign the **TILES-2018 data-use agreement** (account approved; download
  blocked until the DUA is signed). TILES-2018: Fitbit Charge 2, 212
  hospital workers, 10 weeks, semi-daily affect/anxiety/stress self-reports
  — backup/additional training data while EmoPhone access is pending (see
  `datasets.md`). Only the main data record is needed, not the audio record.
- [x] ~~Does the course require a revised proposal?~~ **Yes** — resolved Oct 21
  (Decision #14): update the proposal and share it with Prof. Zantout.
- [ ] **User trial agreement** (human-subjects / consent) — Prof. Zantout
  checking; student to remind him. Trial confirmed with friends as
  participants (Decision #14).
- [ ] **Fitbit for the project** — Prof. Zantout buying one; student to send
  a link.
- [ ] (Informational, not blocking) Prof. Zantout was checking with Dr. Yoon
  about a possibly related wearable project elsewhere on campus.
