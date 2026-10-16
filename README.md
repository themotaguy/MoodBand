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

## Project status

- [x] Problem statement, objectives, and scope defined
- [x] Literature review (10 papers) — [Docs/literature-review.md](Docs/literature-review.md)
- [x] Project proposal revised for the solo-student scope — [Docs/proposal-summary.md](Docs/proposal-summary.md)
- [x] Device and sensor selection finalized (Fitbit, HR + motion, overnight HRV)
- [x] Training datasets identified — [Docs/datasets.md](Docs/datasets.md)
- [x] LifeSnaps dataset acquired; exploratory analysis done
- [x] First Random Forest mood-classification baseline
- [ ] Improve the classifier (overnight HRV/sleep features, PMData cross-dataset check)
- [ ] Feedback-decision module
- [ ] Mobile companion app (accessible, screen-reader compatible)
- [ ] Offline end-to-end integration
- [ ] Google Health API integration (confirm 5-second HR, overnight-only HRV, OAuth on Android and iOS)
- [ ] User evaluation with sighted and visually impaired participants

## Results so far

Trained on **LifeSnaps** (Fitbit Sense, 71 participants), using hourly heart rate, steps, and time of day.

After mapping its self-reported moods (Happy, Neutral, Sad → same; Tense/Anxious → stressed), there are **2,040 labelled hours from 61 participants**: neutral 36%, happy 32%, stressed 26%, sad 6%.

| Model | Balanced accuracy | Macro-F1 |
|---|---|---|
| Chance (4 classes) | 0.25 | — |
| Majority-class baseline | 0.25 | 0.13 |
| Random Forest, generalized (tested on unseen participants) | 0.31 | 0.30 |
| Random Forest, personalized (33 participants with ≥20 labels) | ~0.39 | — |

An early baseline: better than chance, with personalized models ahead of the generalized one. "Sad" is rarely detected, as it has only 131 examples. Hourly-averaged heart rate is the likely main limitation.

## Repository structure

```
.
├── Docs/                     # Decisions log, literature review, proposal summary,
│                             # dataset notes, weekly reports (PDF)
├── model/
│   ├── lifesnaps.py          # Data loading, mood-label mapping, feature engineering
│   ├── explore_lifesnaps.py  # Exploratory data analysis
│   ├── train_baseline.py     # Random Forest training + evaluation
│   └── requirements.txt
├── data/                     # Datasets (gitignored — download separately)
├── CLAUDE.md                 # Project context for Claude Code
└── README.md
```

The `app/` (mobile companion app) and `sensing/` (Google Health API integration) directories will be added as those phases begin.

## Getting started (model)

1. Download LifeSnaps from Zenodo (DOI [`10.5281/zenodo.6826682`](https://doi.org/10.5281/zenodo.6826682)). Place `hourly_fitbit_sema_df_unprocessed.csv` and `daily_fitbit_sema_df_unprocessed.csv` in `data/lifesnaps/`.
2. Install dependencies and run:

```bash
pip install -r model/requirements.txt
python3 model/explore_lifesnaps.py   # dataset summary + label coverage
python3 model/train_baseline.py      # trains, evaluates, saves model/artifacts/rf_baseline.joblib
```

## Tech stack

- **Wearable integration:** Google Health API (REST/OAuth, cloud-based)
- **ML:** Python, pandas, scikit-learn (Random Forest); TensorFlow Lite considered for on-device inference
- **Mobile app:** Flutter or React Native (cross-platform, strong screen-reader support) — to be decided
- **Storage:** on-device buffer + Firebase sync for mood history
- **Optional backend:** Firebase Cloud Functions, if on-device inference proves too heavy

## Scope

**In scope:** Fitbit integration via the Google Health API; the mood-classification pipeline; the companion app delivering auditory, haptic, and visual feedback; a limited set of discrete mood categories; evaluation with a small user sample.

**Out of scope:** custom wearable hardware; long-term clinical validation; mass-manufacturing; health platforms beyond the Google Health API.

## Acknowledgments

Supervised by Prof. Rached Zantout as part of the capstone sequence at Khoury College of Computer Science, Northeastern University. Training data: LifeSnaps (Yfantidou et al., 2022).

## License

TBD
