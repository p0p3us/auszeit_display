# Auszeit Digital Signage

Digital-Signage-System für das Café Restaurant Auszeit auf einem Raspberry Pi 4. Eine Flask-Anwendung verwaltet die Folien, zeigt die aktive Seite im Browser an und stellt eine Administrationsoberfläche bereit. Generatoren erzeugen unter anderem Wetter-, Nachrichten-, Menü-, Namenstags- und Bauernregel-Folien.

## Systemüberblick

- Zielgerät: Raspberry Pi 4, Start von SSD
- Betriebssystem-Benutzer: `pi`
- Installationsordner: `/home/pi/auszeit_display`
- Webanwendung: Flask auf Port `5000`
- Administration: `http://auszeit:5000/admin`
- Anzeige: `http://auszeit:5000/display`
- Statusprüfung: `http://auszeit:5000/status`
- Systemdienst: `auszeit-display.service`

## Verzeichnisstruktur

| Pfad | Inhalt |
|---|---|
| `app.py` | Flask-Anwendung und Webrouten |
| `modules/` | Zustands-, Seiten- und Systemfunktionen |
| `scripts/` | Datenabruf, Seitengenerierung und Veröffentlichung |
| `templates/` | Jinja-Templates für Anwendung und Generatoren |
| `static/` | CSS und statische Dateien der Webanwendung |
| `resources/` | Bilder, Wetter-Icons und Folienressourcen |
| `pages/` | Fertige HTML-Folien |
| `data/` | Zustands- und Eingangsdaten im JSON-Format |
| `tests/` | Automatisierte Tests |
| `config/` | Lokale Konfiguration; Zugangsdaten werden nicht versioniert |
| `webinterface/` | PHP-Verwaltung für Menüs und Termine auf dem Webspace |

## Erstinstallation auf dem Raspberry Pi

Vorausgesetzt werden Raspberry Pi OS, Git und Python 3 mit Unterstützung für virtuelle Umgebungen.

```bash
sudo apt update
sudo apt install -y git python3 python3-venv tesseract-ocr lftp rsync
cd /home/pi
git clone https://github.com/p0p3us/auszeit_display.git
cd /home/pi/auszeit_display
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements.txt
```

`pytesseract` benötigt das separat installierte Programm Tesseract. Falls die Menüerkennung zusätzliche Sprachdaten verwendet, müssen diese passend ergänzt werden.

## Lokale Konfiguration

Die Datei `config/publish.env` enthält Zugangsdaten und API-Schlüssel. Sie ist durch `.gitignore` vom Repository ausgeschlossen und muss auf jedem Zielsystem separat angelegt oder aus einer sicheren Sicherung wiederhergestellt werden.

Benötigte Wetterwerte sind mindestens:

```dotenv
OPENWEATHER_API_KEY=...
WEATHER_LAT=...
WEATHER_LON=...
WEATHER_LOCATION_NAME=Eggendorf
```

Für die Veröffentlichung per FTP werden zusätzlich diese Werte benötigt:

```dotenv
FTP_HOST=...
FTP_USER=...
FTP_PASS=...
FTP_REMOTE_DIR=/auszeit-display
```

`FTP_REMOTE_DIR` bezeichnet den gemeinsamen Webordner. Der vollständige FTP-Export synchronisiert diesen Ordner mit `--delete`. Das Namenstag-Skript beschränkt seine Synchronisierung dagegen auf dessen Unterordner `namenstag` und kann andere Folien nicht löschen.

Die optionale rsync-Variante für den Namenstag benötigt:

```dotenv
RSYNC_REMOTE_USER=...
RSYNC_REMOTE_HOST=...
RSYNC_REMOTE_PATH=/pfad/zum/webroot/auszeit-display
```

Echte Schlüssel, Passwörter und Tokens dürfen niemals committed werden. Die Publish-Skripte verweigern leere Werte und unsichere Zielpfade wie `/`.

## Systemdienst einrichten

Die mitgelieferte Service-Datei erwartet das Projekt unter `/home/pi/auszeit_display` und die virtuelle Umgebung unter `venv/`.

```bash
cd /home/pi/auszeit_display
sudo cp auszeit-display.service /etc/systemd/system/auszeit-display.service
sudo systemctl daemon-reload
sudo systemctl enable --now auszeit-display.service
```

Dienst und Anwendung prüfen:

```bash
systemctl status auszeit-display.service --no-pager
curl http://127.0.0.1:5000/status
```

Die letzten Protokollmeldungen zeigt:

```bash
journalctl -u auszeit-display.service -n 100 --no-pager
```

## Sicher aktualisieren

Vor dem Update muss die lokale Konfiguration erhalten bleiben. `config/publish.env` darf weder gelöscht noch durch eine Datei aus Git ersetzt werden. Eigene, noch nicht eingecheckte Änderungen müssen zuerst geprüft werden.

```bash
cd /home/pi/auszeit_display
git status --short
git pull --ff-only
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m unittest discover -s tests -v
sudo systemctl restart auszeit-display.service
systemctl status auszeit-display.service --no-pager
curl http://127.0.0.1:5000/status
```

Wenn `git status --short` vor dem Update unerwartete Änderungen anzeigt, nicht einfach weiterarbeiten oder Dateien löschen. Zuerst klären, ob es sich um notwendige lokale Anpassungen oder erzeugte Laufzeitdaten handelt.

## Manuell starten

Für einen kontrollierten Test ohne systemd:

```bash
cd /home/pi/auszeit_display
AUSZEIT_DISPLAY_BASE_DIR=/home/pi/auszeit_display venv/bin/python app.py
```

Danach ist die Anwendung unter `http://127.0.0.1:5000/status` erreichbar. Den manuellen Prozess vor dem Start des Systemdienstes wieder beenden, damit Port `5000` nicht doppelt belegt wird.

## Tests

```bash
cd /home/pi/auszeit_display
venv/bin/python -m unittest discover -s tests -v
venv/bin/python -m compileall -q app.py modules scripts
```

Die Tests decken derzeit besonders das sichere Lesen und atomare Schreiben von `data/display_state.json` sowie den Rückfall auf `pages/system/default.html` ab.

## Folien und Fallback

Die aktive Folie steht in `data/display_state.json`. Nur vorhandene HTML-Dateien unter `pages/` werden akzeptiert. Fehlt die gespeicherte Seite oder ist die Zustandsdatei beschädigt, verwendet das System automatisch:

```text
pages/system/default.html
```

Über die Administrationsoberfläche hochgeladene HTML-Dateien liegen unter `pages/upload/`. Nur diese Upload-Folien können dort wieder gelöscht werden.

## Wichtige Betriebsregeln

- `config/publish.env` niemals in Git aufnehmen.
- Laufzeitdaten des Webinterfaces unter `webinterface/data/menus`, `webinterface/data/termine` und `webinterface/uploads/events` niemals aus Git auf den Webspace spiegeln oder löschen.
- `venv/`, Logs, Python-Caches und Exportordner nicht versionieren.
- Generierte Dateien unter `pages/` und betriebsrelevante JSON-Dateien nicht pauschal löschen.
- Updates mit `git pull --ff-only` durchführen; dadurch werden unerwartete Historienkonflikte nicht automatisch überschrieben.
- Nach Änderungen zuerst Tests ausführen, dann den Dienst neu starten und `/status` prüfen.

## Aktueller Hardwarehinweis

Der Raspberry Pi 4 bootet von SSD. Die SSD läuft im derzeitigen Aufbau stabil am USB-2-Port. Der Hostname lautet `auszeit`.
