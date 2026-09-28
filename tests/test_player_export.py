from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from player.export_feed import Export
from player.package_test.activate_real import activate
from player.package_test.server import PackageServer
from player.update_test.updater import Store

ROOT = Path(__file__).resolve().parents[1]


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        (self.root / 'data').mkdir()
        shutil.copytree(ROOT / 'templates', self.root / 'templates')
        shutil.copytree(ROOT / 'static', self.root / 'static')
        images = self.root / 'resources/images'
        images.mkdir(parents=True)
        for name in ('logo.png', 'hintergrund.png', 'menue_wochenschmankerl.png', 'menue_tag.png'):
            shutil.copyfile(ROOT / 'resources/images' / name, images / name)
        self.now = datetime(2026, 9, 28, 12, tzinfo=timezone(timedelta(hours=2)))

    def data(self, name, value):
        (self.root / 'data' / name).write_text(json.dumps(value), encoding='utf-8')

    def export(self):
        return Export(self.root, self.now, self.now + timedelta(hours=4)).collect()

    def events(self, count):
        return [{'title': f'Termin {i}', 'date': '2026-10-01'} for i in range(count)]

    def test_variable_event_counts_zero_two_six(self):
        for count in (0, 2, 6):
            with self.subTest(count=count):
                self.data('termine.json', {'status': 'ok', 'events': self.events(count)})
                result = self.export()
                self.assertEqual(len(result.playlist), count)
                self.assertFalse(any('fallback' in p['path'] for p in result.playlist))
                for name, body in result.files.items():
                    if name.endswith('.html'):
                        self.assertNotIn(b'<script>', body)
                        self.assertIn(b'-inline-1.js', body)

    def test_one_broken_event_does_not_remove_other_events(self):
        events = self.events(3)
        events[1]['image_path'] = '/auszeit-display/resources/termine/missing.png'
        self.data('termine.json', {'status': 'ok', 'events': events})
        self.assertEqual([p['id'] for p in self.export().playlist], ['termin-1', 'termin-3'])

    def test_missing_weekly_special_never_renders_menu_fallback(self):
        data = {'status': 'ok', 'period': {'start_date': '2026-09-28', 'end_date': '2026-10-02'},
                'days': [], 'has_weekly_special': False}
        self.data('menue.json', data)
        self.assertEqual(self.export().playlist, [])
        data.update(has_weekly_special=True, weekly_special={'title': 'Kürbisgulasch'})
        self.data('menue.json', data)
        self.assertEqual([p['id'] for p in self.export().playlist], ['menue-weekly'])

    def test_missing_names_old_news_and_old_html_are_not_used(self):
        self.data('namenstage.json', {'09-28': []})
        self.data('news.json', {'updated': '27.09.2026 12:00', 'items': [{'title': 'Old news'}]})
        old = self.root / 'pages/termine/termin-999.html'
        old.parent.mkdir(parents=True)
        old.write_text('<h1>Old event</h1>')
        self.assertEqual(self.export().playlist, [])

    def test_expired_event_and_external_image_are_omitted(self):
        events = self.events(3)
        events[0]['date'] = '2026-09-27'
        events[1]['image_path'] = 'https://example.org/picture.png'
        self.data('termine.json', {'status': 'ok', 'events': events})
        self.assertEqual([p['id'] for p in self.export().playlist], ['termin-3'])

    def test_empty_release_replaces_old_playlist_and_survives_restart(self):
        self.data('termine.json', {'status': 'ok', 'events': self.events(2)})
        full = self.export()
        full.write(Path(self.temp.name) / 'full')
        store = Path(self.temp.name) / 'store'
        activate(Path(self.temp.name) / 'full', store)
        self.data('termine.json', {'status': 'ok', 'events': []})
        empty = self.export()
        empty.write(Path(self.temp.name) / 'empty')
        activate(Path(self.temp.name) / 'empty', store)
        with PackageServer(('127.0.0.1', 0), store) as server:
            state = server.state(self.now, 0)
            self.assertIsNone(state['slide'])
            self.assertEqual(state['state'], 'fallback')
            Store(store).verify(**Store(store).state()['active'])

    def test_existing_output_is_never_overwritten(self):
        output = Path(self.temp.name) / 'feed'
        self.export().write(output)
        before = (output / 'latest.json').read_bytes()
        with self.assertRaises(FileExistsError):
            self.export().write(output)
        self.assertEqual((output / 'latest.json').read_bytes(), before)

    def test_daily_menu_switches_at_14_and_missing_tomorrow_is_not_replaced(self):
        from player.local_test.server import Playlist
        data = {'status': 'ok', 'period': {'start_date': '2026-09-28', 'end_date': '2026-10-02'},
                'days': [{'date': '2026-09-28', 'title': 'Heute'}, {'date': '2026-09-29', 'title': 'Morgen'}]}
        self.data('menue.json', data)
        result = self.export()
        entries = [p for p in result.playlist if p['id'] in ('menue-today', 'menue-tomorrow')]
        self.assertEqual(len(entries), 2)
        playlist = Playlist(entries, allowed_paths=result.files)
        self.assertEqual(playlist.select(self.now.replace(hour=13, minute=59), 0)['id'], 'menue-today')
        self.assertEqual(playlist.select(self.now.replace(hour=14), 1)['id'], 'menue-tomorrow')
        data['days'].pop()
        self.data('menue.json', data)
        self.assertNotIn('menue-tomorrow', [p['id'] for p in self.export().playlist])

    def test_menu_switch_uses_vienna_winter_offset_after_clock_change(self):
        from zoneinfo import ZoneInfo
        self.now = datetime(2026, 10, 25, 1, tzinfo=ZoneInfo('Europe/Vienna'))
        self.data('menue.json', {'status': 'ok',
            'period': {'start_date': '2026-10-25', 'end_date': '2026-10-26'},
            'days': [{'date': '2026-10-25', 'title': 'Heute'}, {'date': '2026-10-26', 'title': 'Morgen'}]})
        result = Export(self.root, self.now, self.now + timedelta(days=1)).collect()
        today = next(p for p in result.playlist if p['id'] == 'menue-today')
        tomorrow = next(p for p in result.playlist if p['id'] == 'menue-tomorrow')
        self.assertEqual(today['valid_until'], '2026-10-25T14:00:00+01:00')
        self.assertEqual(tomorrow['valid_from'], today['valid_until'])
