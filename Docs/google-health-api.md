# Google Health API Prototype — Setup and Checklist

CLAUDE.md task 3: confirm that the Google Health API gives MoodBand what the
proposal assumes, before building the live connection. The prototype is
`healthapi/probe.py`, run on the laptop. It prints summary numbers only, and
everything it stores (the OAuth client, the sign-in token) stays in
`data/google_health/`, which git ignores.

**Device**: Fitbit Inspire 3 (arrived by Nov 9, 2026; not yet paired).

## What the documentation says (read Nov 9, 2026)

- **Base URL**: `https://health.googleapis.com/v4/users/me/dataTypes/{type}/dataPoints`.
  `list` returns the raw points (they can overlap, from several sources);
  `:reconcile` merges sources into one stream and drops wearable data from
  times the band wasn't worn. Up to 10,000 points per page.
- **Heart rate** (`heart-rate`): point-in-time samples with beats per minute,
  motion context and sensor location. Storage resolution is listed as
  **1 second**. Google's Inspire 3 spec sheet (Memory section) says the band
  stores heart rate every **1 second during exercise tracking and every 5
  seconds at other times**; check 2 confirms this on the band's own data.
- **HRV** (`heart-rate-variability`): samples of RMSSD in milliseconds. The
  type is listed under both the Vitals and the Sleep guides, but the docs
  **don't say whether it is recorded only during sleep**. Daily HRV
  (`daily-heart-rate-variability`) and resting heart rate are daily summaries.
- **Steps** (`steps`): intervals. Their length isn't documented.
- **Sign-in**: Google OAuth 2.0. Scopes used here:
  `googlehealth.health_metrics_and_measurements.readonly` (heart rate, HRV),
  `googlehealth.activity_and_fitness.readonly` (steps),
  `googlehealth.sleep.readonly` (sleep).
- **Testing limits**: while the OAuth app is in *Testing*, only listed test
  users can sign in, and **refresh tokens expire after 7 days**, so you sign
  in again weekly. Up to 100 users are allowed before Google requires a
  security review. That is enough for the friends trial.
- **Read-only**: vitals arrive by the band syncing through the Fitbit app;
  the API can't change them. Data reaches the cloud only after a sync, so
  "real time" means "as recent as the last sync" (check 5 below).
- Google provides no sample data, so nothing can be checked until the band
  has recorded some.

Sources: [Vitals data types](https://developers.google.com/health/data-types/vitals),
[dataPoints reference](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints),
[list](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list),
[reconcile](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile),
[Set up Google Cloud and OAuth](https://developers.google.com/health/setup),
[First API call codelab](https://developers.google.com/health/codelabs/make-your-first-api-call),
[Inspire 3 technical specs](https://store.google.com/product/fitbit_inspire_3_specs).

## Setup (once, about 15 minutes)

Use the **same Google account** for all of this and for the Fitbit app when
you pair the Inspire 3, since the data belongs to that account.

1. **Project**: in the [Google Cloud console](https://console.cloud.google.com/),
   create a project (e.g. `moodband-dev`). Then go to APIs & Services ›
   Library, search **Google Health API**, and click **Enable**.
2. **Consent screen**: Google Auth Platform (or APIs & Services › OAuth
   consent screen):
   - **Branding**: app name *MoodBand*, your email as the support contact.
   - **Audience**: user type **External**, publishing status **Testing**;
     under **Test users**, add the Google account you'll pair the Fitbit with.
   - **Data Access** › Add or remove scopes: search *Google Health API* and
     tick the three `.readonly` scopes listed above.
3. **Client**: Credentials › Create credentials › OAuth client ID ›
   application type **Desktop app**, name *MoodBand laptop*. Download the
   JSON and save it as `data/google_health/client_secret.json`.
   (If you make a *Web application* client instead, add
   `http://127.0.0.1:8765/` as an authorized redirect URI.)
4. **Sign in**, from the repo root:
   `.venv/bin/python healthapi/probe.py auth`. The browser opens. Sign in with
   the test-user account. Google warns that the app isn't verified; choose
   *Continue*, then allow all three permissions. The terminal should say
   **granted** for each scope and **refresh token: yes**.

Steps 1–4 work **before the band is paired**, but data calls don't: until
the Google account has a Fitbit / Google Health profile, every call returns
400 `ACCOUNT_NOT_LINKED` (found Nov 10). If sign-in says `access_denied`,
the account is missing from Audience › Test users.

## After pairing the Inspire 3

1. Pair it in the Fitbit app with the same Google account. Wear it for at
   least **one full day and one night**, then open the Fitbit app so it syncs.
2. `.venv/bin/python healthapi/probe.py raw --days 2`: prints one data point of
   each type. The docs show no example for heart rate or HRV, so this checks
   the field names `probe` relies on (`sampleTime.physicalTime`,
   `beatsPerMinute`, `interval.startTime`).
3. `.venv/bin/python healthapi/probe.py probe --days 2`: answers the checks below.
   For check 5, note the time of the last sync shown in the Fitbit app.

## Checklist

| # | Check | Assumed in the proposal | Result / notes |
|---|---|---|---|
| 1 | Sign-in works end to end from the laptop (all 3 scopes granted, refresh token issued) | Yes | ✅ (Nov 10). First try was blocked (403 `access_denied`) until the account was added under Audience › Test users |
| 1b | Calls succeed with the band not yet paired (0 points, no errors) | — | ✅ (Nov 11): all 6 types return 0 points, no errors. First needed a Fitbit / Google Health profile on the account (Nov 10: every call returned 400 `ACCOUNT_NOT_LINKED` until the Fitbit app was set up with the same Google account) |
| 2 | Heart-rate sampling interval, and gaps during the day | ~5 s, continuous | |
| 2b | `reconcile` vs `list`: same points, or duplicates removed? | — | |
| 3 | Step interval length | 1 min | |
| 4 | HRV samples only inside sleep sessions? | Overnight only (#3) | |
| 4b | Daily HRV and resting heart rate present for each night | Yes | |
| 5 | Delay: newest heart-rate sample vs last sync; does it update without opening the Fitbit app? | Near real time | |
| 6 | At least 50% of minutes have heart rate, so the model's 30-min windows can be built | Yes | |
| 7 | Sign-in from the phone app (iOS now, Android later) | Yes | Later step |
| 8 | Wrist alert: a MoodBand notification buzzes on the Inspire 3 (decisions.md #13 open item) | — | |

Record anything that contradicts the proposal in `decisions.md`.
