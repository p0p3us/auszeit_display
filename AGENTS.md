# Auszeit Digital Signage – Codex Instructions

## Projekt

Dieses Repository enthält das Digital-Signage-System des
Café Restaurant Auszeit.

Das System erzeugt und zeigt automatisch verschiedene
1920×1080-Digital-Signage-Folien und veröffentlicht einen Teil
davon zusätzlich auf einem Webserver.

Repository:
p0p3us/auszeit_display

Produktivsystem:
Raspberry Pi 4 mit Debian 13 (trixie), aarch64.

Produktionspfad auf dem Raspberry Pi:

/home/pi/auszeit_display


## Entwicklungsumgebungen

Die primäre Entwicklungsumgebung ist Windows.

Der Raspberry Pi ist Produktions- und Hardwareumgebung.

Pi-spezifische Pfade oder Systembefehle dürfen nicht automatisch
als Fehler betrachtet oder für Windows umgeschrieben werden.

Insbesondere ist:

/home/pi/auszeit_display

auf dem Produktivsystem ein gültiger Pfad.


## Grundregeln für Änderungen

- Vor größeren Änderungen zuerst die bestehende Architektur untersuchen.
- Bestehende Funktionen nicht unnötig neu schreiben.
- Änderungen möglichst klein, nachvollziehbar und modular halten.
- Vorhandene Tests nach Änderungen ausführen.
- Bei neuen Funktionen nach Möglichkeit Tests ergänzen.
- Keine produktiven Daten löschen.
- Keine Zugangsdaten oder API-Keys in Git einchecken.
- Keine .env-Dateien committen.
- Keine Änderungen an produktiven Datenformaten ohne Prüfung aller Verbraucher.
- Generierte Dateien nicht als alleinige Quelle einer Änderung behandeln.
  Templates und Generatoren müssen die eigentliche Quelle bleiben.
- Bestehende Designregeln der Digital-Signage-Folien beibehalten.
- Bei Unsicherheit zuerst den bestehenden Code und die Dokumentation analysieren.


## Git-Arbeitsweise

Branch:
main

GitHub ist die verbindliche Codequelle.

Änderungen sollen:

1. lokal durchgeführt,
2. getestet,
3. überprüft,
4. committed,
5. nach GitHub gepusht werden.

Produktive Änderungen am Raspberry Pi sollen grundsätzlich aus dem
Git-Repository übernommen werden.

Direkte Änderungen am Raspberry Pi sind nur für Diagnose,
Systemkonfiguration oder ausdrücklich gewünschte Hotfixes vorgesehen.


## Wichtige Verzeichnisse

- app.py
  Flask-Anwendung und lokale Display-Steuerung.

- modules/
  Python-Module für Displayzustand, Seitenverwaltung und Systemstatus.

- scripts/
  Generatoren, Datenabruf, Export und Veröffentlichung.

- templates/
  Jinja-/HTML-Vorlagen der Digital-Signage-Folien.

- pages/
  Generierte HTML-Folien.

- static/
  CSS und andere statische Webressourcen.

- resources/
  Bilder, Logos, Wetter-Icons, Portraits und andere Assets.

- data/
  Datenquellen, Zwischendaten und Statusdateien.

- tests/
  Automatisierte Tests.

- webinterface/
  PHP-Webinterface für Menü- und Termineingabe.


## Persistente Daten

Folgende Bereiche enthalten produktive bzw. vom Webinterface erzeugte
Daten und dürfen durch Deployment oder Synchronisation nicht ungeprüft
gelöscht oder überschrieben werden:

- webinterface/data/menus/
- webinterface/data/termine/
- webinterface/data/auth/
- webinterface/uploads/events/

Die entsprechenden .gitkeep-Dateien und vorgesehenen
Verzeichnisstrukturen bleiben erhalten.


## Aktuelle Digital-Signage-Module

Zum System gehören unter anderem:

- News
- Wetter
- Mittagsmenü
- Wochenschmankerl
- Termine / Events
- Namenstag
- Bauernregel
- Auszeit Weisheit
- Zitat des Tages
- Upload-Folien
- lokale Display-Steuerung

Das frühere Samstagsschmankerl wurde abgeschafft.

Das System verwendet stattdessen das Wochenschmankerl.

Neue Änderungen dürfen die alte Samstagsschmankerl-Logik nicht
wieder einführen.


## Digital-Signage-Design

Zielauflösung:

1920 × 1080 Pixel, 16:9.

Die Folien sind für die Anzeige auf einem Fernseher optimiert.

Gemeinsame Designentscheidungen und vorhandene CSS-Strukturen sollen
wiederverwendet werden.

Wichtige Ziele:

- gute Lesbarkeit aus größerer Entfernung
- große Typografie
- klare Hierarchie
- keine unnötig kleinen Texte
- konsistente Positionen und Abstände
- hochwertige, ruhige Gastronomie-Optik


## Generierte Inhalte

Viele Dateien unter pages/ werden automatisch erzeugt.

Bei Änderungen an einer automatisch erzeugten Folie immer prüfen:

- zugehörigen Generator unter scripts/
- zugehöriges Template unter templates/
- zugehöriges CSS unter static/
- verwendete Assets unter resources/
- Tests

Eine manuelle Änderung ausschließlich an einer generierten HTML-Datei
ist normalerweise nicht ausreichend.


## Veröffentlichung

Ein stündlicher Publikationsprozess erzeugt die öffentlichen Inhalte
und überträgt sie per FTP auf den Webserver.

Wichtige Skripte:

- scripts/export_public.sh
- scripts/publish_public_ftp.sh

Diese Shell-Skripte müssen auf Linux ausführbar bleiben.

Insbesondere scripts/export_public.sh darf sein executable bit
nicht verlieren.


## Geheimnisse und Konfiguration

Produktive Zugangsdaten, FTP-Passwörter und API-Keys gehören nicht
in Git.

Lokale .env-Dateien werden über .gitignore ausgeschlossen.

Beispielsweise enthält publish.env produktive Konfiguration und darf
nicht committed werden.


## Tests

Vorhandene Tests befinden sich unter:

tests/

Auf dem Raspberry Pi wird das Python-Virtual-Environment unter:

/home/pi/auszeit_display/venv

verwendet.

Typischer Testaufruf auf dem Raspberry Pi:

./venv/bin/python -m unittest

Bei gezielten Änderungen möglichst zuerst relevante Tests und danach
die vollständige Testsuite ausführen.


## Webinterface

Das PHP-Webinterface gehört zum selben Gesamtsystem.

Es verwaltet insbesondere:

- Mittagsmenüs
- Wochenschmankerl
- Termine / Veranstaltungen

Änderungen an Datenstrukturen müssen deshalb sowohl auf Python-Seite
als auch im PHP-Webinterface geprüft werden.


## Arbeitsweise von Codex

Bei neuen Aufgaben:

1. Relevante Dateien suchen.
2. Bestehenden Datenfluss verstehen.
3. Abhängige Komponenten identifizieren.
4. Änderung implementieren.
5. Tests ausführen oder ergänzen.
6. Diff auf unbeabsichtigte Änderungen prüfen.
7. Ergebnis und eventuell verbleibende Risiken klar zusammenfassen.

Bei umfangreichen Umbauten nicht ungefragt die gesamte Architektur
ersetzen.

Die Stabilität des laufenden Raspberry-Pi-Systems hat Vorrang vor
unnötigem Refactoring.