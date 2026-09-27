"""Load the prepared wisdom feed through the existing verified downloader."""
from pathlib import Path
import socket

from player.package_test.publish import STORE
from player.update_test.exercise import feed
from player.update_test.updater import Downloader, Store, digest, read_json, require, ID, validate_manifest


def activate(directory, store):
    directory = Path(directory)
    latest_bytes = (directory / 'latest.json').read_bytes()
    latest = read_json(latest_bytes)
    release = latest.get('release_id')
    require(isinstance(release, str) and ID.fullmatch(release), 'Invalid release')
    manifest_path = f'releases/{release}/manifest.json'
    require(latest.get('manifest_path') == manifest_path, 'Invalid manifest path')
    body = (directory / manifest_path).read_bytes()
    require(digest(body) == latest.get('manifest_sha256'), 'Invalid manifest hash')
    manifest = read_json(body)
    validate_manifest(manifest, release)
    routes = {'/latest.json': latest_bytes, '/' + manifest_path: body}
    for item in manifest['files']:
        path = f"releases/{release}/content/{item['path']}"
        routes['/' + path] = (directory / path).read_bytes()
    with feed(routes) as url:
        return Store(store).update(Downloader(url, allow_loopback_http=True))


if __name__ == '__main__':
    if socket.gethostname() != 'auszeit-player-01':
        raise SystemExit('Nur auf auszeit-player-01 ausfuehren.')
    result = activate(Path(__file__).parent / 'prepared', STORE)
    print(f"Auszeit-Weisheit geladen und geprueft: {result['active']['release_id']}")
    print('Anzeige wechselt an der naechsten Foliengrenze. Testfeed beendet.')
