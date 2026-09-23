"""Bounded release downloader. Test stage: no connection to the display service."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

MAX_JSON = 1024 * 1024
MAX_FILE = 50 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
RESERVE = 1024 * 1024 * 1024
ID = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
PART = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,119}\Z")


class InvalidRelease(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidRelease(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def read_json(data):
    try:
        result = json.loads(data, object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(InvalidRelease("Non-finite JSON")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise InvalidRelease("Invalid JSON") from error
    require(isinstance(result, dict), "Expected JSON object")
    return result


def valid_path(value):
    require(isinstance(value, str) and len(value) <= 400, "Invalid path")
    parts = value.split("/")
    require(all(PART.fullmatch(part) and not part.endswith(".") for part in parts), "Unsafe path")
    # Windows aliases must not collide during development or package validation.
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10)}
    require(all(part.split(".")[0].upper() not in reserved for part in parts), "Reserved path")
    return value


def date_value(value):
    if value is None:
        return None
    require(isinstance(value, str), "Invalid date")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise InvalidRelease("Invalid date") from error
    require(parsed.tzinfo is not None, "Date requires timezone")
    return parsed


def validate_manifest(manifest, release_id):
    require(type(manifest.get("schema_version")) is int and manifest["schema_version"] == 1, "Unsupported manifest")
    require(manifest.get("release_id") == release_id, "Release ID mismatch")
    require(manifest.get("timezone") == "Europe/Vienna", "Unsupported timezone")
    require(manifest.get("generated_at") is not None, "Missing generation date")
    date_value(manifest["generated_at"])
    files, playlist = manifest.get("files"), manifest.get("playlist")
    require(isinstance(files, list) and 0 < len(files) <= 2000, "Invalid file list")
    require(isinstance(playlist, list) and len(playlist) <= 2000, "Invalid playlist")
    paths, canonical, total = set(), set(), 0
    for entry in files:
        require(isinstance(entry, dict), "Invalid file entry")
        name = valid_path(entry.get("path"))
        require(name.startswith("auszeit-display/"), "Unexpected content root")
        require(name.casefold() not in canonical, "Duplicate or case-colliding path")
        canonical.add(name.casefold())
        paths.add(name)
        size = entry.get("bytes")
        require(type(size) is int and 0 <= size <= MAX_FILE, "Invalid file size")
        require(isinstance(entry.get("sha256"), str) and HASH.fullmatch(entry["sha256"]), "Invalid hash")
        total += size
    require(total <= MAX_TOTAL, "Release too large")
    require(not any('/'.join(name.split('/')[:i]).casefold() in canonical
                    for name in paths for i in range(1, len(name.split('/')))), "File/directory collision")
    ids = set()
    for slide in playlist:
        require(isinstance(slide, dict), "Invalid slide")
        name = slide.get("id")
        require(isinstance(name, str) and ID.fullmatch(name) and name not in ids, "Invalid slide ID")
        ids.add(name)
        require(isinstance(slide.get("path"), str) and slide["path"] in paths and slide["path"].endswith(".html"), "Slide file missing")
        duration = slide.get("duration_seconds")
        require(type(duration) is int and 5 <= duration <= 300, "Invalid slide duration")
        begin, end = date_value(slide.get("valid_from")), date_value(slide.get("valid_until"))
        require(not (begin and end) or begin < end, "Invalid validity interval")
    return total


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise InvalidRelease("Redirect rejected")


class Downloader:
    def __init__(self, base_url, allow_loopback_http=False):
        parts = urlsplit(base_url)
        require(parts.scheme == "https" or (allow_loopback_http and parts.scheme == "http" and parts.hostname == "127.0.0.1"), "HTTPS required")
        require(bool(parts.hostname) and not parts.username and not parts.password and not parts.query and not parts.fragment, "Invalid feed URL")
        self.base = base_url.rstrip("/") + "/"
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def transfer(self, relative, output, limit, expected_hash=None, expected_size=None):
        valid_path(relative)
        deadline = time.monotonic() + 120
        sha, count = hashlib.sha256(), 0
        with self.opener.open(self.base + relative, timeout=10) as response:
            require(response.status == 200, "Unexpected HTTP response")
            length = response.headers.get("Content-Length")
            if length is not None:
                require(length.isdecimal() and int(length) <= limit, "Response too large")
                require(expected_size is None or int(length) == expected_size, "Wrong declared length")
            while True:
                require(time.monotonic() <= deadline, "Download timed out")
                chunk = response.read(min(65536, limit - count + 1))
                if not chunk:
                    break
                count += len(chunk)
                require(count <= limit, "Response too large")
                sha.update(chunk)
                output.write(chunk)
        require(expected_size is None or count == expected_size, "Incomplete file")
        require(expected_hash is None or sha.hexdigest() == expected_hash, "Checksum mismatch")

    def small(self, relative):
        import io
        output = io.BytesIO()
        self.transfer(relative, output, MAX_JSON)
        return output.getvalue()


def sync_dir(path):
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def save(path, data):
    with path.open("wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


@contextmanager
def lock(root):
    with (root / "update.lock").open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.releases = self.root / "releases"
        self.releases.mkdir(exist_ok=True)

    def state(self):
        path = self.root / "active.json"
        return read_json(path.read_bytes()) if path.exists() else {"active": None, "previous": None}

    def verify(self, release_id, manifest_sha256):
        require(isinstance(release_id, str) and ID.fullmatch(release_id), "Invalid release ID")
        folder = self.releases / release_id
        manifest_bytes = (folder / "manifest.json").read_bytes()
        require(digest(manifest_bytes) == manifest_sha256, "Stored manifest changed")
        manifest = read_json(manifest_bytes)
        validate_manifest(manifest, release_id)
        for entry in manifest["files"]:
            path = folder / "content" / entry["path"]
            require(path.stat().st_size == entry["bytes"], "Stored file size changed")
            with path.open("rb") as handle:
                require(hashlib.file_digest(handle, "sha256").hexdigest() == entry["sha256"], "Stored file changed")
        return manifest

    def update(self, downloader):
        with lock(self.root):
            latest = read_json(downloader.small("latest.json"))
            release_id = latest.get("release_id")
            require(type(latest.get("schema_version")) is int and latest["schema_version"] == 1, "Unsupported pointer")
            require(isinstance(release_id, str) and ID.fullmatch(release_id), "Invalid release ID")
            manifest_path = f"releases/{release_id}/manifest.json"
            require(latest.get("manifest_path") == manifest_path, "Unexpected manifest path")
            manifest_hash = latest.get("manifest_sha256")
            require(isinstance(manifest_hash, str) and HASH.fullmatch(manifest_hash), "Invalid manifest hash")
            content = downloader.small(manifest_path)
            require(digest(content) == manifest_hash, "Manifest checksum mismatch")
            manifest = read_json(content)
            total = validate_manifest(manifest, release_id)
            final = self.releases / release_id
            if final.exists():
                self.verify(release_id, manifest_hash)
            else:
                require(shutil.disk_usage(self.root).free >= total + len(content) + RESERVE, "Insufficient free storage")
                staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=self.releases)).resolve()
                try:
                    for entry in manifest["files"]:
                        target = staging / "content" / entry["path"]
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with target.open("wb") as output:
                            downloader.transfer(f"releases/{release_id}/content/{entry['path']}", output,
                                                entry["bytes"], entry["sha256"], entry["bytes"])
                            output.flush()
                            os.fsync(output.fileno())
                    save(staging / "manifest.json", content)
                    for directory in sorted((p for p in staging.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                        sync_dir(directory)
                    sync_dir(staging)
                    os.rename(staging, final)
                    sync_dir(self.releases)
                finally:
                    if staging.exists():
                        require(staging.parent == self.releases.resolve() and staging.name.startswith(".staging-"), "Unsafe cleanup path")
                        shutil.rmtree(staging)
            previous = self.state()
            active = {"release_id": release_id, "manifest_sha256": manifest_hash}
            if previous["active"] == active:
                return self.state()
            state = {"active": active, "previous": previous["active"]}
            temporary = self.root / "active.json.new"
            save(temporary, json.dumps(state).encode())
            os.replace(temporary, self.root / "active.json")
            sync_dir(self.root)
            return state
