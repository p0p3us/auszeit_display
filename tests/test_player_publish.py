from ftplib import error_perm
from datetime import datetime, timezone
import json
from pathlib import Path
import posixpath
import tempfile
import unittest
from unittest.mock import patch

from player.publish_feed import FOLDERS, TARGET, snapshot, upload, prune_remote
from player.update_test.exercise import package


class FakeFTP:
    def __init__(self, corrupt=False):
        self.here = '/'
        self.dirs = {'/', TARGET}
        self.files = {TARGET + '/latest.json': b'old'}
        self.corrupt = corrupt
        self.renames = []

    def cwd(self, name):
        path = posixpath.normpath(posixpath.join(self.here, name))
        if path not in self.dirs:
            raise error_perm('550 Directory missing')
        self.here = path

    def nlst(self):
        return [posixpath.basename(p) for p in self.dirs if posixpath.dirname(p) == self.here]

    def mkd(self, name):
        self.dirs.add(posixpath.join(self.here, name))

    def pwd(self):
        return self.here

    def storbinary(self, command, stream):
        self.files[posixpath.join(self.here, command[5:])] = stream.read()

    def retrbinary(self, command, callback):
        body = self.files[posixpath.join(self.here, command[5:])]
        callback(b'corrupt' if self.corrupt else body)

    def rename(self, source, target):
        self.renames.append((source, target))
        self.files[posixpath.join(self.here, target)] = self.files.pop(posixpath.join(self.here, source))

    def mlsd(self):
        return [(posixpath.basename(p), {'type': 'dir' if p in self.dirs else 'file',
                                       'modify': '20000101000000'})
                for p in self.dirs | set(self.files) if p != self.here and posixpath.dirname(p) == self.here]

    def delete(self, name):
        del self.files[posixpath.join(self.here, name)]

    def rmd(self, name):
        target = posixpath.join(self.here, name)
        if any(p.startswith(target + '/') for p in self.dirs | set(self.files)):
            raise error_perm('550 Directory not empty')
        self.dirs.remove(target)


class FeedPublishTests(unittest.TestCase):
    def test_remote_retention_preserves_protected_recent_and_unknown_contents(self):
        ftp = FakeFTP()
        for name in ('current', 'previous', 'old', 'recent', 'unknown'):
            for route, body in package(name, name).items():
                if not route.startswith('/releases/'):
                    continue
                if route.endswith('/manifest.json'):
                    manifest = json.loads(body)
                    manifest['generated_at'] = ('2026-09-28' if name == 'recent' else '2000-01-01') + 'T00:00:00+00:00'
                    body = json.dumps(manifest).encode()
                target = TARGET + route
                ftp.files[target] = body
                parent = posixpath.dirname(target)
                while parent != '/':
                    ftp.dirs.add(parent)
                    parent = posixpath.dirname(parent)
        ftp.files[TARGET + '/releases/unknown/keep.txt'] = b'unrelated'
        removed = prune_remote(ftp, {'current', 'previous'}, datetime(2026, 9, 28, 20, tzinfo=timezone.utc))
        self.assertEqual(removed, ['old'])
        for name in ('current', 'previous', 'recent', 'unknown'):
            self.assertIn(TARGET + '/releases/' + name + '/manifest.json', ftp.files)
        self.assertEqual(ftp.files[TARGET + '/latest.json'], b'old')

    def test_upload_checks_contents_before_replacing_pointer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            content = root / 'releases/content-test/content'
            content.mkdir(parents=True)
            (content / 'slide.html').write_bytes(b'example')
            (content.parent / 'manifest.json').write_bytes(b'{}')
            pointer = json.dumps({'release_id': 'content-test'}).encode()
            (root / 'latest.json').write_bytes(pointer)
            broken = FakeFTP(corrupt=True)
            with self.assertRaises(ValueError):
                upload(broken, root)
            self.assertEqual(broken.files[TARGET + '/latest.json'], b'old')
            self.assertEqual(broken.renames, [])
            good = FakeFTP()
            self.assertEqual(upload(good, root), 'content-test')
            self.assertEqual(good.files[TARGET + '/latest.json'], pointer)
            self.assertTrue(all(p.startswith(TARGET + '/') for p in good.files))
            self.assertEqual(good.renames, [('latest.json.uploading', 'latest.json')])
            absent = FakeFTP()
            absent.dirs.remove(TARGET)
            with self.assertRaises(error_perm):
                upload(absent, root)
            self.assertEqual(absent.renames, [])

    def test_snapshot_rejects_concurrent_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            for name in FOLDERS:
                (source / name).mkdir(parents=True)
            (source / 'data/input.json').write_text('{}')
            snapshot(source, root / 'copy')
            self.assertEqual((root / 'copy/data/input.json').read_text(), '{}')
            with patch('player.publish_feed.inventory', side_effect=[{'a': 'old'}, {'a': 'old'}, {'a': 'new'}]):
                with self.assertRaises(ValueError):
                    snapshot(source, root / 'changed')


if __name__ == '__main__':
    unittest.main()
