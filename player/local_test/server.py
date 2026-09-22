#!/usr/bin/env python3
"""Isolated local slideshow test. No production feeds, downloads or credentials."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

ROOT = Path(__file__).resolve().parent / "web"


def timestamp(value):
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Validity timestamps require a timezone")
    return parsed


class Playlist:
    def __init__(self, entries):
        self.entries = entries
        self.index = None
        self.started = None
        ids = set()
        for entry in entries:
            if entry["id"] in ids:
                raise ValueError("Duplicate slide ID")
            ids.add(entry["id"])
            duration = entry["duration_seconds"]
            if type(duration) is not int or not 5 <= duration <= 300:
                raise ValueError("Duration must be an integer from 5 to 300")
            if entry["path"] not in ("/slides/a.html", "/slides/b.html", "/slides/c.html"):
                raise ValueError("Unknown local test slide")
            begin, end = timestamp(entry.get("valid_from")), timestamp(entry.get("valid_until"))
            if begin and end and begin >= end:
                raise ValueError("Empty validity interval")

    def valid(self, index, now):
        entry = self.entries[index]
        begin, end = timestamp(entry.get("valid_from")), timestamp(entry.get("valid_until"))
        return (begin is None or begin <= now) and (end is None or now < end)

    def select(self, now, monotonic):
        if self.index is not None:
            current = self.entries[self.index]
            if self.valid(self.index, now) and monotonic - self.started < current["duration_seconds"]:
                return current
        start = 0 if self.index is None else self.index + 1
        for offset in range(len(self.entries)):
            candidate = (start + offset) % len(self.entries)
            if self.valid(candidate, now):
                self.index, self.started = candidate, monotonic
                return self.entries[candidate]
        self.index = self.started = None
        return None


def demo_entries(now, scenario):
    deadline = (now + timedelta(seconds=65)).isoformat() if scenario == "expiry" else None
    entries = [
        {"id": letter.upper(), "path": f"/slides/{letter}.html", "duration_seconds": 20,
         "valid_from": None, "valid_until": deadline}
        for letter in "abc"
    ]
    if scenario == "expiry":
        entries[1]["valid_from"] = (now + timedelta(seconds=20)).isoformat()
        entries.insert(1, {"id": "EXPIRED", "path": "/slides/b.html", "duration_seconds": 20,
                           "valid_from": None, "valid_until": now.isoformat()})
    return entries


class TestServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, scenario="expiry"):
        self.scenario = scenario
        self.playlist = None
        self.lock = threading.Lock()
        super().__init__(address, Handler)

    def state(self):
        with self.lock:
            now = datetime.now(timezone.utc)
            if self.playlist is None:
                # Start on the first browser poll, not during package installation.
                self.playlist = Playlist(demo_entries(now, self.scenario))
            entry = self.playlist.select(now, time.monotonic())
            return {"scenario": self.scenario, "slide": entry,
                    "state": "playing" if entry else "fallback"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        routes = {"/": ("index.html", "text/html"),
                  "/app.js": ("app.js", "text/javascript"),
                  "/style.css": ("style.css", "text/css")}
        if self.path == "/healthz":
            return self.reply(200, b'{"ok":true}', "application/json")
        if self.path == "/api/state":
            return self.reply(200, json.dumps(self.server.state()).encode(), "application/json")
        if self.path in ("/slides/a.html", "/slides/b.html", "/slides/c.html"):
            letter = self.path[-6].upper()
            content = (ROOT / "slide.html").read_text(encoding="utf-8").replace("{{LETTER}}", letter)
            return self.reply(200, content.encode(), "text/html")
        if self.path not in routes:
            return self.reply(404, b"Not found", "text/plain")
        filename, content_type = routes[self.path]
        self.reply(200, (ROOT / filename).read_bytes(), content_type)

    def reply(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Polling must not fill the SD card with access logs.
        if args and str(args[1] if len(args) > 1 else "") != "200":
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--scenario", choices=("expiry", "cycle"), default="expiry")
    args = parser.parse_args()
    with TestServer(("127.0.0.1", args.port), args.scenario) as server:
        print(f"Local test: http://127.0.0.1:{args.port}/ ({args.scenario})", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
