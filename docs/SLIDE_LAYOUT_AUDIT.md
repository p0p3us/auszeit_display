# Folien- und CSS-Prüfung vom 23. September 2026

## Bestand und fehlende Links

Die übergebene Liste enthält 22 Inhaltsfolien. Der Abgleich mit den Generatoren,
`data/news_sources.json`, dem öffentlichen News-Index und der öffentlichen
Terminquelle `https://populorum.eu/menu_admin/data/termine/aktuell.json` ergibt
zum Prüfzeitpunkt **24 Inhaltsfolien**:

| Gruppe | Öffentlicher Pfad unter `https://populorum.eu/auszeit-display/` | Anzahl |
| --- | --- | ---: |
| News | `news/niederoesterreich-1.html`, `news/niederoesterreich-2.html`, `news/science-1.html`, `news/science-2.html`, `news/sport-1.html`, `news/sport-2.html`, `news/help-1.html`, `news/help-2.html` | 8 |
| Tagesinhalte | `bauernregel/`, `weisheit/`, `namenstag/`, `zitat/` | 4 |
| Wetter | `weather/morgen.html`, `weather/5tage.html`, `weather/morgen-deluxe.html` | 3 |
| Menü | `menue/uebersicht.html`, `menue/heute.html`, `menue/morgen.html`, `menue/wochenschmankerl.html` | 4 |
| Termine | `termine/termin-1.html` bis `termine/termin-5.html` | 5 |

In der ursprünglichen Liste fehlen:

