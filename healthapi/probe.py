"""Google Health API prototype: does the API give MoodBand what the proposal assumes?

CLAUDE.md task 3 / decisions.md open items. Answers, from the signed-in user's own
Fitbit data:
  1. Sign-in: does OAuth work end to end (here from the laptop; the phone comes later)?
  2. Heart rate: how often is it sampled (proposal assumes ~5 s), and are there gaps?
  3. Steps: how long are the step intervals (the model uses per-minute steps)?
  4. HRV: is it only recorded during sleep (decisions.md #3), or also in the day?
  5. Delay: how old is the newest heart-rate sample, i.e. how far behind real time
     the cloud is after the band syncs through the Fitbit app?
  6. Can the model's 30-minute window features (model/windows.py) be built from it?

Only summary numbers are printed. Credentials, tokens and any saved data stay in
data/google_health/ (gitignored). Standard library only.

Setup (once): Docs/google-health-api.md. Then, from the repo root:
  .venv/bin/python healthapi/probe.py auth          # sign in in the browser
  .venv/bin/python healthapi/probe.py raw           # one data point per type, to check field names
  .venv/bin/python healthapi/probe.py probe --days 7
"""

import argparse
import base64
import hashlib
import http.server
import json
import secrets
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "google_health"
CLIENT_FILE = STORE / "client_secret.json"
TOKEN_FILE = STORE / "token.json"

API = "https://health.googleapis.com/v4/users/me"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}/"
SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",  # HR, HRV
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",             # steps
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",                            # sleep
]

# data type id -> (JSON union field, filter field, kind)
TYPES = {
    "heart-rate": ("heartRate", "heart_rate", "sample"),
    "heart-rate-variability": ("heartRateVariability", "heart_rate_variability", "sample"),
    "steps": ("steps", "steps", "interval"),
    "sleep": ("sleep", "sleep", "session"),
    "daily-heart-rate-variability": ("dailyHeartRateVariability", "daily_heart_rate_variability", "daily"),
    "daily-resting-heart-rate": ("dailyRestingHeartRate", "daily_resting_heart_rate", "daily"),
}


# ---------- sign-in ----------

def client():
    if not CLIENT_FILE.exists():
        sys.exit(f"Missing {CLIENT_FILE.relative_to(ROOT)}: download the OAuth client JSON "
                 "(Docs/google-health-api.md, step 3) and save it there.")
    c = json.loads(CLIENT_FILE.read_text())
    return c.get("installed") or c.get("web")


def post_form(url, fields):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode(errors="replace")}


def save_token(tok):
    tok["obtained_at"] = time.time()
    STORE.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tok, indent=2))
    TOKEN_FILE.chmod(0o600)


def auth():
    c = client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": REDIRECT, "response_type": "code",
        "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent",
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
    })
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("MoodBand: signed in. You can close this tab.".encode())

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print("Opening the browser to sign in. If it doesn't open, visit:\n" + url, flush=True)
    webbrowser.open(url)
    while "code" not in got and "error" not in got:
        server.handle_request()
    server.server_close()
    if got.get("error") or got.get("state") != state:
        sys.exit(f"Sign-in failed: {got.get('error', 'state mismatch')}")

    tok = post_form(TOKEN_URL, {
        "code": got["code"], "client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
        "redirect_uri": REDIRECT, "grant_type": "authorization_code", "code_verifier": verifier,
    })
    if "access_token" not in tok:
        sys.exit(f"Token exchange failed: {tok}")
    save_token(tok)
    granted = set(tok.get("scope", "").split())
    print(f"Signed in. Token saved to {TOKEN_FILE.relative_to(ROOT)}.")
    for s in SCOPES:
        print(f"  {'granted' if s in granted else 'NOT granted'}: {s.rsplit('/', 1)[1]}")
    print(f"  refresh token: {'yes' if tok.get('refresh_token') else 'no'}")


def access_token():
    if not TOKEN_FILE.exists():
        sys.exit("Not signed in: run `healthapi/probe.py auth` first.")
    tok = json.loads(TOKEN_FILE.read_text())
    if time.time() < tok["obtained_at"] + tok.get("expires_in", 3600) - 60:
        return tok["access_token"]
    if not tok.get("refresh_token"):
        sys.exit("Token expired and no refresh token: run `auth` again.")
    c = client()
    new = post_form(TOKEN_URL, {"client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                                "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
    if "access_token" not in new:
        # In Testing mode Google expires refresh tokens after 7 days.
        sys.exit(f"Refresh failed (refresh tokens expire after 7 days in Testing mode): run `auth` again.\n{new}")
    tok.update(new)
    save_token(tok)
    return tok["access_token"]


# ---------- requests ----------

def get(path, params=None):
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token()}",
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} on {path}: {e.read().decode(errors='replace')[:500]}") from None


def time_filter(type_id, start, end):
    field, ffield, kind = TYPES[type_id]
    iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    if kind == "sample":
        f = f"{ffield}.sample_time.physical_time"
    elif kind == "interval":
        f = f"{ffield}.interval.start_time"
    elif kind == "session":
        return f'sleep.interval.end_time >= "{iso(start)}" AND sleep.interval.end_time < "{iso(end)}"'
    else:
        return f'{ffield}.date >= "{start:%Y-%m-%d}" AND {ffield}.date < "{end:%Y-%m-%d}"'
    return f'{f} >= "{iso(start)}" AND {f} < "{iso(end)}"'


