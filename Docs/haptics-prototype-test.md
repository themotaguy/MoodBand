# Haptics Prototype — iPhone Test Checklist

App: `app/` (React Native / Expo development build, decisions.md #12). It
plays every vibration pattern in `feedback/interventions.json` on the phone.
Fill in the results after testing, then record anything that changes the
design in `decisions.md`.

**Device**: iPhone 15 Pro Max · iOS 27.0.1 · Date Oct 19, 2026

## Status (Oct 21, 2026): all checks pass

All haptics (A), VoiceOver (B), notification-flow (C), retest (R) and
ask-before-start (D) checks pass on the iPhone 15 Pro Max. Remaining open
item: wrist alerts via Fitbit notification mirroring, once the Fitbit
arrives (decisions.md open items).

## Test session notes

**Before you start**
1. Start the dev server on the Mac: in Terminal, `cd app && npx expo start`
   (or ask Claude Code to start it). Keep it running while testing.
2. iPhone and Mac on the **same Wi-Fi**. Open MoodBand; if it shows an error or
   an old screen, tap **Reload JS**.
3. Free signing: this build stops opening after **Oct 26, 2026** — ask for a
   rebuild if it won't launch.

**1. Retests after the vibration fix** (restart delay + resume only after an
interruption) — these come first, since vibration stopped working entirely
after the previous change:

| # | Check | Result / notes |
|---|---|---|
| R1 | **From a notification**: Stress suggestion → lock phone → tap notification. Vibration starts with the break | ✅ (Oct 21, standalone Release build) |
| R2 | **I need a break** on the home screen: vibration starts straight away | ✅ (Oct 21, standalone Release build) |
| R3 | **Interruption**: during a break, open Notification Center for a few seconds, close it. Vibration resumes in step with the circle | ✅ (Oct 21, standalone Release build) |
| R4 | **Haptics test** screen (home → Developer → Haptics test): patterns still play | ✅ (Oct 21, standalone Release build) |

**2. New build (Oct 21): ask-before-start + VoiceOver speech fix**

| # | Check | Result / notes |
|---|---|---|
| D1 | Open a **stress suggestion** from its notification: screen asks first, with **Start** / **Not now**; nothing plays until Start | ✅ (Oct 21, standalone Release build) |
| D2 | **VoiceOver on**: after Start, VoiceOver reads the screen, *then* the spoken guidance — no overlap | ✅ (Oct 21, standalone Release build) |
| D3 | **Not now** closes the break and shows "not now" under *Your answers* | ✅ (Oct 21, standalone Release build) |
| D4 | **Recovery cue (quiet)**: arrives with **no sound**; opening it shows "Looks like things eased up. Nice." straight away (no Start step) with a double tap | ✅ (Oct 21, standalone Release build) |
| D5 | **I need a break** still starts immediately (no Start step) | ✅ (Oct 21, standalone Release build) |

R1–R4 above still need results if not yet reported. (Section C below:
C1–C14 done Oct 21 except C11 → D4.)

Short notes per check are enough, e.g. "R1 ok, R3 no vibration, C9 silent".

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

## C. Notification → session flow (decisions.md #13)

Home screen → **Test a suggestion**. Each test sends its notification in 5 s.

| # | Check | Result / notes |
|---|---|---|
| C1 | First test asks for notification permission; after allowing, the notification arrives | ✅ |
| C2 | **Locked phone**: the stress suggestion appears on the lock screen with sound/buzz; text reads "Want a 1-minute breathing break?" | ✅ |
| C3 | Tapping it (after Face ID) opens the **breathing break** directly | ✅ Found: opening Notification Center mid-break stopped the vibration (iOS stops custom haptics when the app is inactive) while the circle continued. Fixed: haptics resume from the elapsed point when the app is active again. Retest. Dev-only "Refreshing…" bar = dev server reconnecting; absent in release builds. |
| C4 | **App in background** (home screen): tapping the banner opens the break | ✅ Opens the break. **Found**: with VoiceOver on, VoiceOver reading the screen and the app's own speech overlapped on every session. Fixed: spoken guidance goes through VoiceOver (queued) when it is running; app speech only without VoiceOver. ✅ via D2. |
| C5 | **App open**: the banner still shows at the top; tapping it opens the break | ✅ |
| C6 | Sighted: breathing circle grows on "Breathe in" (4 s) and shrinks on "Breathe out" (6 s), in time with the vibration | ✅ |
| C7 | Low vision: high-contrast circle + spoken guidance + vibration | ✅ |
| C8 | Blind: no visuals needed; spoken guidance + vibration | ✅ |
| C9 | Spoken guidance plays **with the silent switch on** | ✅ |
| C10 | After the break (or Stop): "Was this right?" with Yes / No / Snooze; the answer appears under **Your answers** | ✅ |
| C11 | Recovery cue arrives **without** a sound | ✅ via D4. |
| C12 | **I need a break** starts the breathing break immediately | ✅ |
| C13 | VoiceOver: notification is read aloud on the lock screen; the session screen and its buttons read sensibly | ✅ |
| C14 | Reduce Motion on (Settings → Accessibility → Motion): circle stays still, phase text still changes | ✅ |

## Outcome

- Breathing pacer usable from the phone's vibration motor? **Partly — only while the phone is held** (decisions.md #13).
- Changes needed to `interventions.json` (amplitudes, durations, sharpness):
- Anything that needs the Swift Core Haptics fallback (decisions.md #12)?
