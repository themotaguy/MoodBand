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
