# MoodBand

An inclusive mood-detection and adaptive-feedback mobile system. Final year /
capstone project, Khoury College of Computer Science, Northeastern University.

- **Student**: Ritik Pravin Mota (NUID: 003158858)
- **Supervisor**: Prof. Rached Zantout

This file is the entry point for Claude Code on this repo. Supporting detail
lives in `docs/` — read the relevant doc before making non-trivial changes;
don't re-derive decisions already made below.

## What MoodBand does

MoodBand senses a user's physiological and motion signals from an existing
consumer wearable, classifies their mood in real time into one of five
categories (**happy, neutral, sad, stressed, angry**), and responds with a
personalized feedback intervention (**auditory, haptic, or visual**) delivered
through the user's phone, chosen according to whether the user is sighted or
visually impaired. The goal is to close the loop between mood *sensing* and
mood *regulation* — most existing tools do one or the other, not both — while
treating accessibility as a first-class requirement rather than an add-on.

## Current status (as of Oct 2026)

Done:
- Literature review (10 papers) completed, with explicit reasoning for which
  paper influenced which design decision — see `docs/literature-review.md`.
- Device selection finalized: **Fitbit**, integrated via the **Google Health
  API** — see `docs/decisions.md` for why (short version: it's the only
  candidate device whose data isn't tied to a single phone OS, and the app
  must support both Android and iOS).
- Sensor selection finalized: heart rate + motion (continuous), HRV
  (overnight-only supplementary signal) — see `docs/literature-review.md`.
- Full project proposal written (architecture, methodology, timeline,
  budget) — see `docs/proposal-summary.md`.
- **Mood model baseline built (Oct 15, 2026)** — `model/`. Random Forest on
  heart rate + steps from the 30 min before each LifeSnaps mood report
  (minute-level data from the LifeSnaps MongoDB dump): balanced accuracy
  ~0.33 vs 0.25 chance, 4 classes ("angry" deferred — no label in
  LifeSnaps). Overnight HRV/sleep and PMData were tried and didn't help.
  See `docs/decisions.md` #7-#10 and the README's results section. Run with
  the project venv: `.venv/bin/python model/train_baseline.py`.

