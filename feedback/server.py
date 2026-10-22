"""Laptop server for the app's replay mode (decisions.md #18). Standard library only.

  GET  /days                      demo days (most suggestions matching a real report first)
  GET  /replay?id=<id>&date=<d>   one day's timeline (replay.timeline)
  POST /answers                   one "Was this right?" answer, appended to data/replay/answers.csv

The phone and the laptop must be on the same Wi-Fi; the app is pointed at the
address printed on start-up.

Usage (from the repo root): .venv/bin/python -m feedback.server [--port 8787]
"""

import csv
import json
import socket
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

from feedback import replay

ROOT = Path(__file__).resolve().parent.parent
ANSWERS = ROOT / "data" / "replay" / "answers.csv"
ANSWER_FIELDS = ["received_at", "answered_at", "id", "date", "time", "intervention",
                 "predicted_mood", "reported_mood", "answer", "profile"]
ANSWER_VALUES = {"yes", "no", "snooze", "not_now"}
PROFILE_VALUES = {"sighted", "low_vision", "blind"}


def save_answer(body, reports, path=ANSWERS):
    """Validate an answer from the app, add the person's nearby report, append it to the CSV."""
    missing = [k for k in ("answered_at", "id", "date", "time", "intervention", "answer", "profile") if not body.get(k)]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    if body["answer"] not in ANSWER_VALUES or body["profile"] not in PROFILE_VALUES:
        raise ValueError("unknown answer or profile")
    ts = pd.Timestamp(f"{body['date']} {body['time']}")
    row = {
        **{k: body.get(k) for k in ANSWER_FIELDS},
        "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),  # UTC, like the phone's answered_at
        "reported_mood": replay.nearest_report(reports, body["id"], ts),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ANSWER_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)
    return row


def make_handler(preds, reports, days):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/days":
                return self._send(200, days)
            if url.path == "/replay":
                q = {k: v[0] for k, v in parse_qs(url.query).items()}
                try:
                    return self._send(200, replay.timeline(preds, reports, q["id"], q["date"]))
                except (KeyError, ValueError) as e:
                    return self._send(404, {"error": str(e)})
            self._send(404, {"error": "unknown path"})

        def do_POST(self):
            if urlparse(self.path).path != "/answers":
                return self._send(404, {"error": "unknown path"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                return self._send(201, save_answer(body, reports))
            except (ValueError, TypeError, AttributeError) as e:
                return self._send(400, {"error": str(e)})

    return Handler


def lan_address():
    # Connecting a UDP socket sends nothing; it just picks the interface used for the LAN.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main():
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8787
    preds, reports = replay.load()
    days = replay.demo_days(preds, reports)
    host = socket.gethostname()
    host = host if host.endswith(".local") else f"{host}.local"
    print(f"{len(days)} demo days ready. In the app, set the server to:  http://{lan_address()}:{port}\n"
          f"  (if iOS refuses the IP address, use  http://{host}:{port})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), make_handler(preds, reports, days)).serve_forever()


if __name__ == "__main__":
    main()
