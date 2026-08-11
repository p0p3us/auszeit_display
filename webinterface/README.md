# Auszeit-Webinterface

Dieser Ordner enthält den versionierten Quellcode der PHP-Verwaltung für Menüs und Termine.

## Laufzeitdaten

Die folgenden Verzeichnisse werden auf dem Webspace durch das Webinterface beschrieben und sind absichtlich von Git ausgeschlossen:

- `data/menus/`
- `data/termine/`
- `uploads/events/single/`
- `uploads/events/templates/`

Die `.gitkeep`-Dateien erhalten nur die Verzeichnisstruktur. Produktionsdaten aus diesen Ordnern dürfen weder committed noch bei einem Deployment gelöscht oder überschrieben werden.

## Lokale Konfiguration

Die Anmeldung liest den Passwort-Hash aus `config/local.php`. Diese Datei ist von Git ausgeschlossen und wird nicht automatisch veröffentlicht.

1. `config/local.example.php` als `config/local.php` kopieren.
2. Einen Hash erzeugen:
   `php -r "echo password_hash('NEUES-PASSWORT', PASSWORD_DEFAULT), PHP_EOL;"`
3. Den Platzhalter in `config/local.php` durch den erzeugten Hash ersetzen.
4. `config/local.php` einmalig geschützt auf dem Webspace ablegen.

Ohne gültige lokale Konfiguration antworten die beiden Verwaltungsseiten mit HTTP 503. Menü- und Terminverwaltung verwenden bewusst dieselbe Anmeldung.

## Veröffentlichung

`scripts/publish_webinterface_ftp.sh` überträgt ausschließlich eine feste Positivliste aus PHP-Dateien sowie `assets/gold.jpg` und `assets/leather.jpg`. Es verwendet weder `mirror` noch `--delete`.

In `config/publish.env` wird dafür zusätzlich gesetzt:

```text
WEBINTERFACE_REMOTE_DIR=/menu_admin
```

Das Skript akzeptiert absichtlich kein anderes Ziel. Es überträgt insbesondere nicht:

- `config/local.php`
- `data/menus/`
- `data/termine/`
- `uploads/events/`
- eine über die Menüverwaltung hochgeladene Datei `assets/menu-background.*`

Die Folienveröffentlichung nach `/auszeit-display` und die Webinterface-Veröffentlichung nach `/menu_admin` bleiben getrennte Vorgänge.

## Schutz schreibender Aktionen

Alle authentifizierten POST-Aktionen verwenden ein kryptografisch zufälliges CSRF-Token aus der Session. Das gilt für Speichern, Löschen, Bild-Upload, Hintergrund-Reset und Abmeldung. Die Abmeldung ist deshalb bewusst kein GET-Link mehr.

JSON-Dateien werden zuerst vollständig in eine temporäre Datei im gleichen Ordner geschrieben und anschließend atomar umbenannt. Dadurch bleibt bei einem abgebrochenen Schreibvorgang die zuletzt vollständige Version bestehen.

## Aktuelle Einstiegspunkte

- `menu_admin.php`: Menüverwaltung
- `termine-admin.php`: Terminverwaltung
- `preview-menu.php`: Menüvorschau
- `preview-termine.php`: Terminvorschau

Fehlgeschlagene Anmeldungen werden pro IP-Adresse gezählt. Nach 10 aufeinanderfolgenden Fehlversuchen ist die Anmeldung für diese IP 15 Minuten gesperrt. Eine erfolgreiche Anmeldung setzt den Zähler zurück. Der Zustand liegt ausschließlich in `data/auth/login-attempts.json` und wird weder versioniert noch deployed. Grenzwert und Sperrdauer können in `config/local.php` über `max_login_attempts` und `login_lock_seconds` angepasst werden.

## PHP-Laufzeiteinstellungen

`includes/bootstrap.php` setzt zentral die Zeitzone `Europe/Vienna` und startet die Session im strikten Modus. Session-Cookies sind `HttpOnly`, verwenden `SameSite=Strict` und erhalten bei HTTPS zusätzlich das Attribut `Secure`. Beide Verwaltungsseiten laden diesen Bootstrap vor jeder Verwendung der Session.
