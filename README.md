# MoodBand

**An Inclusive Mobile System for Real-Time Mood Detection and Adaptive Sensory Feedback**

> Capstone Project — Khoury College of Computer Science, Northeastern University
> Supervisor: Prof. Rached Zantout
> Author: Ritik Pravin Mota

---

## Overview

MoodBand is a mobile-first system that detects a user's mood in real time using data from an existing consumer wearable (Fitbit or Apple Watch), and responds with adaptive auditory, haptic, and visual feedback designed to help improve that mood. The project is built with accessibility as a first-class requirement, with particular attention to visually impaired users, rather than as an afterthought.

Most existing mood-monitoring tools either stop at detection (logging or visualizing mood without acting on it) or rely on self-report rather than passive, continuous sensing. They also tend to assume a sighted user, delivering feedback almost exclusively through visual dashboards. MoodBand addresses both gaps: it closes the loop from detection to intervention, and it is designed from the outset to work for sighted and visually impaired users alike.

## Problem Statement

- Mood-monitoring solutions are largely self-report based and provide little to no closed-loop intervention.
- Most consumer well-being tools are visual-first, excluding visually impaired users who rely on screen readers and non-visual feedback.
- Few systems combine passive physiological sensing with accessible, multimodal feedback in a single pipeline.

## Approach

MoodBand is organized into four functional layers:

1. **Sensing Layer** — Pulls physiological and motion data (heart rate, HRV, activity) from a consumer wearable via its official API (Fitbit Web API / Apple HealthKit).
2. **Processing Layer** — Cleans and processes the incoming signal and classifies mood into discrete categories (e.g., happy, neutral, sad, stressed, angry) using a lightweight machine learning model suited to mobile/on-device deployment.
3. **Decision Layer** — Maps the detected mood and the user's accessibility profile to an appropriate feedback intervention.
4. **Feedback Layer** — Delivers the intervention through the mobile companion app via auditory, haptic (vibration), and/or visual channels, accessible via screen readers.

## Project Status

🚧 **In progress — early development phase.**

- [x] Problem statement, objectives, and scope defined
- [x] Literature review completed across four areas: affective computing fundamentals, wearable physiological sensing, mood classification models, and accessible feedback design
- [ ] Project proposal updated to reflect revised scope (solo-student pivot to existing wearable + mobile app)
- [ ] Wearable API integration (sensing layer)
- [ ] Mood classification model
- [ ] Feedback subsystem (audio / haptic / visual)
- [ ] Mobile companion app (accessible, screen-reader compatible)
- [ ] User evaluation with sighted and visually impaired participants

This README will be updated as implementation begins.

## Scope

**Within scope:** wearable API integration (Fitbit or Apple Watch), the mood-classification pipeline, and the companion mobile application delivering multimodal feedback; detection of a limited set of discrete mood categories; evaluation with a small user sample.

**Out of scope:** custom wearable hardware, long-term clinical validation, mass-manufacturing considerations, and integration with third-party health platforms beyond the chosen wearable's API.

## Tech Stack (planned)

- **Sensing:** Fitbit Web API / Apple HealthKit
- **ML/Classification:** Python (scikit-learn / lightweight on-device model, TBD)
- **Mobile App:** TBD (accessibility-first, screen-reader compatible)

## Repository Structure

```
.
├── docs/           # Proposal, literature review, weekly reports
├── sensing/        # Wearable API integration
├── model/          # Mood classification model + training
├── app/            # Mobile companion app
└── README.md
```

*(Structure will evolve as implementation begins.)*

## Acknowledgments

This project is supervised by Prof. Rached Zantout as part of the capstone sequence at Khoury College of Computer Science, Northeastern University.

## License

TBD