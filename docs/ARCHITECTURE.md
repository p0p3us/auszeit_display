# Auszeit Digital Signage – Architektur

Stand: September 2026

## Überblick

Das System besteht aus mehreren logisch getrennten Bereichen:

1. lokale Flask-Anwendung auf dem Raspberry Pi
2. Python-Generatoren und Datenabruf
3. generierte HTML-Digital-Signage-Folien
4. PHP-Webinterface auf dem Webserver
5. öffentlicher Export per FTP
6. Chromium-Kiosk-Anzeige auf dem Raspberry Pi

## Gesamtfluss

Vereinfacht:

Webinterface / externe Datenquellen
↓
Python-Fetch-Skripte
↓
lokale JSON-Daten
↓
Python-Generatoren
↓
HTML-Seiten unter pages/
↓
lokale Anzeige über Flask / Chromium
↓
optional öffentlicher Export
↓
FTP-Webserver

## Raspberry-Pi-Anwendung

Hauptanwendung:

app.py

Die Flask-Anwendung übernimmt unter anderem:

* lokale Administration
* Auswahl der aktiven Seite
* Statusanzeige
* Upload zusätzlicher HTML-Seiten
* Bereitstellung der Digital-Signage-Seiten
* Bereitstellung statischer Dateien und Ressourcen

Produktionsbasis:

/home/pi/auszeit_display

Wichtige Routen umfassen unter anderem:

* /admin
* /admin/upload
* /admin/set/...
* /admin/delete/...
* /status
* /display
* /pages/...
* /resources/...
* /auszeit-display/resources/...
* /auszeit-display/static/...

## Module

Python-Module liegen unter:

modules/

### display_state.py

Aufgabe:

* aktiven Displayzustand lesen
* aktiven Displayzustand speichern
* aktuelle Seite setzen

Persistenz:

data/display_state.json

### page_manager.py

Aufgabe:

* verfügbare HTML-Seiten unter pages/ finden
* Pfade validieren
* prüfen, ob eine Seite existiert

Sicherheitsrelevant:

* absolute Pfade werden abgelehnt
* ".." in Pfaden wird abgelehnt

### system_status.py

Aufgabe:

Systeminformationen des Raspberry Pi auslesen.

Beispiele:

* Root-Dateisystem
* USB-SSD
* USB-Geschwindigkeit
* Unterspannungsstatus
* Festplattenbelegung

Verwendete Linux-Kommandos:

* findmnt
* lsusb
* vcgencmd

Dieses Modul ist bewusst Raspberry-Pi-/Linux-spezifisch.

## Datenverzeichnis

Pfad:

data/

Hier liegen sowohl statische Datenquellen als auch erzeugte
Zwischen- und Statusdaten.

Beispiele:

* display_state.json
* weather.json
* news.json
* news_sources.json
* menue.json
* menue_source.json
* menue_status.json
* bauernregeln.json
* namenstage.json
* weisheiten.json
* zitate.json

Nicht jede Datei hat dieselbe Funktion.

Es muss unterschieden werden zwischen:

* statischen Quelldaten
* heruntergeladenen Daten
* normalisierten Daten
* Statusdateien

## Fetch-Schicht

Die Fetch-Skripte befinden sich unter:

scripts/

Sie lesen externe Datenquellen ein und normalisieren diese für
die weiteren Generatoren.

Beispiele:

* Wetter-API
* RSS-Feeds
* Menü-Webinterface
* Termin-Webinterface

Die Fetch-Schicht soll externe Datenformate von der
Darstellungslogik entkoppeln.

## Menü-Datenfluss

Webinterface:

webinterface/menu_admin.php

↓ speichert Menüstruktur

Webspace-Daten:

webinterface/data/menus/

↓ Abruf durch Raspberry Pi

scripts/fetch_menue.py

↓ erzeugt normalisierte lokale Daten

data/menue.json

↓ Verarbeitung

scripts/export_menue.py

↓ Templates

templates/display_pages/

↓ Ausgabe

pages/menue/

## Menüstruktur

Das aktuelle Menümodell enthält:

* Dienstag
* Mittwoch
* Donnerstag
* Freitag Menü 1
* optional Freitag Menü 2
* optional Wochenschmankerl
* Informationsblöcke

Das frühere Samstagsschmankerl ist Legacy und darf nicht wieder
als aktive Funktion eingeführt werden.

## Termin-Datenfluss

