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

## Open items / things to verify before trusting the above

- [ ] **Confirm the new Google Health API's actual behavior** — does it
  really provide 5-second HR resolution with no approval step? Is HRV still
  overnight-only, or has that changed? (Ties to Decision #2 and #3.)
- [ ] Confirm OAuth/auth flow end-to-end for the Google Health API works
  from both an Android and an iOS client.
- [ ] **Ask Prof. Zantout at the Wed Oct 21, 2026 weekly meeting**: is
  deferring "angry" (Decision #7) acceptable given Objective 3 lists five
  classes? If anger must be in scope, which source — PMData, MoodBand's own
  trial (with an anger-inducing stimulus added to the protocol), or merging
  it into "stressed"?
- [ ] (Informational, not blocking) Prof. Zantout was checking with Dr. Yoon
  about a possibly related wearable project elsewhere on campus.
