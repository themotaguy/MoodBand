# Haptics Prototype — iPhone Test Checklist

App: `app/` (React Native / Expo development build, decisions.md #12). It
plays every vibration pattern in `feedback/interventions.json` on the phone.
Fill in the results after testing, then record anything that changes the
design in `decisions.md`.

**Device**: iPhone 15 Pro Max · iOS 27.0.1 · Date Oct 19, 2026

## A. Haptics (sighted use)

| # | Check | Result / notes |
|---|---|---|
| A1 | Status line says custom haptics are supported | ✅ |
| A2 | **Intensity check**: weak and strong halves clearly feel different | Round 1 (weak 50/255, strong 255): contrast good, but weak too faint to notice. Raised floor to 100 and strong phases to 255 across the catalog. Round 2 (weak 100): intensity good. ✅ |
| A3 | **Breathing pacer**: gentle 4 s / strong 6 s phases are easy to follow; breathing along for the full minute feels calming, not annoying | ✅ Works and is calming. |
| A4 | Breathing pacer works with the phone **in the hand**, **on a table**, and **in a pocket** | ❌ **Only in the hand.** Table: barely, only in a quiet room with no case. Pocket: not noticeable. → decisions.md #13 |
| A5 | **Slow heartbeat**: feels like a heartbeat (double tap), not a buzz | ❌ → ✅ Felt like a buzz; changed to two crisp transient taps per beat (sharpness 0.8). Retest: works. |
| A6 | **Descending pulses**: the fade from strong to faint is noticeable | ✅ |
| A7 | **Soft tap** and **double tap** are noticeable but not startling | ✅ |
| A8 | **Stop** ends a pattern immediately | ✅ Patterns run their full length unless stopped. Starting a pattern now stops any one already playing. |
| A9 | Patterns still play with the **Ring/Silent switch on silent** | ✅ |
| A10 | Any pattern that is uncomfortable, too weak, or confusing? | |

## B. VoiceOver (Settings → Accessibility → VoiceOver)

| # | Check | Result / notes |
|---|---|---|
| B1 | Swiping right reads every heading and button in a sensible order | ✅ |
| B2 | Each button reads its name, length, and (after a pause) its description | ✅ |
| B3 | Double-tapping a button plays the pattern and announces "Playing …" | Plays. VoiceOver re-reads the button on activation; a queued announcement then repeated the name ("…5 seconds, Playing weak then strong…"). Announcement shortened to "Playing". Retest pending. |
| B4 | The announcement and the vibration don't clash or cut each other off | ✅ |
| B5 | The rotor's Headings option jumps between the two sections | ✅ |
| B6 | Text stays readable at a larger text size (Settings → Display & Brightness → Text Size) | ✅ |

## Outcome

- Breathing pacer usable from the phone's vibration motor? **Partly — only while the phone is held** (decisions.md #13).
- Changes needed to `interventions.json` (amplitudes, durations, sharpness):
- Anything that needs the Swift Core Haptics fallback (decisions.md #12)?