def points(type_id, start, end, method="list", max_pages=200):
    path = f"dataTypes/{type_id}/dataPoints" + (":reconcile" if method == "reconcile" else "")
    params = {"filter": time_filter(type_id, start, end)}
    if TYPES[type_id][2] not in ("session",):
        params["pageSize"] = 10000
    out = []
    for _ in range(max_pages):
        page = get(path, params)
        out += page.get("dataPoints", [])
        if not page.get("nextPageToken"):
            break
        params["pageToken"] = page["nextPageToken"]
    return out


# ---------- parsing (field names checked with `raw`) ----------

def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def body(dp, type_id):
    return dp.get(TYPES[type_id][0], {})


def sample_time(b):
    st = b.get("sampleTime", {})
    return parse_time(st.get("physicalTime") if isinstance(st, dict) else st)


def interval(b):
    iv = b.get("interval", {})
    return parse_time(iv.get("startTime")), parse_time(iv.get("endTime"))


def first_number(b, preferred):
    for k in preferred:
        if isinstance(b.get(k), (int, float, str)):
            try:
                return float(b[k])
            except ValueError:
                pass
    for v in b.values():
        if isinstance(v, (int, float)):
            return float(v)
    return None


# ---------- commands ----------

def raw(args):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    for type_id in TYPES:
        try:
            pts = points(type_id, start, end, max_pages=1)
        except RuntimeError as e:
            print(f"\n== {type_id}: ERROR {e}")
            continue
        print(f"\n== {type_id}: {len(pts)} points on the first page")
        if pts:
            print(json.dumps(pts[0], indent=2)[:1500])


def gaps_summary(times):
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    if not gaps:
        return "not enough samples"
    c = Counter(round(g) for g in gaps if g <= 60)
    common = ", ".join(f"{s}s: {n / len(gaps):.0%}" for s, n in c.most_common(4))
    return (f"median gap {statistics.median(gaps):.0f}s; most common {common}; "
            f"gaps > 1 min: {sum(g > 60 for g in gaps):,} (longest {max(gaps) / 3600:.1f} h)")


def probe(args):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=args.days)
    print(f"Window: last {args.days} days (UTC {start:%Y-%m-%d %H:%M} to {now:%Y-%m-%d %H:%M})\n")

    # 1. Sign-in already worked if we got here with a token; the first call proves the scopes.
    hr = points("heart-rate", start, now)
    print(f"1. Sign-in: OK (heart-rate list returned {len(hr):,} points)")

    # 2. Heart rate resolution and gaps.
    hr_t = sorted(t for t in (sample_time(body(p, "heart-rate")) for p in hr) if t)
    print(f"\n2. Heart rate: {len(hr_t):,} samples")
    if hr_t:
        bpm = [first_number(body(p, "heart-rate"), ["beatsPerMinute"]) for p in hr]
        bpm = [b for b in bpm if b is not None]
        print(f"   {gaps_summary(hr_t)}")
        if bpm:
            print(f"   bpm range {min(bpm):.0f}-{max(bpm):.0f}, median {statistics.median(bpm):.0f}")
        rec = points("heart-rate", start, now, method="reconcile")
        print(f"   reconcile returned {len(rec):,} points (list: {len(hr):,})")

    # 3. Steps interval lengths.
    st = points("steps", start, now)
    lengths = Counter()
    for p in st:
        a, b = interval(body(p, "steps"))
        if a and b:
            lengths[round((b - a).total_seconds())] += 1
    print(f"\n3. Steps: {len(st):,} intervals; lengths: "
          + (", ".join(f"{s}s × {n:,}" for s, n in lengths.most_common(4)) or "none"))

    # 4. HRV: inside or outside sleep sessions?
    sleep = points("sleep", start, now)
    sessions = [interval(body(p, "sleep")) for p in sleep]
    sessions = [(a, b) for a, b in sessions if a and b]
    hrv = points("heart-rate-variability", start, now)
    hrv_t = [t for t in (sample_time(body(p, "heart-rate-variability")) for p in hrv) if t]
    asleep = sum(any(a <= t <= b for a, b in sessions) for t in hrv_t)
    hours = Counter(t.astimezone().hour for t in hrv_t)
    print(f"\n4. HRV: {len(hrv_t):,} samples; {asleep:,} inside the {len(sessions)} sleep sessions, "
          f"{len(hrv_t) - asleep:,} outside")
    if hrv_t:
        print("   local hours with samples: " + ", ".join(f"{h:02d}h×{n}" for h, n in sorted(hours.items())))
    for type_id in ("daily-heart-rate-variability", "daily-resting-heart-rate"):
        print(f"   {type_id}: {len(points(type_id, start, now + timedelta(days=1)))} days")

    # 5. How far behind real time is the newest heart-rate sample?
    if hr_t:
        lag = (now - hr_t[-1]).total_seconds() / 60
        print(f"\n5. Newest heart-rate sample is {lag:.0f} min old "
              "(compare with when the Fitbit app last synced)")

    # 6. Can the model's per-minute inputs be built?
    if hr_t:
        minutes = {t.replace(second=0, microsecond=0) for t in hr_t}
        span = (hr_t[-1] - hr_t[0]).total_seconds() / 60
        print(f"\n6. Minutes with a heart-rate reading: {len(minutes):,} of {span:,.0f} "
              f"({len(minutes) / max(span, 1):.0%}); the model needs ≥ 50% of a 30-min window")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    for name in ("raw", "probe"):
        p = sub.add_parser(name)
        p.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    {"auth": lambda a: auth(), "raw": raw, "probe": probe}[args.cmd](args)


if __name__ == "__main__":
    main()
