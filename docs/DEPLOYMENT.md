# Auszeit Digital Signage – Deployment

Stand: September 2026

## Ziel

Dieses Dokument beschreibt, wie Änderungen am Auszeit-Digital-Signage-System sicher vom Entwicklungsrechner in die produktive Raspberry-Pi-Umgebung und auf den Webspace übernommen werden.

Ziel ist ein reproduzierbarer Ablauf ohne Verlust produktiver Daten.

---

## Grundprinzip

Der normale Entwicklungsweg ist:

Windows
→ Git
→ GitHub
→ Raspberry Pi
→ öffentlicher Export / Webspace

Der Raspberry Pi ist die produktive Laufzeitumgebung.

Direkte Änderungen auf dem Raspberry Pi sollen nur für:

* Diagnose
* Systemkonfiguration
* Hardwaretests
* ausdrücklich gewünschte Hotfixes

durchgeführt werden.

---

## Entwicklungsrechner

Lokaler Projektordner:

C:\Users\marku\OneDrive\03_Auszeit\05_DS Projekt\raspberry_pi\auszeit_display

Git-Repository:

p0p3us/auszeit_display

Hauptbranch:

main

---

## Vor jeder Änderung

Vor Beginn einer neuen Arbeit:

```powershell
& "C:\Program Files\Git\cmd\git.exe" status
```

Danach:

```powershell
& "C:\Program Files\Git\cmd\git.exe" pull
```

Ziel:

* lokaler Stand aktuell
* keine unerwarteten lokalen Änderungen
* keine Konflikte

---

## Nach Änderungen auf Windows

Änderungen prüfen:

```powershell
& "C:\Program Files\Git\cmd\git.exe" status
```

Diff prüfen:

```powershell
& "C:\Program Files\Git\cmd\git.exe" diff
```

Dateien vormerken:

```powershell
& "C:\Program Files\Git\cmd\git.exe" add .
```

Commit erstellen:

```powershell
& "C:\Program Files\Git\cmd\git.exe" commit -m "Beschreibung der Änderung"
```

Danach:

```powershell
& "C:\Program Files\Git\cmd\git.exe" push
```

---

## Produktivsystem Raspberry Pi

Hostname:

auszeit

Produktionspfad:

/home/pi/auszeit_display

Benutzer:

pi

Betriebssystem:

Debian 13 trixie

Architektur:

aarch64

---

## Update auf dem Raspberry Pi

Im Regelfall:

```bash
cd /home/pi/auszeit_display
git status
git pull
```

Vor dem Pull sollte geprüft werden, dass keine unbeabsichtigten lokalen Änderungen vorhanden sind.

Wenn `git status` lokale Änderungen zeigt, diese nicht einfach überschreiben.

Zuerst klären, ob es sich um:

* einen produktiven Hotfix
* lokale Konfiguration
* generierte Dateien
* versehentliche Änderungen

handelt.

---

## Python-Abhängigkeiten

Produktives virtuelles Environment:

/home/pi/auszeit_display/venv

Wenn sich `requirements.txt` geändert hat:

```bash
cd /home/pi/auszeit_display
./venv/bin/pip install -r requirements.txt
```

Danach Tests ausführen.

---

## Tests auf dem Raspberry Pi

Vollständige Testsuite:

```bash
cd /home/pi/auszeit_display
./venv/bin/python -m unittest
```

Gezielte Tests können ebenfalls ausgeführt werden.

Beispiel:

```bash
./venv/bin/python -m unittest tests.test_generators
```

oder mehrere Testmodule:

```bash
./venv/bin/python -m unittest \
  tests.test_zitat \
  tests.test_generators \
  tests.test_shell_scripts
```

Ein Deployment soll nicht als abgeschlossen gelten, solange relevante Tests fehlschlagen.

---

## Flask-Dienst

Systemd-Dienst:

auszeit-display.service

Status prüfen:

```bash
systemctl status auszeit-display.service
```

Neustart:

```bash
sudo systemctl restart auszeit-display.service
```

Danach erneut prüfen:

```bash
systemctl status auszeit-display.service
```

Bei Fehlern Logs ansehen:

```bash
journalctl -u auszeit-display.service -n 100 --no-pager
```

---

## Öffentliche Publikation

Die öffentlichen Inhalte werden automatisch stündlich erzeugt und übertragen.

Wichtige Komponenten:

* scripts/export_public.sh
* scripts/publish_public_ftp.sh
* auszeit-publish-public.timer

Timer prüfen:

```bash
systemctl status auszeit-publish-public.timer
```

Nächste geplante Läufe:

```bash
systemctl list-timers | grep auszeit
```

---

## Veröffentlichung manuell auslösen

Wenn eine Änderung sofort geprüft werden soll und nicht bis zum nächsten Timerlauf gewartet werden soll:

```bash
cd /home/pi/auszeit_display
./scripts/publish_public_ftp.sh
```

Falls das Skript nicht ausführbar ist:

```bash
chmod +x scripts/publish_public_ftp.sh
chmod +x scripts/export_public.sh
```

Danach erneut starten.

Die Shell-Skripte müssen in Git mit gesetztem executable bit gespeichert bleiben.

---

## Bekannter Fehler: Permission denied

Wenn erscheint:

```text
./scripts/publish_public_ftp.sh: line ...:
.../scripts/export_public.sh: Permission denied
```

prüfen:

```bash
ls -l scripts/export_public.sh
```

Das Skript muss ausführbar sein.

Korrektur:

```bash
chmod +x scripts/export_public.sh
```

Danach den korrekten Dateimodus auch in Git sicherstellen.

Auf Windows kann dazu verwendet werden:

```powershell
& "C:\Program Files\Git\cmd\git.exe" update-index --chmod=+x scripts/export_public.sh
```