- [Wir schwanken Richtung Nationalfeiertag – 25. Oktober 2026](https://populorum.eu/auszeit-display/termine/termin-4.html)
- [Frühstücksbuffet – 31. Oktober 2026](https://populorum.eu/auszeit-display/termine/termin-5.html)

Zusätzlich werden [News-Index](https://populorum.eu/auszeit-display/news/) und
[Wetter-Index](https://populorum.eu/auszeit-display/weather/) erzeugt. Das sind
Linkverzeichnisse und keine Fernsehfolien. Der Wetter-Index enthielt bisher keinen
Link auf `morgen-deluxe.html`; dieser wird ergänzt.

Der öffentliche Export erzeugt nun auch ein [vollständiges Linkverzeichnis](https://populorum.eu/auszeit-display/)
aus den tatsächlich im Staging vorhandenen HTML-Dateien. Mit obigem Bestand sind
das insgesamt 27 HTML-Seiten einschließlich aller drei Verzeichnisse. Dieser neue
Index ist erst nach Übernahme und Veröffentlichung der Änderungen verfügbar.

Termin-Nummern sind **keine dauerhaften Veranstaltungs-IDs**: Der Generator
nummeriert die jeweils aktuellen Termine neu. Künftig können weitere Nummern
hinzukommen oder entfallen. News-Quellen erzeugen derzeit je zwei Folien.

Nur lokal, nicht im öffentlichen Export: `pages/system/default.html`,
`pages/upload/*.html` (aktuell eine ungestaltete Testseite) und die Flask-Ansicht
`/display`. Die Standardfolie nutzt ebenfalls die Skalierung. Beliebige
hochgeladene HTML-Dateien haben eigenes Layout und werden nicht automatisch
umgestaltet. `templates/display_pages/news.html` ist nicht das vom aktuellen
News-Generator verwendete Template; dieser verwendet `news_item.html`.

## Befunde und Korrekturen

- **Wochenmenü:** 72-px-Gerichtsnamen und 40-px-Beilagen liefen über die festen
  Kartenhöhen. Zentrierung bei Übergröße schob Text nach oben über die Tageszeile.
  Nun stehen 48-px-Gerichtsnamen, 30-px-Beilagen und Preise in getrennten Bereichen;
  der Inhalt beginnt oben und wird bei Bedarf weiter angepasst.
- **Tagesmenü:** Einzeilig erzwungene lange Hauptüberschriften überschritten die
  Textbreite; beim morgigen Gericht reichten Preis/Fußtext über den unteren Rand.
  Überschriften dürfen umbrechen, Abstände sind reduziert, die gesamte Textgruppe
  hat ein festes verfügbares Höhenbudget.
- **News:** Mehrere aktuelle Meldungen erreichten den unteren Sicherheitsrand;
  `help-2.html` lief bei Full HD tatsächlich über das Bild hinaus. Kompaktere
  Metadaten und eine größenabhängige Anpassung halten Überschrift und Meldung zusammen.
- **Wetter:** Die Aktualisierung der einfachen Morgenfolie war zu tief. Beim
  Deluxe-Wetter waren Empfehlung und Aktualisierung abgeschnitten. Abstände,
  Überschrift und Textanpassung berücksichtigen nun die verfügbare Höhe.
- **Bauernregel, Namenstag, Weisheit, Zitat:** Prüfung wechselnder Inhalte statt
  nur des aktuellen Tages. Gemeinsame Anpassung berücksichtigt auch Zusatz- und
  Autorentexte. Bewusste Zeilen der Weisheiten bleiben erhalten.
- **Termine:** Lange zweizeilige Titel konnten trotz vorhandener Größenanpassung
  an der Titelbox angeschnitten sein. Mehr Zeilenhöhe und Platz für Ober-/Unterlängen
  beheben das. Überlange Textgruppen werden nicht mehr nach oben zentriert.
- **Große Motivbilder:** Verkettete Schattenfilter führten bei Namenstag und
  Weisheit im skalierten Chromium-Bild zu einer komplett leeren Darstellung,
  obwohl die Textmaße korrekt waren. Auf der skalierten Arbeitsfläche entfallen
  diese zusätzlichen Motivfilter; die bereits in den Bildern enthaltenen
  Licht-/Schatteneffekte bleiben erhalten. Dieser Befund wurde per Screenshot
  erkannt und nach der Korrektur visuell überprüft.

`static/js/display_layout.js` hält eine logische Arbeitsfläche von **1920 × 1080**
und skaliert sie proportional in das Browserfenster. Abweichende Seitenverhältnisse
erhalten schmale Hintergrundränder. CSS-Viewportmaße beziehen sich innerhalb der
Folie auf diese Arbeitsfläche. So bleiben Pixelgrößen und viewportabhängige Maße
auch bei kleineren Fenstern konsistent.

Die Schriftanpassung verkleinert nur bei tatsächlichem Platzmangel, höchstens auf
60 Prozent der jeweiligen Ausgangsgrößen. Inhalte werden nicht gekürzt. Extrem
lange freie Eingaben sind damit nicht unbegrenzt darstellbar: verbleibende
Überläufe werden über `data-layout-overflow="true"` für den Layouttest sichtbar.

## Wiederholbare Prüfung

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/layout_preview.py
```

Danach `http://127.0.0.1:8765/?allSizes` öffnen. Die browserseitige Prüfung misst
Textgrenzen, verdeckte Überläufe und Textanpassungsgrenzen in 1920 × 1080,
1280 × 720 und 1736 × 969. Sie nutzt aktuelle Templates/CSS und verändert keine
Produktionsdaten. Enthalten sind alle 894 Bauernregeln, 71 Weisheiten, 52 Zitate,
366 Namenstagslisten, Menü-Beispiele aus dem gemeldeten Fehler, Ersatzanzeigen,
lange News-/Termintexte, neun Wetterfälle und die lokale Standardfolie.

Optional können gespeicherte öffentliche HTML-Seiten ergänzt werden:

```powershell
.\.venv\Scripts\python.exe tests/layout_preview.py --snapshots PFAD_ZU_HTML_KOPIEN
```

Die Kopien behalten ihre Inhalte, verwenden aber die lokalen Layoutdateien.
Bei Weisheit/Zitat ersetzt das gemeinsame Skript die alte eingebettete Anpassung.
Aktuelle News-/Terminbilder werden vom öffentlichen Server geladen, damit kein
veraltetes lokales Bild mit einer aktuellen Überschrift kombiniert wird.
Mit `&filter=menu` lässt sich die Testauswahl einschränken.

Ergebnis: 52 Python-Tests bestanden. Die erste vollständige Browsermatrix mit
1.425 Fällen × drei Größen meldete keine Überläufe; ergänzende Prüfungen deckten
die zwei nachträglich gefundenen Terminfolien, die Standardfolie sowie Änderungen
an Weisheit/Zitat und den Menüumbrüchen ab (ebenfalls ohne Überläufe).

Screenshots wurden ergänzend visuell kontrolliert. Die Browserprüfung ersetzt
keinen Lesbarkeitstest am realen Fernseher und keinen Hardwaretest am Anzeige-Pi.
Der Inhaltsserver erhält keine Browser- oder Kioskänderungen. Zur Übernahme werden
der Git-Stand und anschließend der reguläre öffentliche Export benötigt; CSS,
JavaScript und neu generierte HTML-Dateien müssen gemeinsam veröffentlicht werden.
