"""Local package export from an immutable source snapshot. Never publishes or fetches."""
import argparse
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, select_autoescape
from scripts import export_menue as menu
from scripts import generate_bauernregel as rules
from scripts import generate_weather as weather
from scripts.generate_termine import format_date
from scripts.generate_zitat import lebensdaten
from player.update_test.updater import digest, valid_path, validate_manifest, require


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        require(tag not in ('iframe', 'object', 'embed', 'base'), 'Unsupported embedded content')
        require('srcset' not in attrs and 'style' not in attrs, 'Unsupported inline asset syntax')
        if 'src' in attrs:
            self.urls.append(attrs['src'])
        if tag == 'link' and 'href' in attrs:
            self.urls.append(attrs['href'])


def resolve(source, reference):
    parts = urlsplit(reference)
    require(not parts.scheme and not parts.netloc and not parts.query and not parts.fragment,
            'Only local, unversioned asset paths are supported')
    target = (parts.path.lstrip('/') if parts.path.startswith('/') else
              posixpath.normpath(posixpath.join(posixpath.dirname(source), parts.path)))
    valid_path(target)
    require(target.startswith('auszeit-display/'), 'Asset outside package')
    return target


def dependencies(root, page, html):
    """Fail a whole slide when any static dependency is missing; no broken-image slide."""
    pending = {page: html.encode()}
    result = {}
    # Current event template has one inline layout script. Externalize only in copy.
    counter = 0

    def script(match):
        nonlocal counter
        counter += 1
        name = page[:-5] + f'-inline-{counter}.js'
        pending[name] = match.group(1).encode()
        return f'<script src="{posixpath.basename(name)}"></script>'
    pending[page] = re.sub(r'<script>\s*([\s\S]*?)</script>', script, html).encode()
    while pending:
        name, body = pending.popitem()
        if name in result:
            continue
        references = []
        text = None
        if name.endswith(('.html', '.css')):
            text = body.decode('utf-8')
            if name.endswith('.html'):
                parser = References()
                parser.feed(text)
                references = parser.urls
            else:
                require('@import' not in text, 'CSS imports require explicit support')
                references = re.findall(r'url\([\'"]?([^\)\'\"]+)', text)
            for reference in references:
                target = resolve(name, reference)
                if target not in result and target not in pending:
                    local = (root / target.removeprefix('auszeit-display/')).resolve()
                    require(local.is_relative_to(root), 'Asset escapes source snapshot')
                    pending[target] = local.read_bytes()
                text = text.replace(reference, posixpath.relpath(target, posixpath.dirname(name)))
            body = text.encode()
        result[name] = body
    return result