Webinterface
↓
webinterface/data/termine/
↓
Fetch-Skript
↓
normalisierte lokale Termindaten
↓
Termin-Generator
↓
Templates
↓
pages/termine/

Unterstützt werden:

* Einzeltermine
* Serientermine

Die generierten Folien enthalten abhängig von den Daten:

* Titel
* Datum
* Uhrzeit
* Beschreibung
* Preis / Eintritt
* Reservierungsinformation
* optionale Bilder

## News-Datenfluss

Konfiguration:

data/news_sources.json

↓ RSS-Abruf

News-Fetch-/Generatorlogik

↓ lokale Daten

data/news.json

↓ erzeugte Folien

pages/news/

↓ optionale heruntergeladene Bilder

resources/news/

## Wetter-Datenfluss

OpenWeather API
↓
Wetter-Fetch
↓
data/weather.json
↓
Wetter-Generator
↓
Wetter-Templates
↓
pages/weather/

Verwendete Symbolcodes orientieren sich an OpenWeather.

Die grafischen Wetter-Icons liegen als eigene Ressourcen im Projekt.

## Weisheit des Tages

Quelle:

data/weisheiten.json

Generator:

scripts/generate_weisheit.py

Template:

templates/display_pages/weisheit.html

CSS:

static/css/display_pages/weisheit.css

Ausgabe:

pages/weisheit/anzeige.html

## Zitat des Tages

Quelle:

data/zitate.json

Generator:

scripts/generate_zitat.py

Portraits:

resources/zitate/

Ausgabe:

pages/zitat/anzeige.html

Die Portraits sind grundsätzlich Schwarz-Weiß-Darstellungen.

## Namenstag

Quelle:

data/namenstage.json

Generator:

entsprechendes Skript unter scripts/

Ausgabe:

pages/namenstag/

## Bauernregel

Quelle:

data/bauernregeln.json

Generator:

entsprechendes Skript unter scripts/

Ausgabe:

pages/bauernregel/

## Templates

Pfad:

templates/display_pages/

Die Templates sind die eigentliche HTML-Struktur der automatisch
generierten Folien.

Bei Layoutänderungen sollte nicht nur die generierte Datei unter
pages/ verändert werden.

Regel:

Template + Generator + CSS gemeinsam prüfen.

## CSS

Pfad:

static/css/display_pages/

Es gibt gemeinsame Basisstile und modulbezogene Stylesheets.

Zielauflösung:

1920 × 1080

Die Darstellung ist nicht primär für responsive Webbrowser gedacht,
sondern für einen festen Digital-Signage-Bildschirm.

## Ressourcen

Pfad:

resources/

Typische Inhalte:

* Auszeit-Logo
* Folienmotive
* Menübilder
* Wetter-Icons
* News-Bilder
* Zitat-Portraits
* Eventgrafiken

Ressourcen sind Teil des Designs und werden teilweise auch in den
öffentlichen Export übernommen.

## Generierte Seiten

Pfad:

pages/

Die Dateien in diesem Bereich sind häufig Resultate von Generatoren.

Daher gilt:

Eine direkte Änderung an pages/... kann beim nächsten Generatorlauf
überschrieben werden.

Dauerhafte Änderungen müssen an der jeweiligen Quelle vorgenommen
werden.

## Upload-Seiten

Pfad:

pages/upload/

Diese Seiten sind eine Ausnahme.

Sie werden über die lokale Administrationsoberfläche hochgeladen und
dürfen dort auch wieder gelöscht werden.

Andere automatisch erzeugte Seiten sollen über die Admin-Oberfläche
nicht gelöscht werden.

## Öffentlicher Export

Wichtige Skripte:

scripts/export_public.sh
scripts/publish_public_ftp.sh

Ablauf:

1. Daten aktualisieren
2. Seiten generieren
3. Exportverzeichnis vorbereiten
4. HTML kopieren
5. CSS kopieren
6. benötigte Bilder und Ressourcen kopieren
7. per FTP hochladen

Exportverzeichnis:

public_export/

Dieses Verzeichnis ist generiert und wird nicht mit Git versioniert.

## FTP-Publikation

Die produktive FTP-Konfiguration liegt außerhalb von Git.

Typische Werte:

* FTP_HOST
* FTP_USER
* FTP_PASS
* FTP_REMOTE_DIR

Die Veröffentlichung erfolgt automatisiert über systemd.

## Systemd

Wichtige Einheit:

auszeit-display.service

Zusätzli
