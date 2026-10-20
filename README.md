# MoodBand

**An Inclusive Mobile System for Real-Time Mood Detection and Adaptive Sensory Feedback**

> Capstone Project — Khoury College of Computer Science, Northeastern University
> Supervisor: Prof. Rached Zantout
> Author: Ritik Pravin Mota

---

## Overview

MoodBand detects a user's mood in real time from a **Fitbit** wearable (via the **Google Health API**) and responds with adaptive **auditory, haptic, or visual** feedback through a companion mobile app on **both Android and iOS**. Feedback is chosen according to whether the user is sighted or visually impaired: accessibility is a core requirement, not an add-on.

Most mood-monitoring tools either stop at detection (logging or visualizing mood without acting on it) or rely on self-report rather than passive sensing. They also tend to assume a sighted user. MoodBand closes the loop from detection to intervention, and is designed from the outset for sighted and visually impaired users alike.

Target mood categories: **happy, neutral, sad, stressed, angry** ("angry" is currently deferred — see [Key decisions](#key-decisions)).

## Architecture

A four-stage logical pipeline: **sense → process → classify → feedback**.

```
Fitbit wearable ──> Google Health API (cloud, cross-platform)
                          │
                          v
        Mood Detection Engine (processing + classification)
        [phone, laptop, or lightweight cloud backend]
                          │
                          v
        Feedback Decision Module (mood + accessibility profile → intervention)
        [phone, laptop, or lightweight cloud backend]
                          │
                          v
        Feedback / Actuation Layer  [always on the phone]
        ├─ Auditory (speaker)
        ├─ Haptic (vibration)
        └─ Visual (colour cues, screen-reader-accessible UI)
```

Full on-device execution is the target end-state, not a hard requirement. Only feedback actuation is pinned to the phone.

### Feedback mapping (illustrative)

| Mood detected | Sighted users | Visually impaired users |
|---|---|---|
| Stress / anxiety | Cool-toned colour pulse + on-screen breathing animation | Slow-paced vibration synced with spoken breathing cues |
| Sadness | Warm colour cue + suggested uplifting playlist | Gentle spoken affirmation + calming audio track |
| Anger / frustration | Red-to-green fading colour cue as a calming timer | Descending vibration intensity + guided calming voice prompt |
| Neutral / happy | Soft green confirmation banner, no interruption | Brief pleasant chime, no interruption |

Every visual cue has an audio or haptic equivalent, because the literature review showed screen readers don't reliably work in practice.

## Key decisions

Full reasoning for each is in [Docs/decisions.md](Docs/decisions.md).

| # | Decision | Why |
|---|---|---|
| 1 | Use an existing consumer wearable, not custom hardware | Single student, 16-week timeline |
| 2 | **Fitbit via the Google Health API** | Only candidate whose data isn't tied to one phone OS. Apple Watch is iPhone-only; Samsung's continuous streaming is Android-only; WHOOP exposes no continuous HR. The legacy Fitbit Web API was retired in Oct 2026. |
| 3 | Heart rate + motion as real-time features; HRV overnight-only | Fitbit computes HRV only during sleep; EDA and skin temperature aren't exposed by the consumer API |
| 4 | Flexible deployment (phone / laptop / cloud) | Supervisor feedback: the requirement is a working near-real-time loop, not everything on the phone |
| 5 | Offline-first build order | Validate model, feedback, and app on public datasets before live Fitbit integration |
| 6 | Random Forest as primary classifier | Best classical model on wearable features in the reviewed literature; lightweight. Personalized models evaluated alongside a generalized one. |
| 7 | **"Angry" deferred; classifier is 4-class for now** | The primary dataset (LifeSnaps) has no anger label. To be discussed with the supervisor. |
| 8 | Overnight HRV/sleep kept out of the generalized model; optional for personalized | Lowered accuracy on unseen participants; small, not-yet-significant gain per person |
| 9 | Classify from the **30 minutes of heart rate + steps before each mood report** | Matches how the app will run on live data; slightly better than hourly averages |
| 10 | PMData not used; cross-dataset check inconclusive | Its daily, mostly post-wake 1–5 scores show no link to heart rate/steps even for a PMData-trained model; validation will come from MoodBand's own trial |
| 11 | Feedback module acts on ~1 suggestion a day (confidence ≥ 0.45, persistence, cooldown, cap, exercise filter); three accessibility profiles | Simulation: stricter thresholds cut interruptions but not errors — "stressed" interventions match the reported mood ~1 in 3 times (chance 1 in 4) |

## Project status

- [x] Problem statement, objectives, and scope defined
- [x] Literature review (10 papers) — [Docs/literature-review.md](Docs/literature-review.md)
- [x] Project proposal revised for the solo-student scope — [Docs/proposal-summary.md](Docs/proposal-summary.md)
- [x] Device and sensor selection finalized (Fitbit, HR + motion, overnight HRV)
- [x] Training datasets identified — [Docs/datasets.md](Docs/datasets.md)
- [x] LifeSnaps dataset acquired; exploratory analysis done
- [x] First Random Forest mood-classification baseline
- [x] Overnight HRV/sleep features evaluated (Decision #8)
- [x] Minute-level heart rate from the LifeSnaps MongoDB dump (Decision #9)
- [x] PMData cross-dataset check — inconclusive (Decision #10)
- [x] Literature review extended with intervention and feedback-timing research (final: mk5)
- [x] Feedback-decision module, tuned by simulation (Decision #11)
- [ ] Mobile companion app (accessible, screen-reader compatible)
- [ ] Offline end-to-end integration
- [ ] Google Health API integration (confirm 5-second HR, overnight-only HRV, OAuth on Android and iOS)
- [ ] User evaluation with sighted and visually impaired participants

## Results so far

Trained on **LifeSnaps** (Fitbit Sense, 71 participants). Self-reported moods are mapped Happy, Neutral, Sad → same; Tense/Anxious → stressed. Each mood report gets heart-rate and step features from the **30 minutes before it** (minute-level data from the LifeSnaps MongoDB dump).

There are **1,961 usable reports from 61 participants**: neutral 36%, happy 32%, stressed 26%, sad 7%.

Balanced accuracy, averaged over 5 repeated participant-grouped splits (chance = 0.25):

| Model | Generalized (unseen participants) | Personalized (33 participants) |
|---|---|---|
| Majority-class baseline | 0.25 | — |
| Random Forest, hourly CSV averages | 0.32 | ~0.37–0.39 |
| Random Forest, hourly + last night's HRV/sleep | 0.27–0.30 | ~0.42 |
| **Random Forest, 30 min before report** | **0.33** | ~0.38–0.39 |

An early baseline: consistently better than chance, but heart rate and steps carry limited mood signal across people. Personalized models do better, but with few test labels per person their numbers vary by several points between runs. "Sad" remains hardest (F1 ≈ 0.13). See Decisions #8–#9 for detail.

**Cross-dataset check (PMData):** applying the model to PMData shows no meaningful relationship with its daily mood and stress scores. A model trained on PMData itself doesn't find one either, so PMData's once-a-day, mostly post-wake ratings can't settle whether the model generalizes (Decision #10).

## Repository structure

```
.
├── Docs/                     # Decisions log, literature review, proposal summary,
│                             # dataset notes, weekly reports (PDF)
├── model/
│   ├── lifesnaps.py          # Hourly/daily CSV loading, mood-label mapping, features
│   ├── extract_lifesnaps_mongo.py  # One-off: MongoDB dump → minute-level HR/steps
│   ├── windows.py            # Features from the 30 min before each mood report
│   ├── pmdata.py             # PMData loader + minute-level extraction
│   ├── evaluate_pmdata.py    # Cross-dataset check against PMData
│   ├── explore_lifesnaps.py  # Exploratory data analysis
│   ├── train_baseline.py     # Random Forest training + evaluation
│   └── requirements.txt
├── feedback/
│   ├── interventions.json    # Feedback catalog: haptic patterns, audio, visuals, per profile
│   ├── decision.py           # Decision rule: mood prediction + profile → intervention or nothing
│   ├── simulate.py           # Replays held-out predictions to tune the confidence threshold
│   └── tests/                # Guardrail and accessibility tests
├── app/                      # React Native (Expo) companion app — haptics prototype so far
├── data/                     # Datasets (gitignored — download separately)
├── CLAUDE.md                 # Project context for Claude Code
└── README.md
```

The `sensing/` directory (Google Health API integration) will be added when that phase begins.

## Getting started (model)

1. Download LifeSnaps from Zenodo (DOI [`10.5281/zenodo.6826682`](https://doi.org/10.5281/zenodo.6826682)). Place `hourly_fitbit_sema_df_unprocessed.csv` and `daily_fitbit_sema_df_unprocessed.csv` in `data/lifesnaps/`. Keep the `mongo_rais_anonymized/` dump folder (~9.7 GB) anywhere; `data/lifesnaps/mongo/` is the default location.
2. Set up the environment and run:

```bash
python3 -m venv .venv
.venv/bin/pip install -r model/requirements.txt
.venv/bin/python model/extract_lifesnaps_mongo.py path/to/mongo_rais_anonymized  # one-off, ~3 min
.venv/bin/python model/explore_lifesnaps.py   # dataset summary + label coverage
.venv/bin/python model/train_baseline.py      # trains, evaluates, saves model/artifacts/rf_baseline.joblib
.venv/bin/python model/pmdata.py              # optional: PMData (data/pmdata/) → minute files, ~25 s
.venv/bin/python model/evaluate_pmdata.py     # optional: cross-dataset check
.venv/bin/python -m unittest discover -s feedback/tests -t .   # feedback module tests
.venv/bin/python feedback/simulate.py         # feedback simulation (~5 min first run, then cached)
```

## Tech stack

- **Wearable integration:** Google Health API (REST/OAuth, cloud-based)
- **ML:** Python, pandas, scikit-learn (Random Forest); TensorFlow Lite considered for on-device inference
- **Mobile app:** React Native with Expo (development build); haptics via react-native-haptic-feedback (Core Haptics on iOS)
- **Storage:** on-device buffer + Firebase sync for mood history
- **Optional backend:** Firebase Cloud Functions, if on-device inference proves too heavy

## Scope

**In scope:** Fitbit integration via the Google Health API; the mood-classification pipeline; the companion app delivering auditory, haptic, and visual feedback; a limited set of discrete mood categories; evaluation with a small user sample.

**Out of scope:** custom wearable hardware; long-term clinical validation; mass-manufacturing; health platforms beyond the Google Health API.

## Acknowledgments

Supervised by Prof. Rached Zantout as part of the capstone sequence at Khoury College of Computer Science, Northeastern University. Training data: LifeSnaps (Yfantidou et al., 2022).

## License

TBD