class Export:
    def __init__(self, root, now, expires, menu_switch=time(14)):
        self.root = Path(root).resolve()
        require(now.tzinfo is not None and expires.tzinfo is not None and now < expires,
                'Explicit timezone and a future expiry are required')
        self.now, self.expires = now, expires
        self.day = now.date()
        self.menu_switch = menu_switch
        self.env = Environment(loader=FileSystemLoader(self.root / 'templates/display_pages'),
                               autoescape=select_autoescape(['html', 'xml']))
        self.files, self.playlist, self.omitted = {}, [], []

    def data(self, name):
        return json.loads((self.root / 'data' / name).read_text(encoding='utf-8'))

    def attempt(self, name, action):
        try:
            action()
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
            self.omitted.append({'id': name, 'reason': str(error)})

    def add(self, name, template, context, until=None, begin=None):
        from jinja2 import TemplateError
        try:
            path = f'auszeit-display/{name}/index.html'
            html = self.env.get_template(template).render(**context)
            require(bool(html.strip()), 'Empty rendered slide')
            files = dependencies(self.root, path, html)
            deadline = min(self.expires, until or self.expires)
            begin = begin or self.now
            require(begin < deadline, 'Slide expired or outside package validity')
            entry = {'id': name, 'path': path, 'duration_seconds': 20,
                     'valid_from': begin.isoformat(), 'valid_until': deadline.isoformat()}
            self.files.update(files)
            self.playlist.append(entry)
        except (OSError, ValueError, KeyError, TypeError, TemplateError) as error:
            self.omitted.append({'id': name, 'reason': str(error)})

    def midnight(self, day):
        return datetime.combine(day, time(), self.now.tzinfo)

    def daily(self):
        end = self.midnight(self.day + timedelta(days=1))
        common = {'date_text': self.now.strftime('%d.%m.%Y'), 'updated_text': self.now.isoformat(), 'hostname': ''}

        def names():
            values = self.data('namenstage.json').get(self.day.strftime('%m-%d'))
            require(isinstance(values, list) and bool(values) and all(isinstance(v, str) and v.strip() for v in values), 'No names')
            self.add('namenstag', 'namenstag.html', common | {'names': values}, end)
        self.attempt('namenstag', names)

        def rule():
            text, label = rules.get_rule_for_date(self.data('bauernregeln.json'), self.now)
            require(isinstance(text, str) and bool(text.strip()), 'No rule')
            self.add('bauernregel', 'bauernregel.html', common | {'headline': 'Bauernregel', 'regel': text, 'zusatz': label}, end)
        self.attempt('bauernregel', rule)

        def wisdom():
            items = self.data('weisheiten.json')['weisheiten']
            require(isinstance(items, list) and bool(items), 'No wisdom')
            text = items[self.day.toordinal() % len(items)]
            require(isinstance(text, str) and bool(text.strip()), 'Empty wisdom')
            self.add('weisheit', 'weisheit.html', common | {'weisheit': text, 'weisheit_lines': text.splitlines()}, end)
        self.attempt('weisheit', wisdom)

        def quote():
            items = self.data('zitate.json')['zitate']
            require(isinstance(items, list) and bool(items), 'No quotes')
            item = items[self.day.toordinal() % len(items)]
            require(all(isinstance(item.get(key), str) and item[key].strip() for key in ('text', 'autor', 'bild')), 'Incomplete quote')
            self.add('zitat', 'zitat.html', {'zitat': item, 'lebensdaten': lebensdaten(item)}, end)
        self.attempt('zitat', quote)

    def menus(self):
        data = self.data('menue.json')
        require(data.get('status') == 'ok', 'No valid menu data')
        # The source period is authoritative; an old file never becomes today's menu.
        start = date.fromisoformat(data['period']['start_date'])
        end = date.fromisoformat(data['period']['end_date'])
        current = start <= self.day <= end
        require(current or start == self.day + timedelta(days=1), 'Menu period not current')
        days = menu.get_valid_days(data)
        period = menu.format_period(start, end)
        deadline = self.midnight(end + timedelta(days=1))
        if current and days:
            self.add('menue-overview', menu.OVERVIEW_TEMPLATE,
                     {'is_fallback': False, 'days': days, 'period_text': period}, deadline)
        special = menu.get_weekly_special(data)
        if current and special:
            self.add('menue-weekly', menu.WEEKLY_TEMPLATE,
                     {'is_fallback': False, 'special': special, 'period_text': period}, deadline)
        elif current:
            self.omitted.append({'id': 'menue-weekly', 'reason': 'No weekly special'})
        if self.menu_switch is None:
            self.omitted.append({'id': 'menue-daily', 'reason': 'Menu switching hour not configured'})
            return
        switch = datetime.combine(self.day, self.menu_switch, self.now.tzinfo)
        for mode, day, begin, until in (
                ('today', self.day, self.now, switch),
                ('tomorrow', self.day + timedelta(days=1), max(self.now, switch), self.midnight(self.day + timedelta(days=1)))):
            entry = menu.find_menu_for_date(days, day)
            if entry and start <= day <= end:
                self.add('menue-' + mode, menu.DAY_TEMPLATE,
                         {'is_fallback': False, 'menu': entry, 'time_mode': mode}, until, begin)

    def events(self):
        data = self.data('termine.json')
        require(data.get('status') == 'ok' and isinstance(data.get('events'), list), 'No valid events')
        for number, event in enumerate(data['events'], 1):
            name = f'termin-{number}'
            def one(event=event, name=name):
                require(isinstance(event.get('title'), str) and bool(event['title'].strip()), 'Missing event title')
                day = date.fromisoformat(event['date'])
                self.add(name, 'termin.html', {'event': event | {'date_text': format_date(event['date'])}},
                         self.midnight(day + timedelta(days=1)))
            self.attempt(name, one)

    def news(self):
        data = self.data('news.json')
        require(datetime.strptime(data['updated'], '%d.%m.%Y %H:%M').date() == self.day, 'News source is not current')
        for number, item in enumerate(data['items'], 1):
            name = f'news-{number}'
            def one(item=item, name=name):
                require(isinstance(item.get('title'), str) and bool(item['title'].strip()), 'No news title')
                self.add(name, 'news_item.html', {'source': item.get('source', ''), 'title': item['title'],
                    'description': item.get('description', ''), 'published': item.get('published', ''),
                    'date_text': self.day.isoformat(), 'image_path': item.get('image_path') or '/auszeit-display/resources/images/news.png'},
                    self.midnight(self.day + timedelta(days=1)))
            self.attempt(name, one)

    def forecast(self):
        data = self.data('weather.json')
        require(datetime.strptime(data['updated'], '%d.%m.%Y %H:%M').date() == self.day, 'Weather source is not current')
        tomorrow = self.day + timedelta(days=1)
        def one():
            day = data['tomorrow']
            require(date.fromisoformat(day['date']) == tomorrow, 'Wrong tomorrow forecast date')
            day = day | {'icon_path': weather.icon_path(day.get('icon_code', ''))}
            until = self.midnight(tomorrow)
            self.add('weather-tomorrow', 'weather_tomorrow.html', {'location': data.get('location', ''), 'day': day}, until)
            self.add('weather-deluxe', 'weather_tomorrow_deluxe.html', {'location': data.get('location', ''), 'day': weather.enrich_deluxe(day)}, until)
        self.attempt('weather-tomorrow', one)
        def five():
            days = data['five_days']
            require(isinstance(days, list) and len(days) == 5 and all(date.fromisoformat(d['date']) > self.day for d in days), 'Incomplete or old five-day forecast')
            days = [d | {'icon_path': weather.icon_path(d.get('icon_code', ''))} for d in days]
            self.add('weather-5days', 'weather_5days.html', {'location': data.get('location', ''), 'days': days}, self.midnight(tomorrow))
        self.attempt('weather-5days', five)

    def collect(self):
        self.daily()
        for name, action in (('menue', self.menus), ('termine', self.events), ('news', self.news), ('weather', self.forecast)):
            self.attempt(name, action)
        return self

    def write(self, destination):
        manifest = {'schema_version': 1, 'release_id': 'pending', 'generated_at': self.now.isoformat(),
                    'timezone': 'Europe/Vienna', 'files': [{'path': path, 'bytes': len(body), 'sha256': digest(body)}
                    for path, body in sorted(self.files.items())], 'playlist': self.playlist}
        release = 'content-' + digest(json.dumps(manifest, sort_keys=True).encode())[:20]
        manifest['release_id'] = release
        validate_manifest(manifest, release)
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)
        # A new local output only; never replace a live feed in this preparation step.
        folder = destination / 'releases' / release
        folder.mkdir(parents=True)
        for path, body in self.files.items():
            target = folder / 'content' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        body = json.dumps(manifest).encode()
        (folder / 'manifest.json').write_bytes(body)
        (destination / 'report.json').write_text(json.dumps({'included': [p['id'] for p in self.playlist], 'omitted': self.omitted}, ensure_ascii=False, indent=2), encoding='utf-8')
        (destination / 'latest.json').write_text(json.dumps({'schema_version': 1, 'release_id': release,
            'manifest_path': f'releases/{release}/manifest.json', 'manifest_sha256': digest(body)}), encoding='utf-8')
        return manifest


def main():
    from zoneinfo import ZoneInfo
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True, help='Immutable source copy, not a concurrently updated production tree')
    parser.add_argument('--output', type=Path, required=True, help='New, separate output directory')
    parser.add_argument('--expires-at', required=True, help='Explicit ISO timestamp with timezone; provisional maximum validity')
    parser.add_argument('--menu-switch-at', type=time.fromisoformat, default=time(14), help='Local switching time, agreed default 14:00')
    args = parser.parse_args()
    now = datetime.now(ZoneInfo('Europe/Vienna'))
    export = Export(args.snapshot, now, datetime.fromisoformat(args.expires_at), args.menu_switch_at).collect()
    manifest = export.write(args.output)
    print(f"{len(manifest['playlist'])} Folien; {len(export.omitted)} ausgelassen. Details: {args.output / 'report.json'}")


if __name__ == '__main__':
    main()
