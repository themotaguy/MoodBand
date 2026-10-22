# Replay Mode — iPhone Test Checklist

App: `app/` replay screen, with `feedback/server.py` on the laptop
(decisions.md #18). A recorded LifeSnaps day runs through the Random Forest and
the decision module on the laptop and plays on the phone at one hour per
minute. Fill in the results after testing, then record anything that changes
the design in `decisions.md`.

**Device**: iPhone 15 Pro Max · Date: Oct 21, 2026 (standalone Release build)

## Before you start

1. **Laptop**: from the repo root, `.venv/bin/python -m feedback.server`.
   Wait for "demo days ready" and note the address it prints
   (`http://<ip>:8787`; a `.local` address is printed as a backup).
2. iPhone and laptop on the **same Wi-Fi**.
3. **New native build needed** (adds AsyncStorage and the local-network
   setting): with the iPhone plugged in and unlocked, from `app/`,
   `npx expo run:ios --device 00008130-000E48C63A04001C --configuration Release --no-bundler`.
   Free signing expires 7 days after install.

## Status (Oct 21, 2026): E and F pass; VoiceOver (G) not yet tested

All connection (E) and playback (F) checks pass on the iPhone 15 Pro Max
(standalone Release build). Testing added **Snooze for an hour** to the
session's first screen (F7b).

## E. Connection and day list

| # | Check | Result / notes |
|---|---|---|
| E1 | Home → **Replay**. Enter the server address, tap **Load days**. iOS asks to allow **local network** access; allow it | ✅ (Oct 21); plain HTTP to the laptop's IP address works (no `.local` needed) |
| E2 | A list of about 20 days appears. If you get "Could not reach the laptop" with the IP address, try the `.local` address | ✅ (Oct 21) |
| E3 | Tap a day (the first one has 4 suggestions, 2 of them matching the person's report): its summary and **Start replay** appear | ✅ (Oct 21) |
| E4 | Close and reopen the app: the server address is still filled in | ✅ (Oct 21) |

## F. Playing a day

| # | Check | Result / notes |
|---|---|---|
| F1 | **Start replay**: the clock starts at 08:00 and moves one recorded minute per second; mood, confidence and the decision's reason update every 10 seconds | ✅ (Oct 21) |
| F2 | The first suggestion arrives as a notification at the expected time, **with the app open** (banner) | ✅ (Oct 21) |
| F3 | **Lock the phone**: the next suggestion still arrives on the lock screen | ✅ (Oct 21) |
| F4 | Tap it: the session asks first and shows "Replay: at HH:MM in the recorded day, the model read …"; Start plays the break as before | ✅ (Oct 21) |
| F5 | Answer **Yes** or **No**: back on the home screen, the answer shows "(replay, saved on laptop)" | ✅ (Oct 21) |
| F6 | On the laptop, `data/replay/answers.csv` has the row, including the person's **reported mood** when they reported within 30 min | ✅ (Oct 21); the 10:40 answer was saved with reported mood *stressed* (report at 10:44) |
| F7 | **Snooze** on one suggestion (Start → after the break, *Was this right?* → Snooze): the suggestions due in the next recorded hour don't arrive | ✅ (Oct 21). Found on the first try: no Snooze on the ask screen, so you had to sit through a break to snooze; added **Snooze for an hour** there (F7b) |
| F7b | **Snooze for an hour** on the ask screen (new build): the screen closes, and suggestions due in the next recorded hour don't arrive | ✅ (Oct 21) |
| F8 | **Stop replay** partway: no more notifications arrive | ✅ (Oct 21) stopped after 10:40; nothing arrived after |
| F9 | **Laptop server stopped** while answering: the answer shows without "saved on laptop"; restart the server, reopen the app, and it gets sent | ✅ (Oct 21) answered 04:26:30 with the server down; received 04:27:47 after reopening the app, once |

## G. VoiceOver

| # | Check | Result / notes |
|---|---|---|
| G1 | The server field, **Load days** and each day are read clearly (day buttons read as selectable, with the selected one marked) | |
| G2 | During a replay, the status box reads as one item: time, the model's mood and percentage, and the reason | |
| G3 | A connection error is announced | |
| G4 | Anything confusing or too chatty? | |
