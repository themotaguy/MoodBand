# Candidate Training Datasets

Researched Oct 2026. None of these are stored in this repo (respect their
individual licenses) — download them separately and place under a
gitignored `data/` directory.

## Primary: LifeSnaps (Fitbit Sense)

This is the exact dataset behind literature-review paper [4]
(Velu et al.).

- **71 participants, 4+ months, 71M+ rows** of multi-modal data
- **Access**: fully open. Hosted on Zenodo, DOI `10.5281/zenodo.6826682`
  (also mirrored on Kaggle: search "LifeSnaps Fitbit dataset")
- **Signals**: heart rate, HRV, SpO2, skin temperature, Fitbit's computed
  stress score, sleep, steps/activity
- **Mood-relevant labels**: SEMA3 ecological momentary assessments (context +
  mood, collected multiple times/day) and scored surveys including **PANAS**
  (Positive and Negative Affect Schedule) and **STAI** (state-trait anxiety)
  — genuine validated mood ground truth, not just physiological signal
- **Format**: ready-to-use CSVs at daily and hourly granularity
  (`daily_fitbit_sema_df_unprocessed.csv`,
  `hourly_fitbit_sema_df_unprocessed.csv`), or a full MongoDB dump for
  finer-grained/raw data
- **MongoDB dump (in use since Oct 15, 2026)**: `fitbit.bson` (~9.7 GB;
  heart rate every few seconds with a confidence value, per-minute steps,
  plus calories, distance, SpO2 variation, exercise logs), `sema.bson` (each
  SEMA3 response with its exact completion timestamp, mood, and place), and
  `surveys.bson`. No MongoDB server needed —
  `model/extract_lifesnaps_mongo.py` streams it with pymongo's `bson`
  module into minute-level CSVs under `data/lifesnaps/` (see decisions.md #9)
- **Why this is the priority dataset**: same device family as MoodBand's
  chosen wearable, same paper already cited in the lit review, and real
  validated mood labels (PANAS/STAI) rather than just activity data

## Secondary: PMData (Fitbit Versa 2)

- 16 participants, 5 months, paired with the **PMSys** self-report app
  logging mood, stress, fatigue, and readiness directly
- Smaller sample than LifeSnaps, but a useful independent source to check
  the model generalizes across datasets rather than overfitting to
  LifeSnaps' specific population
- Referenced in: Thambawita et al. (2020)
- **Tried Oct 15, 2026 — inconclusive** (decisions.md #10): mood/stress
  are once-daily 1-5 wellness scores, mostly reported right after waking,
  so they don't match LifeSnaps' in-the-moment mood categories and show no
  detectable link to pre-report HR/steps. Loader: `model/pmdata.py`;
  check: `model/evaluate_pmdata.py`

## Additional candidates (researched Oct 15, 2026)

Searched for more datasets after the LifeSnaps baseline plateaued (~0.33
balanced accuracy) and PMData turned out unusable (decisions.md #10).
Ranked by fit: Fitbit-family device, in-the-moment labels, HR resolution.

1. **EmoPhone** (KAIST; arXiv 2609.16581, Sep 2026 preprint) — **best fit.**
   Fitbit Inspire HR (1 Hz heart rate, steps), three waves 2020-2022,
   92 / 99 / 106 students, ~4 weeks each, 10-15 experience-sampling prompts
   per day (roughly 50k labels in all). Every wave has valence, arousal, and
   stress; wave D-3 adds 0-6 ratings of Happy, Relaxed, Cheerful, Content,
   Sad, Anxious, Depressed, and **Angry** — the only candidate with an anger
   label. Authors' own cross-user baselines are modest (valence AUROC ~0.57-0.59),
   consistent with our LifeSnaps results. **Access: hosted on Harvard
   Dataverse; access requested Oct 15, 2026 — pending.**
2. **TILES-2018** (Scientific Data 2020, doi 10.1038/s41597-020-00655-3) —
   Fitbit Charge 2 (sub-minute HR, steps, sleep), 212 hospital workers,
   10 weeks, EMAs twice daily including PANAS-Short affect and a momentary
   anxiety item. Signed data-use agreement required (tiles-data.isi.edu).
   **Status (Oct 15, 2026): account approved; DUA to be reviewed/signed with
   Prof. Zantout on Oct 21.** Use TILES-2018 (main data record only), not
   TILES-2019 (57 residents, 3 weeks, affect/anxiety measured only once).
   Labels are coarser than SEMA3 (twice daily, positive/negative affect).
3. **K-EmoPhone** (Scientific Data 2023, doi 10.1038/s41597-023-02248-2) —
   77 students, 7 days, 5,582 in-situ valence/arousal/stress/attention
   labels. Not Fitbit (Microsoft Band 2). Zenodo record 7606611, restricted:
   access-request form + user agreement.
4. **GLOBEM** (PhysioNet, credentialed access) — Fitbit, 497 participants,
   2018-2021, but labels are weekly surveys (PHQ-4, PANAS) — too coarse for
   moment-level mood.
5. **QoL_Stress** (Zenodo 10.5281/zenodo.23210360, CC BY 4.0, open) —
   Fitbit Charge 6, 66 adults, per-second HR, but a ~30-minute **lab**
   stressor protocol with STAI-S before/after. Could serve only as a
   stressed-vs-relaxed sanity check, not mood training data.

## Lower priority / situational

- **Apple Watch + Fitbit dataset (Kaggle, `aleespinosa/apple-watch-and-fitbit-data`)**
  — 46 participants wearing both devices for 65 minutes. No mood labels;
  useful only if cross-checking how Fitbit vs. Apple Watch heart-rate
  readings compare on the same person.
- **AW-FB dataset (Harvard)** — Apple Watch Series 2 + Fitbit Charge HR2 +
  GENEActiv, 46 participants. Labels are physical-activity intensity
  (lying/sitting/walking/METs), not mood. Same caveat as above.
- **WESAD (Wearable Stress and Affect Detection)** — the field's standard
  benchmark for stress/affect detection (neutral/stress/amusement labels,
  15 subjects), but uses lab-grade Empatica E4 sensors (EDA, chest ECG), not
  Fitbit/Apple Watch. Not device-matched to this project, but worth knowing
  as a point of comparison if a reviewer asks "how does this compare to the
  standard benchmark."
- **Fitbit Fitness Tracker Data (Kaggle, `arashnic/fitbit`)** — 30 users,
  activity/sleep data only, no mood labels. Not directly useful for mood
  classification.

## Practical note

Dataset files are not downloadable directly from within a sandboxed dev
environment without outbound network access. Download LifeSnaps (and/or
PMData) locally first, then bring the CSVs into this repo's `data/`
directory (gitignored) to start exploratory analysis and model training.

## Suggested next step

Start exploratory data analysis on LifeSnaps'
`hourly_fitbit_sema_df_unprocessed.csv` — check feature availability (HR,
steps, stress score), check SEMA3 mood-label coverage/frequency, and decide
the initial feature set before training the first Random Forest baseline
(see `decisions.md` §6).
