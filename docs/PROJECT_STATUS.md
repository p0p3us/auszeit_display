# Auszeit Digital Signage – Projektstatus

Stand: September 2026

## Projektziel

Das Projekt stellt ein lokales Digital-Signage-System für das
Café Restaurant Auszeit bereit.

Die Inhalte werden automatisch erzeugt und auf einem Fernseher
im 16:9-Format angezeigt.

Ein Teil der erzeugten Inhalte wird zusätzlich stündlich auf einen
öffentlichen Webserver exportiert.

## Produktivsystem

Hardware:

* Raspberry Pi 4 Model B
* SSD als System-/Projektlaufwerk
* Fernseher als Anzeige

Betriebssystem:

* Debian 13 trixie
* aarch64

Benutzer:

* pi

Hostname:

* auszeit

Projektpfad:

/home/pi/auszeit_display

## Display-Umgebung

Das Raspberry-Pi-System startet in eine grafische Umgebung.

Verwendet werden unter anderem:

* LightDM
* labwc
* Chromium im Kiosk-Betrieb

Das Display zeigt die lokal erzeugten HTML-Seiten.

## Flask-Anwendung

Die Flask-Anwendung stellt unter anderem bereit:

* Administrationsoberfläche
* Auswahl der aktiven Seite
* Upload von HTML-Seiten
* Statusinformationen
* Anzeige der aktuellen Seite
* Ressourcen und statische Dateien

Der aktive Seitenzustand wird lokal gespeichert.

## Systemdienst

Die Anwendung läuft als systemd-Dienst.

Dienst:

auszeit-display.service

Der Dienst startet die Anwendung aus:

/home/pi/auszeit_display

## Publikation

Die öffentlichen Digital-Signage-Seiten werden stündlich erzeugt
und per FTP auf den Webserver übertragen.

Wichtige Komponenten:

* scripts/export_public.sh
* scripts/publish_public_ftp.sh
* systemd timer auszeit-publish-public.timer

Der Timer läuft stündlich.

Der Export umfasst unter anderem:

* HTML
* CSS
* Bilder
* Wetter-Icons
* News-Bilder
* Menüfolien
* Terminfolien
* Weisheit
* Zitat des Tages

Produktive FTP- und API-Zugangsdaten liegen außerhalb von Git
in lokalen Umgebungsdateien.

## Webinterface

Zum Gesamtsystem gehört ein PHP-Webinterface auf dem Webspace.

Es dient insbesondere zur Pflege von:

* Mittagsmenüs
* Wochenschmankerl
* Veranstaltungen / Termine

Die Daten werden vom Raspberry Pi abgeholt und in lokale
Zwischenformate normalisiert.

## Persistente Webinterface-Daten

Folgende Daten dürfen bei Deployment oder Synchronisation
nicht gelöscht werden:

* webinterface/data/menus/
* webinterface/data/termine/
* webinterface/data/auth/
* webinterface/uploads/events/

Diese Daten werden auf dem Webspace erzeugt bzw. gepflegt.

## Menüsystem

Das Menüsystem verarbeitet derzeit:

* Dienstag
* Mittwoch
* Donnerstag
* Freitag
* optional zweites Freitagsmenü
* Wochenschmankerl
* zusätzliche Informationsblöcke

Das frühere Samstagsschmankerl wurde entfernt.

Das Wochenschmankerl hat jetzt eine eigene Digital-Signage-Folie.

Wichtige Dateien befinden sich unter anderem in:

* scripts/fetch_menue.py
* scripts/export_menue.py
* templates/display_pages/
* static/css/display_pages/menue.css
* webinterface/menu_admin.php
* webinterface/menu-layout.php

Die Menüfolien verwenden große Typografie und separate
Motivbilder.

## Termine / Veranstaltungen

Termine werden über das Webinterface gepflegt.

Unterstützt werden:

* Einzeltermine
* Serientermine

Die Daten werden vom Raspberry Pi geladen und daraus
automatisch Digital-Signage-Folien erzeugt.

Gestaltungsstand:

* hochwertige dunkle Gestaltung
* Goldakzente
* automatische Textskalierung
* Preis / Eintritt als eigener Bereich
* Reservierungsinformationen als eigener Bereich

Die genaue visuelle Feinabstimmung kann später noch weiter
optimiert werden.

## News

News werden automatisch aus RSS-Quellen geladen.

Verwendete Kategorien waren zuletzt:

* Sport
* Niederösterreich
* Science
* Help

