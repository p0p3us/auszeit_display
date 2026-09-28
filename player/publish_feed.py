"""Separate feed publisher; reads source files but never runs production generators."""
from datetime import datetime, timedelta
from ftplib import FTP, error_perm
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
from zoneinfo import ZoneInfo

from player.export_feed import Export
from player.package_test.activate_real import activate
from player.update_test.updater import Store, lock

TARGET = '/auszeit-player-feed'
FOLDERS = ('templates', 'data', 'static', 'resources')


def inventory(root):
    result = {}
    for folder in FOLDERS:
        for path in sorted((root / folder).rglob('*')):
            if path.is_symlink():
                raise ValueError('Symbolic links are not supported in feed sources')
            if path.is_file():
                with path.open('rb') as stream:
                    result[path.relative_to(root).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return result


def snapshot(source, destination):
    before = inventory(source)
    for folder in FOLDERS:
        shutil.copytree(source / folder, destination / folder)
    if before != inventory(destination) or before != inventory(source):
        raise ValueError('Source changed during snapshot; retry on next run')


def enter_directory(ftp, name):
    # Only existing, or newly created, children of the dedicated feed directory.
    try:
        ftp.cwd(name)
        return
    except error_perm as error:
        if not str(error).startswith('550'):
            raise
        ftp.mkd(name)
    ftp.cwd(name)


def upload(ftp, package):
    latest = (package / 'latest.json').read_bytes()
    pointer = json.loads(latest)
    release = pointer['release_id']
    folder = package / 'releases' / release
    ftp.cwd(TARGET)  # Must already exist; never fall back to the FTP root.
    enter_directory(ftp, 'releases')
    enter_directory(ftp, release)
    release_root = ftp.pwd()
    for path in sorted(folder.rglob('*')):
        if not path.is_file():
            continue
        ftp.cwd(release_root)
        relative = path.relative_to(folder)
        for part in relative.parts[:-1]:
            enter_directory(ftp, part)
        with path.open('rb') as stream:
            ftp.storbinary('STOR ' + path.name, stream)
        # Read back every uploaded file before exposing the new release.
        received = hashlib.sha256()
        ftp.retrbinary('RETR ' + path.name, received.update)
        with path.open('rb') as stream:
            expected = hashlib.file_digest(stream, 'sha256').hexdigest()
        if received.hexdigest() != expected:
            raise ValueError('Uploaded file checksum mismatch')
    ftp.cwd(TARGET)
    ftp.storbinary('STOR latest.json.uploading', io.BytesIO(latest))
    received = io.BytesIO()
    ftp.retrbinary('RETR latest.json.uploading', received.write)
    if received.getvalue() != latest:
        raise ValueError('Uploaded pointer mismatch')
    ftp.rename('latest.json.uploading', 'latest.json')
    return release


def main():
    if socket.gethostname() != 'auszeit':
        raise SystemExit('Only run on content server auszeit')
    source = Path(__file__).resolve().parents[1]
    state = Path.home() / '.local/state/auszeit-player-feed'
    state.mkdir(parents=True, exist_ok=True)
    with lock(state), tempfile.TemporaryDirectory(prefix='build-', dir=state) as temporary:
        work = Path(temporary)
        snapshot(source, work / 'snapshot')
        now = datetime.now(ZoneInfo('Europe/Vienna'))
        export = Export(work / 'snapshot', now, now + timedelta(days=7)).collect()
        package = work / 'package'
        export.write(package)
        activate(package, work / 'verification')
        store = Store(work / 'verification')
        store.verify(**store.state()['active'])
        with FTP(timeout=30) as ftp:
            ftp.connect(os.environ['FTP_HOST'])
            ftp.login(os.environ['FTP_USER'], os.environ['FTP_PASS'])
            release = upload(ftp, package)
        # Save only the latest report; never persist credentials.
        report = json.loads((package / 'report.json').read_text())
        report.update(release_id=release, published_at=now.isoformat())
        pending = state / 'last-publish.new'
        pending.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        pending.replace(state / 'last-publish.json')
        print(f"Published {release}: {len(export.playlist)} slides, {len(export.omitted)} omitted", flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # FTP exceptions may contain server details; never log credentials.
        raise SystemExit('Feed publication failed: ' + type(error).__name__) from None