Danach committen und pushen.

---

## Generierte Seiten manuell aktualisieren

Einzelne Generatoren können auf dem Raspberry Pi gezielt ausgeführt werden.

Beispiele:

```bash
./venv/bin/python scripts/generate_weather.py
```

```bash
./venv/bin/python scripts/generate_zitat.py
```

```bash
./venv/bin/python scripts/generate_weisheit.py
```

Für Menü, Termine und andere Module die entsprechenden Skripte unter `scripts/` verwenden.

Nach manuellen Generatorläufen prüfen:

* Rückgabecode
* erzeugte Dateien
* Browserdarstellung
* ggf. Tests

---

## Öffentlicher Export

Das Exportskript erzeugt ein temporäres bzw. generiertes Exportverzeichnis.

Exportverzeichnis:

public_export/

Dieses Verzeichnis ist nicht Bestandteil der Versionsverwaltung.

Es wird bei der Publikation neu erzeugt bzw. vorbereitet.

---

## FTP-Konfiguration

Produktive Zugangsdaten liegen außerhalb von Git.

Typische Konfiguration enthält:

* FTP_HOST
* FTP_USER
* FTP_PASS
* FTP_REMOTE_DIR
* OPENWEATHER_API_KEY
* WEATHER_LAT
* WEATHER_LON
* WEATHER_LOCATION_NAME

Lokale Konfigurationsdateien wie:

publish.env

dürfen nicht committed werden.

---

## Geheimnisse

Folgende Inhalte gehören niemals ins Repository:

* FTP-Passwörter
* API-Keys
* Zugangsdaten
* produktive Login-Daten
* lokale Authentifizierungsdateien
* private `.env`-Dateien

Die `.gitignore` schließt entsprechende Dateien aus.

Vor Commits mit Konfigurationsänderungen immer prüfen:

```powershell
& "C:\Program Files\Git\cmd\git.exe" status
```

und bei Bedarf:

```powershell
& "C:\Program Files\Git\cmd\git.exe" ls-files "*.env"
```

---

## Webinterface

Das PHP-Webinterface befindet sich im Repository unter:

webinterface/

Nicht alle Inhalte dieses Verzeichnisses dürfen einfach auf den Webspace gespiegelt werden.

Besonders wichtig:

Produktive Daten auf dem Webspace dürfen nicht gelöscht oder überschrieben werden.

Geschützte Bereiche:

* webinterface/data/menus/
* webinterface/data/termine/
* webinterface/data/auth/
* webinterface/uploads/events/

Diese Verzeichnisse enthalten produktive bzw. benutzererzeugte Daten.

---

## Webinterface-Deployment

Bei Änderungen am Webinterface nur die eigentlichen Programmdateien aktualisieren.

Beispiele:

* PHP-Dateien
* CSS
* JavaScript
* Templates

Nicht ungeprüft übertragen:

* produktive Menüdaten
* produktive Termindaten
* Authentifizierungsdaten
* Eventuploads

---

## Menü-Webinterface

Änderungen am Menüsystem müssen immer gemeinsam geprüft werden in:

* webinterface/menu_admin.php
* webinterface/menu-layout.php
* scripts/fetch_menue.py
* scripts/export_menue.py
* Menü-Templates
* Menü-CSS
* zugehörigen Tests

Das aktuelle Datenmodell verwendet das Wochenschmankerl.

Das alte Samstagsschmankerl darf nicht wieder eingeführt werden.

---

## Termin-Webinterface

Änderungen an Terminstrukturen müssen auf beiden Seiten geprüft werden:

Webinterface
und
Raspberry-Pi-Fetch-/Generatorlogik

Unterstützte produktive Daten dürfen nicht durch neue Deployments überschrieben werden.

---

## Kontrolle nach einem Deployment

Nach jeder produktiven Änderung prüfen:

1. `git status`
2. Tests
3. Flask-Dienst
4. systemd-Timer
5. betroffene Generatoren
6. lokale Digital-Signage-Darstellung
7. öffentlichen Export
8. Webinterface, falls betroffen

---

## Browserkontrolle

Nach Änderungen an HTML/CSS:

* lokale Seite im Chromium prüfen
* Textgrößen prüfen
* 1920×1080-Darstellung prüfen
* keine abgeschnittenen Inhalte
* keine horizontalen Scrollbars
* Bilder korrekt geladen
* Fallbacks korrekt
* keine sichtbaren Debug-Ausgaben

---

## Datenformatänderungen

Bei Änderungen an JSON-Strukturen niemals nur eine Seite anpassen.

Immer prüfen:

Producer
→ gespeicherte Daten
→ Consumer
→ Generator
→ Template
→ Test

Beispiele:

Menü:
Webinterface → Fetch → `menue.json` → Export → Template

Termine:
Webinterface → Fetch → lokale Daten → Generator → Template

---

## Rollback

Wenn eine Änderung produktiv Probleme verursacht:

Zuerst aktuellen Stand prüfen:

```bash
git status
git log --oneline -10
```

Keine produktiven Daten löschen.

Bei reinem Codeproblem kann auf einen bekannten funktionierenden Commit zurückgegangen werden.

Vor einem harten Reset immer prüfen, ob lokale produktive Änderungen existieren.

Ein `git reset --hard` darf nicht unüberlegt verwendet werden.

---

## Kein automatisches Löschen produktiver Daten

Deployment-Skripte dürfen produktive Webinterface-Daten nicht löschen.

Besonders kritisch sind Synchronisationsbefehle mit Optionen wie:

```text
--delete
```

Solche Befehle dürfen nur auf vollständig generierte Exportbereiche angewendet werden.

Nicht auf Verzeichnisse mit:

* Menüdaten
* Termindaten
* Uploads
* Authentifizierungsdaten

---

## Abschluss