Pro Kategorie werden mehrere Meldungen erzeugt.

News enthalten nach Möglichkeit:

* Titel
* Kurzbeschreibung
* Link
* Bild

Wenn kein Bild vorhanden ist, wird ein Fallback-Motiv verwendet.

## Wetter

Wetterdaten werden über OpenWeather bezogen.

Konfigurierter Anzeigename:

Sdlg. M. Theresia

API-Ort:

Sollenau, AT

Erzeugt werden unter anderem:

* Wetter morgen
* 5-Tage-Wetter

Es gibt eigene Wetter-Icons für die OpenWeather-Codes.

## Namenstag

Die Namenstage werden aus einer lokalen JSON-Datei bezogen.

Das Modul erzeugt automatisch die jeweilige Tagesfolie.

## Bauernregel

Bauernregeln liegen lokal als JSON vor.

Es gibt:

* allgemeine Monatsregeln
* Regeln für bestimmte Kalendertage

Die passende Regel wird automatisch ausgewählt.

## Auszeit Weisheit

Status:

abgeschlossen.

Die Weisheiten werden aus:

data/weisheiten.json

geladen.

Design:

* roter Hintergrund
* Auszeit-Logo
* Claim "täglich frisch eingeschenkt"
* Weisheit in zentraler Textkarte

Wichtige Textregeln:

* maximale Textbreite ungefähr 70 % der Folienbreite
* Zeilenumbrüche aus den Quelldaten werden berücksichtigt
* wenn eine Zeile umgebrochen werden muss, wird ein konsistenter
  mehrzeiliger Satz bevorzugt
* zwei- und dreizeilige Darstellungen sind vorgesehen

Das Modul wechselt einmal täglich.

## Zitat des Tages

Status:

abgeschlossen.

Die Zitate liegen in:

data/zitate.json

Die Folie enthält:

* Zitat
* Autor
* kurze Beschreibung
* Geburtsdatum
* Sterbedatum
* Schwarz-Weiß-Portrait

Portraits liegen unter:

resources/zitate/

Für unbekannte Personen kann ein neutrales Ersatzmotiv verwendet werden.

Das Modul wurde erfolgreich getestet.

## Upload-Folien

Zusätzliche HTML-Seiten können über die lokale Administration
hochgeladen werden.

Nur Upload-Seiten dürfen über die Administrationsoberfläche
wieder gelöscht werden.

## Tests

Es existieren automatisierte Tests unter:

tests/

Getestet werden unter anderem:

* Generatoren
* Fetch-Skripte
* Shell-Skripte
* Zitat-Modul
* Menülogik
* Terminlogik

Auf dem Raspberry Pi wurden wiederholt vollständige bzw.
gezielte Tests erfolgreich ausgeführt.

## Git-Workflow

Zentrales Repository:

p0p3us/auszeit_display

Hauptbranch:

main

Entwicklungsablauf:

Windows
-> Git
-> GitHub
-> Raspberry Pi

Direkte Änderungen am Raspberry Pi sollen vermieden werden,
außer bei Diagnose oder Pi-spezifischen Problemen.

## Aktuell wichtige abgeschlossene Bereiche

Abgeschlossen bzw. weitgehend abgeschlossen:

* Grundstruktur
* Flask-Anwendung
* Wetter
* News
* Namenstag
* Bauernregel
* Menüsystem
* Wochenschmankerl
* Termine
* Auszeit Weisheit
* Zitat des Tages
* öffentlicher Export
* FTP-Publikation
* Webinterface-Integration

## Noch offene bzw. spätere Themen

Noch offen bzw. für eine spätere Phase vorgesehen:

* eigentliches zentrales Abspiel-/Playlist-Modul für die
  Digital-Signage-Inhalte
* weitere statische Folien
* weitere grafische Feinabstimmung einzelner Folien
* mögliche Umstellung der Flask-Anwendung auf einen produktiveren
  WSGI-Betrieb
* weitere Stabilitäts- und Deployment-Optimierungen

## Aktuelle Priorität

Das laufende System soll stabil bleiben.

Neue Entwicklungen sollen künftig primär mit Codex direkt im
Repository durchgeführt werden.

Vor größeren Änderungen soll zuerst geprüft werden:

* welche Module betroffen sind
* welche Templates betroffen sind
* welche Datenformate betroffen sind
* ob das Webinterface ebenfalls angepasst werden muss
* welche Tests betroffen sind
* ob die Änderung Auswirkungen auf den Raspberry Pi oder den
  öffentlichen Export hat
