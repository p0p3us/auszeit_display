"""Build a link inventory from the actual staged export, including variable events."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
from urllib.parse import quote


def build_index(export_dir: Path) -> str:
    links = []
    for path in sorted(export_dir.rglob('*.html')):
        relative = path.relative_to(export_dir).as_posix()
        if relative == 'index.html':
            continue
        links.append(f'<li><a href="{quote(relative)}">{escape(relative)}</a></li>')
    return ('<!doctype html>\n<html lang="de"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Auszeit – öffentliche Seiten</title>'
            '<h1>Öffentliche Auszeit-Seiten</h1>'
            '<p>Automatisch aus dem aktuellen Export erstellt. '
            'Indexseiten sind Linkverzeichnisse, keine TV-Folien. '
            'Termin-Nummern können sich mit dem Veranstaltungskalender ändern.</p><ul>\n'
            + '\n'.join(links) + '\n</ul></html>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export_dir', type=Path)
    args = parser.parse_args()
    if not args.export_dir.is_dir():
        parser.error('Export directory does not exist')
    (args.export_dir/'index.html').write_text(build_index(args.export_dir), encoding='utf-8')


if __name__ == '__main__':
    main()
