import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from player.update_test.exercise import package
from player.update_test.updater import Store


class CleanupTests(unittest.TestCase):
    def test_nested_link_guard_prevents_recursive_deletion(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(temporary)
            folder = store.releases / '.staging-old'
            folder.mkdir()
            (folder / 'link').write_text('guard')
            os.utime(folder, (0, 0))
            original = Path.is_symlink
            with patch.object(Path, 'is_symlink', lambda path: path.name == 'link' or original(path)):
                self.assertEqual(store.prune('displayed', now=100000), [])
            self.assertTrue((folder / 'link').exists())

    def test_retains_active_previous_displayed_and_recent(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(temporary)
            for name in ('active', 'previous', 'displayed', 'old', 'recent'):
                for route, body in package(name, name).items():
                    if '/releases/' not in route:
                        continue
                    path = store.root / route.lstrip('/')
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(body)
                os.utime(store.releases / name, (0, 0))
            os.utime(store.releases / 'recent', (99999, 99999))
            (store.root / 'active.json').write_text(json.dumps({
                'active': {'release_id': 'active'}, 'previous': {'release_id': 'previous'}}))
            for name in ('.staging-old', '.staging-new', 'unrelated'):
                (store.releases / name).mkdir()
                os.utime(store.releases / name, (0, 0))
            os.utime(store.releases / '.staging-new', (99999, 99999))
            self.assertEqual(store.prune('displayed', now=100000), ['.staging-old', 'old'])
            self.assertEqual({p.name for p in store.releases.iterdir()},
                             {'active', 'previous', 'displayed', 'recent', '.staging-new', 'unrelated'})

    def test_invalid_protection_aborts_without_deleting(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(temporary)
            pending = store.releases / '.staging-old'
            pending.mkdir()
            os.utime(pending, (0, 0))
            (store.root / 'active.json').write_text(json.dumps({
                'active': {'release_id': '../escape'}, 'previous': None}))
            with self.assertRaises(ValueError):
                store.prune('displayed', now=100000)
            self.assertTrue(pending.exists())

    def test_link_outside_store_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = Store(root / 'store')
            outside = root / 'outside'
            outside.mkdir()
            (outside / 'keep').write_text('keep')
            link = store.releases / '.staging-link'
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('Directory symlinks not permitted on this host')
            self.assertEqual(store.prune('displayed', now=10**12), [])
            self.assertEqual((outside / 'keep').read_text(), 'keep')
