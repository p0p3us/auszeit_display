"""Display verified synthetic packages. Relative assets only; not a production feed."""
import argparse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import mimetypes
import threading
import time

from player.local_test.server import Handler as LocalHandler, Playlist
from player.update_test.updater import Store
from player.package_test.publish import STORE


class PackageServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, root):
        self.store = Store(root)
        self.playlist = None
        self.release = None
        self.observed = None
        self.routes = {}
        self.lock = threading.Lock()
        self.last_error = None
        super().__init__(address, Handler)

    def load(self, pointer):
        manifest = self.store.verify(**pointer)
        release = pointer['release_id']
        prefix = f'/releases/{release}/content/'
        entries = [entry | {'id': release + ':' + entry['id'], 'path': prefix + entry['path']}
                   for entry in manifest['playlist']]
        paths = {prefix + item['path']: self.store.releases / release / 'content' / item['path']
                 for item in manifest['files']}
        playlist = Playlist(entries, allowed_paths=paths)
        # Retain the outgoing release for a frame still finishing its load.
        old_prefix = f'/releases/{self.release}/content/'
        self.routes = {name: path for name, path in self.routes.items() if name.startswith(old_prefix)} | paths
        self.playlist, self.release = playlist, release

    def state(self, now=None, monotonic=None):
        with self.lock:
            now = now or datetime.now(timezone.utc)
            monotonic = time.monotonic() if monotonic is None else monotonic
            playlist = self.playlist
            boundary = (playlist is None or playlist.index is None
                        or not playlist.valid(playlist.index, now)
                        or monotonic - playlist.started >= playlist.entries[playlist.index]['duration_seconds'])
            if boundary:
                try:
                    state = self.store.state()
                    pointer = state['active']
                    if pointer and pointer != self.observed:
                        self.observed = pointer
                        try:
                            self.load(pointer)
                            self.last_error = None
                        except (OSError, ValueError, KeyError, TypeError) as error:
                            self.last_error = str(error)
                            if self.playlist is None and state.get('previous'):
                                self.load(state['previous'])
                except (OSError, ValueError, KeyError, TypeError) as error:
                    self.last_error = str(error)
            entry = self.playlist.select(now, monotonic) if self.playlist else None
            return {'scenario': 'packages', 'release_id': self.release, 'slide': entry,
                    'state': 'playing' if entry else 'fallback', 'last_error': self.last_error}


class Handler(LocalHandler):
    def do_GET(self):
        if self.path.startswith('/releases/'):
            with self.server.lock:
                path = self.server.routes.get(self.path)
            if path is None:
                return self.reply(404, b'Not found', 'text/plain')
            try:
                body = path.read_bytes()
            except OSError:
                return self.reply(404, b'Not found', 'text/plain')
            return self.reply(200, body, mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        # The earlier synthetic routes are not part of the package display.
        if self.path.startswith('/slides/'):
            return self.reply(404, b'Not found', 'text/plain')
        super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8081)
    args = parser.parse_args()
    with PackageServer(('127.0.0.1', args.port), STORE) as server:
        server.serve_forever()


if __name__ == '__main__':
    main()
