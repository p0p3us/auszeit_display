"""One bounded update/status cycle; invoked by systemd, never by slide content."""
import argparse
from datetime import datetime, timezone
import json
from http.client import HTTPException
import os
from pathlib import Path
import shutil
import subprocess
from urllib.request import Request, build_opener, ProxyHandler
from urllib.parse import urlsplit

from player.update_test.updater import Downloader, NoRedirect, Store, save, sync_dir, require, read_json, ID, lock

CONFIG = Path('/etc/auszeit-player/config.json')
ROOT = Path('/var/lib/auszeit-player-package-test')
STATUS = Path('/var/lib/auszeit-player-operations')


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    temporary = path.with_suffix('.new')
    save(temporary, json.dumps(value).encode())
    os.replace(temporary, path)
    sync_dir(path.parent)


def command(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=3, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def sample(root):
    try:
        temperature = float(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
    except (OSError, ValueError):
        temperature = None
    heartbeat = None
    try:
        opener = build_opener(ProxyHandler({}), NoRedirect())
        with opener.open('http://127.0.0.1:8081/api/heartbeat', timeout=3) as response:
            heartbeat = read_json(response.read(8193))
    except (OSError, ValueError, HTTPException):
        pass
    return {'free_bytes': shutil.disk_usage(root).free, 'temperature_c': temperature,
            'throttled': command(['/usr/bin/vcgencmd', 'get_throttled']),
            'clock_synchronized': command(['/usr/bin/timedatectl', 'show', '-p', 'NTPSynchronized', '--value']),
            'playback': heartbeat or {'state': 'unknown', 'age_seconds': None}}


def post_status(url, token, payload):
    parts = urlsplit(url)
    require(parts.scheme == 'https' and parts.hostname and not parts.username and not parts.password
            and not parts.fragment and not parts.query, 'Invalid status URL')
    require(isinstance(token, str) and 32 <= len(token) <= 256 and token.isascii()
            and all(c.isalnum() or c in '-_' for c in token), 'Invalid device token')
    request = Request(url, data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, method='POST')
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=10) as response:
        require(response.status == 200, 'Status rejected')
        reply = read_json(response.read(1025))
        require(reply.get('ok') is True, 'Missing status acknowledgement')


def cycle(config, root=ROOT, status_root=STATUS, download_factory=Downloader, sender=post_status, sampler=sample):
    require(isinstance(config.get('device_id'), str) and ID.fullmatch(config['device_id']), 'Invalid device ID')
    root, status_root = Path(root), Path(status_root)
    status_root.mkdir(parents=True, exist_ok=True)
    previous_path = status_root / 'status.json'
    try:
        previous = read_json(previous_path.read_bytes())
    except (OSError, ValueError):
        previous = {}
    store = Store(root)
    status = {'schema_version': 1, 'device_id': config['device_id'], 'sampled_at': utcnow(),
              'last_update_success': previous.get('last_update_success'),
              'last_status_success': previous.get('last_status_success'),
              'update_state': 'unconfigured', 'update_error': None, 'report_error': None}
    feed = config.get('feed_url')
    if feed:
        try:
            store.update(download_factory(feed))
            status['update_state'] = 'ok'
            status['last_update_success'] = utcnow()
        except Exception as error:
            # Do not persist exception messages which might contain URLs or credentials.
            status['update_state'] = 'failed'
            status['update_error'] = type(error).__name__
    try:
        status['content'] = store.state()
    except (OSError, ValueError):
        status['content'] = None
    status.update(sampler(root))
    endpoint = config.get('status_url')
    if endpoint:
        try:
            token = Path(config['token_file']).read_text().strip()
            sender(endpoint, token, status)
            status['last_status_success'] = utcnow()
        except Exception as error:
            status['report_error'] = type(error).__name__
    atomic_json(previous_path, status)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=CONFIG)
    args = parser.parse_args()
    STATUS.mkdir(parents=True, exist_ok=True)
    with lock(STATUS):
        result = cycle(read_json(args.config.read_bytes()))
    print(f"Update: {result['update_state']}; Status: {result['report_error'] or 'local/sent'}", flush=True)


if __name__ == '__main__':
    main()
