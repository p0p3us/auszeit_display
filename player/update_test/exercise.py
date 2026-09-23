"""Run the release update lab without touching the kiosk or production server."""
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPException
import json
from pathlib import Path
import socket
import tempfile
import threading

try:
    from .updater import Downloader, Store, digest, InvalidRelease
except ImportError:
    from updater import Downloader, Store, digest, InvalidRelease


def package(release_id, label):
    files = {
        "auszeit-display/demo/index.html": f'<!doctype html><html lang="de"><head><link rel="stylesheet" href="../style.css"></head><body><h1>{label}</h1></body></html>'.encode(),
        "auszeit-display/style.css": b"body {background:#172925;color:#f5eedc;font:80px sans-serif}",
    }
    manifest = {
        "schema_version": 1, "release_id": release_id,
        "generated_at": datetime.now(timezone.utc).isoformat(), "timezone": "Europe/Vienna",
        "files": [{"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in files.items()],
        "playlist": [{"id": "demo", "path": "auszeit-display/demo/index.html", "duration_seconds": 20,
                      "valid_from": None, "valid_until": None}],
    }
    encoded = json.dumps(manifest).encode()
    pointer = {"schema_version": 1, "release_id": release_id,
               "manifest_path": f"releases/{release_id}/manifest.json", "manifest_sha256": digest(encoded)}
    routes = {"/latest.json": json.dumps(pointer).encode(), f"/releases/{release_id}/manifest.json": encoded}
    routes.update({f"/releases/{release_id}/content/{name}": value for name, value in files.items()})
    return routes


@contextmanager
def feed(routes):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            value = routes.get(self.path)
            if value is None:
                self.send_error(404)
                return
            body, declared = value if isinstance(value, tuple) else (value, len(value))
            self.send_response(200)
            self.send_header("Content-Length", str(declared))
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def run(root):
    store = Store(root)
    routes = package("demo-1", "Erster geprüfter Stand")
    with feed(routes) as url:
        client = Downloader(url, allow_loopback_http=True)
        store.update(client)
        assert store.state()["active"]["release_id"] == "demo-1"
        print("OK 1/6: Gueltiges Paket geladen, geprueft und im Testbestand aktiviert.", flush=True)

        def reject(changed, label):
            before = store.state()
            routes.clear()
            routes.update(changed)
            try:
                store.update(client)
            except (InvalidRelease, OSError, HTTPException):
                assert store.state() == before, "Aktiver Stand wurde trotz Fehler geaendert"
                store.verify(**before["active"])
                print(label, flush=True)
            else:
                raise AssertionError("Fehlerhaftes Paket wurde angenommen")

        corrupt = package("demo-corrupt", "Defekt")
        key = "/releases/demo-corrupt/content/auszeit-display/style.css"
        corrupt[key] = b"X" * len(corrupt[key])
        reject(corrupt, "OK 2/6: Falsche Pruefsumme abgewiesen; demo-1 bleibt aktiv.")
        missing = package("demo-missing", "Unvollstaendig")
        del missing["/releases/demo-missing/content/auszeit-display/style.css"]
        reject(missing, "OK 3/6: Fehlende CSS-Datei abgewiesen; demo-1 bleibt aktiv.")
        truncated = package("demo-truncated", "Abgebrochen")
        key = "/releases/demo-truncated/content/auszeit-display/style.css"
        body = truncated[key]
        truncated[key] = (body[:10], len(body))
        reject(truncated, "OK 4/6: Abgebrochener Download abgewiesen; demo-1 bleibt aktiv.")
        routes.clear()
        routes.update(package("demo-2", "Zweiter geprüfter Stand"))
        store.update(client)
        assert store.state()["active"]["release_id"] == "demo-2"
        assert store.state()["previous"]["release_id"] == "demo-1"
        print("OK 5/6: demo-2 aktiviert; demo-1 als vorheriger Stand erhalten.", flush=True)
    # Server is now stopped. Reopen the state as a new consumer would on startup.
    before = store.state()
    try:
        store.update(client)
    except OSError:
        pass
    else:
        raise AssertionError("Feed unerwartet erreichbar")
    reopened = Store(root)
    assert reopened.state() == before
    reopened.verify(**before["active"])
    reopened.verify(**before["previous"])
    print("OK 6/6: Ohne Feed bleiben aktiver und vorheriger Stand vollstaendig lesbar.", flush=True)
    print("PASS: Alle 6 Downloadtests bestanden. Laufende Anzeige unveraendert.", flush=True)


if __name__ == "__main__":
    if socket.gethostname().split(".")[0].lower() == "auszeit":
        raise SystemExit("Abbruch: Dieses Labor nicht auf dem Inhaltsserver ausfuehren.")
    base = Path.home() / ".local" / "state" / "auszeit-update-lab"
    base.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="run-", dir=base))
    print(f"Isolierter Testbestand: {root}", flush=True)
    run(root)
