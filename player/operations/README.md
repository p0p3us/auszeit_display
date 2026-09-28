# Automatischer Abruf und Status

Noch keine produktive Feed-URL eingerichtet. Bestätigte Webspace-Verzeichnisse:
`/auszeit-player-feed/` für Pakete und `/auszeit-conf-status/` für den PHP-Empfänger.
Private PHP-Ablage: `/var/www/vhosts/populorum.eu/auszeit-player-private`,
mit `config.php` und Unterordner `status`. Kein Eingriff in den bestehenden Inhaltsserver.

## Player

`bash ~/player/operations/install.sh` installiert zuerst die vorhandene Wiedergabe
mit Lebenszeichen und danach einen systemd-Timer. Der aktuelle Inhaltsstand bleibt
erhalten. Der Timer startet frühestens 60 Sekunden nach Boot und danach fünf
Minuten nach jedem abgeschlossenen Lauf, jeweils mit bis zu 45 Sekunden Zufallsversatz.
Ein Lauf ist auf vier Minuten begrenzt. Kein Warten auf eine Internetverbindung
beim Displaystart; Downloadfehler lassen die bisherigen Inhalte unverändert.

Neue Konfiguration `/etc/auszeit-player/config.json`, root:player 0640:

```json
{
  "device_id": "PRO_GERAET_ERZEUGT",
  "feed_url": null,
  "status_url": null,
  "token_file": "/etc/auszeit-player/status.token"
}
```

Der Installer erzeugt die Geräte-ID einmalig. Ohne URLs schreibt er nur lokalen
Status nach `/var/lib/auszeit-player-operations/status.json`. Vorhandene Konfiguration
wird nicht überschrieben. Keine Zugangsdaten in Git oder im Image.

Später: Feed-URL auf den bestätigten HTTPS-Ordner setzen, Status-URL auf den separat
installierten `status.php`. Kein Querystring, keine Credentials in URLs, keine
Redirects. Token als zufällige mindestens 32-stellige Zeichenfolge getrennt in
`status.token`, Eigentümer root:player, Modus 0640. Kein Token in Kommandozeilen,
Logs oder Screenshots. Der Empfänger bekommt nur den SHA-256-Hash des Tokens.

Status enthält letzte erfolgreiche Updateprüfung, bestätigte Statusübertragung,
aktiven/vorherigen Paketzeiger, Browser-Lebenszeichen, freien Speicher, Temperatur,
Throttling- und Uhrsynchronisationsangaben. Unzugängliche Werte bleiben null.
Fehler werden nur als Typ gespeichert, damit keine Secrets aus URLs/Exceptions
in die Statusdatei geraten. Es gibt nur einen aktuellen Datensatz, keine Warteschlange.

Das Lebenszeichen belegt die laufende Steueroberfläche, noch keine pixelgenaue
Korrektheit oder einen intakten iframe-Renderer. Nach 30 Sekunden ohne Lebenszeichen
lautet der Zustand `unresponsive`. Die vorhandene systemd-Neustartregel bei einem
beendeten Browser bleibt aktiv; ein gesonderter Hänger-Watchdog steht noch aus.

## Webspace-Empfänger

PHP >= 8.1. `player/web/status.php` und `player/web/.htaccess` in den gesonderten
HTTPS-Bereich `/auszeit-conf-status/` legen. Eine bestehende `.htaccess` nicht
überschreiben, sondern die Direktive ergänzen. `CGIPassAuth On` reicht den
Authorization-Header an PHP weiter; auf diesem Hosting war er sonst nicht vorhanden.
Quelle: https://httpd.apache.org/docs/2.4/mod/core.html#cgipassauth
`private-config.example.php` ist eine Vorlage, **kein öffentlich zu ladendes Artefakt**.
Die tatsächliche Konfiguration und das beschreibbare Statusverzeichnis müssen
außerhalb von DOCUMENT_ROOT liegen. Das Skript verweigert anderenfalls die Annahme.

Im öffentlichen Skriptverzeichnis lokal eine nicht versionierte Datei
`status-config-path.php` anlegen, die nur den absoluten privaten Konfigurationspfad
zurückgibt. Dieser Pfad kann erst nach Kenntnis des Hostings eingerichtet werden.
Geräte-ID und Tokenhash in der privaten Konfiguration eintragen. Das Empfängerskript
prüft Token zeitkonstant, nimmt maximal 16 KiB entgegen und ergänzt serverseitig
`received_at`. Es speichert atomar nur den letzten Status je freigeschaltetem Gerät.
Keine öffentliche Leseansicht, kein gemeinsames Schreibkennwort für alle Geräte.

Am 28. September 2026 auf PHP 8.5.10 bestätigt: privater Statusordner beschreibbar,
Timer aktiv, Wiedergabe-Lebenszeichen vorhanden. Nach Aktivieren von CGIPassAuth
wurde die authentifizierte Statusübertragung erfolgreich bestätigt
(`last_status_success` gesetzt, `report_error: null`). Feed weiterhin unkonfiguriert.
Temporäre Diagnose-Dateien `check.php` und `auth-check.php` nach Prüfung entfernen.
Der lokale Windows-Rechner hat aktuell kein PHP-CLI.
Quelle für Tokenvergleich: https://www.php.net/manual/en/function.hash-equals.php

## Verbleibende Inbetriebnahme

1. FTP-Ziel und privates Hosting-Verzeichnis bestimmen; separaten Feed und Empfänger
   einrichten, ohne den vorhandenen FTP-Spiegel oder dessen Löschregeln zu verändern.
2. Paketproduzent an eine eingefrorene Quelle aktueller Daten anschließen. Der lokale
   Export alleine ist noch kein laufender Publikationsprozess.
3. HTTPS-Feed und Status-Endpunkt prüfen, Geräte-ID/Token provisionieren, URLs aktivieren.
4. Hängererkennung, Offline-Rendererprobe und Rollback, Aufräumen alter Pakete und
   verlässliche Uhrzeit beim Offline-Kaltstart vervollständigen.
5. Erst danach reproduzierbare Gesamtinstallation und Bereinigungslauf auf einer
   separaten Image-Vorlage testen. Das eingerichtete Gerät nicht ungefragt bereinigen.
