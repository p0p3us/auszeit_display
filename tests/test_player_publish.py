from ftplib import error_perm
import json
from pathlib import Path
import posixpath
import tempfile
import unittest
from unittest.mock import patch

from player.publish_feed import FOLDERS, TARGET, snapshot, upload


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


class FeedPublishTests(unittest.TestCase):
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