Not yet done / in progress:
1. **Feedback-decision module — built (Oct 18).** `feedback/`: catalog,
   decision rule, simulation, 23 tests (`python -m unittest discover -s
   feedback/tests -t .`). Default threshold 0.45 from simulation; key finding:
   model confidence doesn't track correctness (`docs/decisions.md` #11).
   **Next build step: the mobile companion app** — React Native / Expo
   development build in `app/` (decisions.md #12); testing is on the user's
   iPhone. First milestone: haptics prototype (`app/App.tsx`), test plan in
   `docs/haptics-prototype-test.md`. Follow `app/AGENTS.md` for Expo work.
2. **More training data (pending access).** EmoPhone (Fitbit, ~300
   participants, includes anger) requested on Harvard Dataverse; TILES-2018
   account approved but its data-use agreement needs Prof. Zantout's
   signature. See `docs/datasets.md`. Questions for the weekly Wednesday
   supervisor meeting are tracked under "Open items" in `docs/decisions.md`.
3. **Prototype against the Google Health API** to confirm it actually
   supports what the proposal assumes, and flag any missing pieces (e.g.,
   confirm real-time HR resolution, confirm HRV truly is overnight-only
   under the *new* API, confirm OAuth/auth flow works end-to-end). Per the
   build order, this comes after the offline pipeline (model, feedback
   module, app) works.
4. Prof. Zantout was separately checking with Dr. Yoon about a possibly
   related wearable project elsewhere on campus — informational, no action
   needed from the code side.

## Architecture (see `docs/decisions.md` for full reasoning)

Four-stage pipeline: **sense → process → classify → feedback**.

```
Fitbit Wearable ──┐
                   ├──> Google Health API (cloud, cross-platform)
                   │
                   v
      Mood Detection Engine (processing + classification)
      [may run on: mobile device / laptop / cloud backend]
                   │
                   v
      Feedback Decision Module (mood + accessibility profile → intervention)
      [may run on: mobile device / laptop / cloud backend]
                   │
                   v
      Feedback / Actuation Layer  [MUST run on the phone — it drives the
      phone's speaker, vibration motor, and screen]
      ├─ Auditory (speaker)
      ├─ Haptic (vibration)
      └─ Visual (in-app colour cues, screen-reader-accessible UI)
```

**Important**: full on-device mobile execution is the *target end-state*, not
a hard requirement. Processing and feedback-decision logic may run on a
connected laptop or a lightweight cloud backend (e.g., a Firebase Cloud
Function) if on-device performance constraints make that necessary. Only the
final feedback-actuation step is pinned to the phone, since that's the
hardware the user directly experiences. Don't assume everything must be
refactored to run on-device — check `docs/decisions.md` before "fixing" this.

## Key constraints to keep in mind

- **Cross-platform is a hard requirement.** The app must work on both
  Android and iOS. This is *why* Fitbit was chosen over Apple Watch
  (iPhone-only) and Samsung (Android-only for continuous streaming) despite
  those having some technical advantages. Don't suggest switching to a
  platform-native health framework (HealthKit, Samsung Health Sensor SDK) as
  the primary sensing path — it would break cross-platform support.
- **HRV is overnight-only.** Fitbit (via the Google Health API) does not
  expose live daytime HRV. The classifier should treat HR + motion as the
  real-time, waking-state features, and HRV as a supplementary nightly
  feature only. This needs re-confirming against the *new* Google Health API
  specifically (task 2 above) — the lit review's HRV finding was from the
  legacy Fitbit Web API, which was deprecated in Oct 2026.
- **Single student, 16-week timeline.** Build order is deliberately: model +
  feedback module + mobile app, validated end-to-end on offline/public
  datasets first → only then integrate the live Fitbit/Google Health API.
  Don't front-load live API integration work ahead of the offline pipeline
  being solid.
- **Accessibility is a core requirement, not a stretch goal.** Every visual
  feedback cue needs a corresponding audio or haptic equivalent — see the
  three accessibility profiles in `docs/feedback-module-plan.md` (the
  proposal's original mapping table is superseded). This was
  directly informed by user research in the lit review showing screen
  readers don't reliably work in practice (paper [10]).

## Planned tech stack

- **Wearable integration**: Google Health API (REST/OAuth, cloud-based — not
  the legacy Fitbit Web API, which Google retired Oct 2026)
- **ML**: Python, scikit-learn (Random Forest is the literature-backed
  starting point — see `docs/literature-review.md`, paper [6]) / TensorFlow
  Lite for lightweight inference
- **Mobile app**: React Native with Expo (development build, not Expo Go);
  haptics via react-native-haptic-feedback (Core Haptics on iOS) — see
  `docs/decisions.md` #12
- **Data storage**: Local on-device buffer + Firebase sync for mood history
- **Optional backend**: Firebase Cloud Functions, if on-device inference
  proves too heavy

## Docs in this repo

- `Docs/RitikMota_Capstone_LiteratureReview_mk5.pdf` — the final, authoritative
  literature review (earlier mk2–mk4 are superseded drafts).
- `Docs/Capstone_Project_Proposal_MoodBand_mk2.pdf` — the original proposal,
  kept as a **historical** record of the starting goal; deliberately not
  updated as the project evolves. Where it disagrees with `docs/decisions.md`
  or `docs/feedback-module-plan.md`, those win.
- `docs/literature-review.md` — the 10 reviewed papers, organized by theme,
  each with an explicit "why this shaped MoodBand" note; plus the sensor
  recommendation table and a condensed device comparison.
- `docs/decisions.md` — ADR-style log of the big decisions (device, sensors,
  architecture flexibility, build ordering) and the reasoning behind each.
- `docs/proposal-summary.md` — condensed version of the original proposal
  (historical), with a list of where the project has since diverged.
- `docs/feedback-module-plan.md` — final plan for the feedback-decision
  module (next build step): decision steps, three accessibility profiles,
  feedback catalog, evaluation.
- `docs/datasets.md` — candidate training datasets (LifeSnaps, PMData, and
  others considered), what each contains, and how to get them.

## Working conventions

- This is a solo-student academic project on a fixed timeline — prefer
  simple, explainable approaches (e.g., Random Forest before anything
  fancier) over state-of-the-art complexity, consistent with the literature
  review's own reasoning.
- When a design question comes up that was already settled in `docs/`,
  follow what's documented rather than re-litigating it in code review —
  but if new information (e.g., something found while testing the Google
  Health API) contradicts a documented assumption, flag it explicitly and
  update `docs/decisions.md` rather than silently diverging from it.
