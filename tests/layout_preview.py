"""Browser regression fixtures. Run with the project Python, then open localhost:8765.

No generators write to production data/pages. Optional --snapshots DIR adds saved
public HTML, using the current local styles and layout script for comparison.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
import mimetypes
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.export_menue import FALLBACKS
from scripts.generate_zitat import lebensdaten
from scripts.generate_weather import enrich_deluxe, icon_path


def build_cases(snapshots: Path | None = None) -> dict[str, str]:
    env = Environment(loader=FileSystemLoader(ROOT / 'templates/display_pages'),
                      autoescape=select_autoescape(['html']))
    cases = {}
    cases['system-default'] = (ROOT/'pages/system/default.html').read_text(encoding='utf-8')

    def add(name, template, **context):
        cases[name] = env.get_template(template).render(**context)

    dishes = [
        ('Gebratener Leberkäse', 'mit Spiegelei und Fisolen-Erdäpfelgröstl'),
        ('Gebackene Pußta-Laibchen', 'mit Knoblauchsauce und Pommes Frites'),
        ('Puten Champignongeschnetzeltes', 'mit Spiralen'),
        ('Wiener Schnitzel', 'mit gemischtem Salat'),
    ]
    days = [dict(weekday=weekday, date_text=f'{22+i}. September',
                 full_date_text=f'{weekday}, {22+i}. September 2026',
                 soup='Tagessuppe', title=title, description=description, price='10,50')
            for i, (weekday, (title, description)) in enumerate(zip(
                ['Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag'], dishes))]
    add('menu-overview', 'menue_uebersicht.html', page_title='Mittagsmenü',
        days=days, period_text='22. bis 25. September 2026')
    for mode in ('today', 'tomorrow'):
        add('menu-'+mode, 'menue_tag.html', menu=days[2], time_mode=mode,
            page_title='Das heutige Mittagsmenü' if mode == 'today' else 'Das morgige Mittagsmenü')
    add('menu-weekly', 'menue_wochenschmankerl.html', page_title='Wochenschmankerl',
        special=dict(title='Gebratenes Zanderfilet auf Kürbisrisotto',
                     description='mit gerösteten Kürbiskernen, frischen Kräutern und gemischtem Salat', price='18,90'),
        period_text='22. bis 25. September 2026')
    for key, template in [('overview', 'menue_uebersicht.html'), ('weekly', 'menue_wochenschmankerl.html'),
                          ('today', 'menue_tag.html'), ('tomorrow', 'menue_tag.html')]:
        add('fallback-'+key, template, is_fallback=True, fallback=FALLBACKS[key], page_title='Mittagsmenü')
    for photo in (False, True):
        add('news-long-'+str(photo), 'news_item.html', source='Niederösterreich', published='23.09.2026 11:00',
            title='Neue Entwicklungen in Niederösterreich: Gemeinden beraten über gemeinsame Maßnahmen für die kommenden Monate',
            description=('Vertreterinnen und Vertreter der Gemeinden diskutieren heute über die nächsten Schritte. '
                         'Dabei stehen die Anliegen der Bevölkerung und die Zusammenarbeit in der Region im Mittelpunkt. '
                         'Weitere Einzelheiten sollen nach Abschluss der Gespräche bekannt gegeben werden.'),
            image_path='/auszeit-display/resources/news/test.png' if photo else '/auszeit-display/resources/images/news.png')
    add('event-long', 'termin.html', event=dict(title='Ein besonderer Abend mit Musik und Unterhaltung',
        date_text='Donnerstag, 24. September 2026', time='19:00',
        description='Gemeinsam genießen wir einen unterhaltsamen Abend.\nLive-Musik, gute Gespräche und Spezialitäten aus unserer Küche.\nWir freuen uns auf Ihren Besuch!',
        price='€ 24,50 pro Person inklusive Begrüßungsgetränk',
        reservation='Reservierung unbedingt erforderlich – bitte direkt im Café anmelden.'))
    for index, text in enumerate(json.loads((ROOT/'data/weisheiten.json').read_text(encoding='utf-8'))['weisheiten']):
        add(f'weisheit-{index:03}', 'weisheit.html', weisheit=text, weisheit_lines=text.splitlines())
    for index, entry in enumerate(json.loads((ROOT/'data/zitate.json').read_text(encoding='utf-8'))['zitate']):
        add(f'zitat-{index:03}', 'zitat.html', zitat=entry, lebensdaten=lebensdaten(entry))
    names = json.loads((ROOT/'data/namenstage.json').read_text(encoding='utf-8'))
    # Include all distinct name lists, not just today's short example.
    for index, values in enumerate(names.values()):
        if isinstance(values, list):
            add(f'namenstag-{index:03}', 'namenstag.html', names=values, date_text='30. September 2026')
    rules = json.loads((ROOT/'data/bauernregeln.json').read_text(encoding='utf-8'))
    for month, entries in rules.items():
        for day, texts in entries.items():
            for index, text in enumerate(texts):
                add(f'bauernregel-{month}-{day}-{index}', 'bauernregel.html', headline='Bauernregel',
                    date_text='30. September 2026', regel=text, zusatz=f'Quelle: {month} {day}')
    weather = json.loads((ROOT/'data/weather.json').read_text(encoding='utf-8'))
    for description, temperature in [('Leichter Regen', 18), ('Mäßiger Schneefall', -12), ('Überwiegend bewölkt', 34)]:
        day = dict(weather['tomorrow'], description=description, temp_max=temperature,
                   temp_min=temperature-5, icon_path=icon_path('04d'), wind_kmh=120, rain_probability=100)
        common = dict(location='Siedlung Maria Theresia', updated='23.09.2026 11:00')
        add(f'weather-{temperature}', 'weather_tomorrow.html', day=day, **common)
        add(f'weather-deluxe-{temperature}', 'weather_tomorrow_deluxe.html', day=enrich_deluxe(day), **common)
        add(f'weather-five-{temperature}', 'weather_5days.html', days=[day]*5, **common)
    if snapshots:
        for path in sorted(snapshots.rglob('*.html')):
            source = path.read_text(encoding='utf-8')
            if path.parent.name in ('weisheit', 'zitat'):
                source = re.sub(r'<script>.*?</script>', '', source, flags=re.S)
            source = source.replace('</head>', '<script defer src="/auszeit-display/static/js/display_layout.js"></script></head>')
            # Do not pair current headlines with an old local image cache.
            source = re.sub(r'src="(/auszeit-display/resources/(?:news|termine)/[^"]+)"',
                            r'src="https://populorum.eu\1"', source)
            cases['live-'+path.relative_to(snapshots).as_posix().replace('/', '-')] = source
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshots', type=Path)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    cases = build_cases(args.snapshots)
    harness = (ROOT/'tests/layout_runner.html').read_text(encoding='utf-8').replace('__CASES__', json.dumps(list(cases)))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path == '/':
                content, mime = harness.encode('utf-8'), 'text/html; charset=utf-8'
            elif path.startswith('/case/') and path[6:] in cases:
                content, mime = cases[path[6:]].encode('utf-8'), 'text/html; charset=utf-8'
            elif path.startswith('/auszeit-display/'):
                relative = path.removeprefix('/auszeit-display/')
                asset = (ROOT/relative).resolve()
                if not asset.is_relative_to(ROOT) or relative.split('/')[0] not in ('static', 'resources'):
                    self.send_error(404)
                    return
                if not asset.is_file():
                    # Public snapshot images may be newer than the local cache.
                    self.send_response(302)
                    self.send_header('Location', 'https://populorum.eu'+path)
                    self.end_headers()
                    return
                content, mime = asset.read_bytes(), mimetypes.guess_type(asset)[0] or 'application/octet-stream'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_):
            pass

    print(f'{len(cases)} cases: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
