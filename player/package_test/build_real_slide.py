"""Build one reproducible wisdom test feed from repository sources (Windows)."""
from datetime import datetime
import json
from pathlib import Path
import posixpath
import re

from scripts.generate_weisheit import render_page
from player.update_test.updater import digest, validate_manifest

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent / 'prepared'
ASSETS = ('static/css/display_pages/base_display.css',
          'static/css/display_pages/weisheit.css', 'static/js/display_layout.js',
          'resources/images/logo.png', 'resources/images/weisheit.png',
          'resources/images/hintergrund.png')


def relative_assets(text, source, known):
    def replace(match):
        target = match.group(0).lstrip('/')
        if target not in known:
            raise ValueError(f'Unlisted asset: {target}')
        return posixpath.relpath(target, posixpath.dirname(source))
    return re.sub(r'/auszeit-display/[A-Za-z0-9_./-]+', replace, text)


def build(output=OUTPUT):
    page = 'auszeit-display/weisheit/index.html'
    files = {'auszeit-display/' + name: (ROOT / name).read_bytes() for name in ASSETS}
    # Fixed snapshot, not a claim to show today's rotating wisdom.
    files[page] = render_page(datetime(2026, 9, 27, 12)).encode()
    for name, body in list(files.items()):
        if name.endswith(('.html', '.css')):
            files[name] = relative_assets(body.decode(), name, files).encode()
    identity = digest(b''.join(name.encode() + b'\0' + files[name] for name in sorted(files)))[:16]
    release = 'weisheit-' + identity
    manifest = {'schema_version': 1, 'release_id': release,
                'generated_at': '2026-09-27T12:00:00+02:00', 'timezone': 'Europe/Vienna',
                'files': [{'path': name, 'bytes': len(body), 'sha256': digest(body)}
                          for name, body in sorted(files.items())],
                'playlist': [{'id': 'weisheit', 'path': page, 'duration_seconds': 20,
                              'valid_from': None, 'valid_until': None}]}
    validate_manifest(manifest, release)
    encoded = json.dumps(manifest).encode()
    manifest_path = f'releases/{release}/manifest.json'
    output = Path(output)
    for name, body in files.items():
        path = output / 'releases' / release / 'content' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    (output / manifest_path).write_bytes(encoded)
    (output / 'latest.json').write_text(json.dumps({'schema_version': 1, 'release_id': release,
        'manifest_path': manifest_path, 'manifest_sha256': digest(encoded)}), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    result = build()
    print(f"Vorbereitet: {result['release_id']} ({len(result['files'])} Dateien), {OUTPUT}")
