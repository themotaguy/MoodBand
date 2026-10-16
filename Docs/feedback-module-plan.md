# Feedback-Decision Module — Plan (draft, not yet started)

Drafted Oct 15, 2026. Evidence: `literature-review.md` §4b. Once the open
questions below are answered and the module is built, record the design as
a numbered decision in `decisions.md` and trim this file.

## Job

Turn a mood prediction into **either no action or one concrete
intervention** for this user. Inputs: the model's class probabilities, the
user's accessibility profile, and recent history (predictions and
interventions). Output: a fully specified intervention (haptic pattern,
audio cue, visual cue, screen-reader text), or "do nothing" with a reason.
Framed as a JITAI decision rule (Nahum-Shani et al.).

## Decision steps

1. **Confidence gate** — act only if the top class's probability is high
   enough and clearly ahead of the runner-up. Threshold chosen from
   simulation, not guessed (model is ~0.33 balanced accuracy).
2. **Persistence** — same mood in e.g. 2 of the last 3 predictions.
3. **Exercise filter** — suppress "stressed" when recent steps show
   activity (avoids the "I just went for a run" mismatch; Koh et al. 2026).
4. **Rate limits** — cooldown (default 30 min), daily cap, quiet hours,
   user snooze.
5. **Mood → intervention** (proposal's table, revised by §4b):
   - stressed → breathing pacer (~6 breaths/min, strong-exhale haptic
     pattern per PIV++; slow-heartbeat tap alternative per EmotionCheck)
   - sad → iso-principle audio (calm first, then gradually brighter)
   - angry → calming timer (in catalog; model can't predict anger yet —
     decisions.md #7)
   - happy / neutral → **no feedback** while the state continues (avoids
     feedback fatigue)
   - **recovery** (stressed / sad / angry → happy / neutral) → brief
     positive-reinforcement cue — the only "positive" feedback
6. **Channels by accessibility profile** — three profiles (hard rules):
   - **blind / visually impaired**: always audio **and** haptic, never one
     alone ([10])
   - **low vision**: audio + haptic as above, plus optional high-contrast
     visual cues
   - **sighted**: visual + haptic by default
   - every visual cue has a non-visual equivalent and screen-reader text
   - audio unavailable (silent mode): visually impaired users still get
     haptic plus a deferred audio cue — never visual-only

Every intervention is phrased as a **suggestion** ("Want a 1-minute
breathing break?"), not a diagnosis, and offers **"Was this right?"**
(yes / no / snooze). Answers are logged as in-the-moment labels for
personalized models (paper [7]) and the user trial. An on-demand "I need a
break" option complements automatic triggers.

## Files

```
feedback/
├── interventions.json   # catalog: haptic timings/amplitudes, audio cue/script,
│                        # colour/animation, screen-reader text — portable to any runtime
├── decision.py          # the steps above, pure Python
├── simulate.py          # replays LifeSnaps CV predictions through the module
└── tests/test_decision.py
```

JSON catalog so the same table works in a Python backend or the phone app
(Flutter or React Native, whichever is chosen) — see `decisions.md` §4.

## Testing and evaluation

- Unit tests for the accessibility guarantees: visually impaired profile
  always gets audio + haptic; no visual-only output; cooldown respected;
  low confidence → no action; happy/neutral never interrupts.
- Simulation: for each confidence threshold, interventions per person per
  day and how often a fired intervention matched the reported mood. Picks
  the default threshold and gives a reportable evaluation number.
- Risk: probabilities are flat; a strict threshold may rarely fire and a
  loose one is often wrong. That is a finding to report, not hide.

## Resolved questions (Oct 15, 2026)

1. **Happy/neutral feedback?** No feedback for a continuing happy/neutral
   state (feedback fatigue). Positive reinforcement only on a transition
   from a negative mood (stressed/sad/angry) to a positive one
   (happy/neutral). Note: §4b found no direct evidence for recovery-based
   reinforcement — it is a design choice motivated by alert-fatigue findings
   (Koh et al. 2026), to be evaluated in the user trial.
2. **Profiles: two or three?** Three: sighted, low vision, blind/visually
   impaired.

Next: user is updating the formal literature review (on claude.ai) to cover
these feedback decisions before the module is built.
