"""Publish a synthetic package to the display test store via a temporary feed."""
import argparse
import json
from pathlib import Path
import socket

from player.update_test.exercise import feed
from player.update_test.updater import Downloader, InvalidRelease, Store, digest

STORE = Path('/var/lib/auszeit-player-package-test')


def package(version):
    release = f'display-{version}'
    css = (Path(__file__).resolve().parents[1] / 'local_test/web/style.css').read_bytes()
    files = {'auszeit-display/style.css': css}
    for letter in 'abc':
        files[f'auszeit-display/{letter}.html'] = f'''<!doctype html>
<html lang="de"><meta charset="utf-8"><title>Auszeit Pakettest</title>
<link rel="stylesheet" href="style.css">
<main class="stage slide-{letter.upper()}">
<div class="eyebrow">CAFÉ RESTAURANT AUSZEIT</div>
<h1>Folie {letter.upper()}</h1><p>Inhaltsstand {version}</p>
<div class="note">Lokal gespeichert · 20 Sekunden pro Folie</div>
</main></html>'''.encode()
    # Stable test fixtures: an existing release ID always has identical bytes.
    manifest = {'schema_version': 1, 'release_id': release,
                'generated_at': '2026-09-23T00:00:00+02:00', 'timezone': 'Europe/Vienna',
                'files': [{'path': name, 'bytes': len(body), 'sha256': digest(body)}
                          for name, body in files.items()],
                'playlist': [{'id': letter.upper(), 'path': f'auszeit-display/{letter}.html',
                              'duration_seconds': 20, 'valid_from': None, 'valid_until': None}
                             for letter in 'abc']}
    body = json.dumps(manifest).encode()
    manifest_path = f'releases/{release}/manifest.json'
    routes = {'/latest.json': json.dumps({'schema_version': 1, 'release_id': release,
              'manifest_path': manifest_path, 'manifest_sha256': digest(body)}).encode(),
              '/' + manifest_path: body}
    routes.update({f'/releases/{release}/content/{name}': body for name, body in files.items()})
    return routes


def publish(root, version):
    routes = package(version)
    if version == 'broken':
        routes['/releases/display-broken/content/auszeit-display/style.css'] = b'broken'
    with feed(routes) as url:
        return Store(root).update(Downloader(url, allow_loopback_http=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', choices=('1', '2', 'broken', 'init'))
    args = parser.parse_args()
    if socket.gethostname() != 'auszeit-player-01':
        raise SystemExit('Nur auf dem Anzeige-Pi auszeit-player-01 ausfuehren.')
    store = Store(STORE)
    if args.version == 'init' and store.state()['active']:
        store.verify(**store.state()['active'])
        print('Vorhandenen Testbestand beibehalten.')
        return
    try:
        state = publish(STORE, '1' if args.version == 'init' else args.version)
    except InvalidRelease as error:
        raise SystemExit(f'Paket abgewiesen; bisheriger Stand unveraendert: {error}')
    print(f"Gepruefter Bestand: {state['active']['release_id']}. Testfeed ist jetzt beendet.")


if __name__ == '__main__':
    main()
