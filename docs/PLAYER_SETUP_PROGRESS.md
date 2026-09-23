# Anzeige-Pi – eingerichteter Stand

Stand: 22. September 2026. Die folgenden Ergebnisse wurden vom Benutzer am
separaten Player ausgeführt und zurückgemeldet; kein direkter SSH-Zugriff durch
den Agenten. Inhaltsserver `auszeit` und produktiver Webspace blieben unverändert.
Dieses Protokoll ergänzt die ältere Planung in `DISPLAY_PLAYER.md`.
Schnittstellenentwurf: `PLAYER_INTERFACE_DRAFT.md`.

## Gerät und Software

| Punkt | Beobachteter Stand |
|---|---|
| Hostname | `auszeit-player-01` |
| Hardware | Raspberry Pi 4 Model B, 2 GB RAM (1,8 GiB sichtbar) |
| Speichermedium | microSD nominal 16 GB; vom Benutzer zum Löschen freigegeben |
| Netzwerk | Aktuell Heim-WLAN; später Café-Gast-WLAN mit SSID/Passwort, ohne Anmeldeseite |
| OS | Raspberry Pi OS Lite 64-bit, Debian 13 Trixie |
| Kernel nach Update | `6.18.50+rpt-rpi-v8` |
| Grafik | labwc `0.20.1`, wlroots `0.20.2` |
| Browser | Chromium `153.0.8010.52` |
| Anzeige | Browserfläche 1920×1080, Testseitenrand an allen Seiten vollständig |
| Zeit | `Europe/Vienna`, NTP aktiv und synchronisiert |
| Wartung | Benutzer `auszeit`, SSH mit separatem Ed25519-Schlüssel |
| Anzeige | Benutzer `player`, keine sudo-Rechte, keine Passwortanmeldung eingerichtet |
| Fernzugriff | Raspberry Pi Connect Lite `2.12.2`, dem Benutzer `auszeit` zugeordnet |

Die Versionsnummern dokumentieren den beobachteten Stand, keine dauerhaft
festzuschreibenden Sicherheitsupdates. Image-Dateiname, Image-SHA-256 und eine
vollständige Paketliste wurden noch nicht erfasst. Daher noch kein reproduzierbarer
automatisierter Build und noch kein wiederverwendbares Image.

## Bisherige Einrichtung

1. Imager: Pi 4, OS Lite 64-bit/Trixie, Österreich, deutsche Tastatur,
   `Europe/Vienna`, Hostname und Wartungsbenutzer, Heim-WLAN, SSH-Schlüssel.
2. Grundsystem mit `sudo apt update` und `sudo apt full-upgrade` aktualisiert.
3. Pakete mit `--no-install-recommends` installiert:
   `labwc chromium chromium-sandbox dbus-user-session wlr-randr
   fonts-dejavu-core fonts-liberation`.
4. `player` mit Home `/home/player` und Shell `/bin/bash` eingerichtet.
5. Lokale HTML-Testseite `/home/player/test.html`: Auszeit-Schriftzug, laufende
   Uhr, Anzeige der Browserfläche und goldener Rand. Keine echte Playlist.
6. Browser als systemd-Benutzerdienst statt direktem Autostart eingerichtet.
7. Connect Lite aktiviert, Anmeldung interaktiv im Browser vorgenommen.

## Maßgebliche Konfiguration auf dem Player

`/etc/systemd/system/getty@tty1.service.d/autologin.conf`:

```ini
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin player --noclear %I $TERM
```

`/home/player/.bash_profile`:

```sh
if [ "$(tty)" = "/dev/tty1" ]; then
    export XDG_SESSION_TYPE=wayland
    exec dbus-run-session -- labwc >"$HOME/display.log" 2>&1
fi
```

`/home/player/.config/labwc/autostart` (ausführbar, Eigentümer `player`):

```sh
#!/bin/sh
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
systemctl --user import-environment WAYLAND_DISPLAY XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS
systemctl --user daemon-reload
systemctl --user restart auszeit-browser.service &
```

`/home/player/.config/systemd/user/auszeit-browser.service`:

```ini
[Unit]
Description=Auszeit kiosk browser
StartLimitIntervalSec=0

[Service]
Type=exec
ExecStart=/usr/bin/chromium --ozone-platform=wayland --kiosk --no-first-run --noerrdialogs --user-data-dir=/home/player/.config/chromium file:///home/player/test.html
Restart=always
RestartSec=5
TimeoutStopSec=10
KillMode=control-group
```

Dieser Dienst wird erst von labwc gestartet, nicht vor Verfügbarkeit der
Grafiksitzung. Der explizite Buspfad verbindet `systemctl --user` mit dem
systemd-Benutzermanager trotz der privaten D-Bus-Sitzung von labwc.
Die aktuelle unbegrenzte Wiederholung ist ein Aufbauzustand; für wiederholte
Fehler sind Backoff, Fallback und Status im eigentlichen Player geplant.

`/etc/chromium/policies/managed/auszeit-player.json`:

```json
{"TranslateEnabled": false}
```

Für den unbeaufsichtigten Fernzugang:

```sh
sudo apt install rpi-connect-lite
sudo loginctl enable-linger auszeit
rpi-connect on
rpi-connect signin
```

Die letzten beiden Befehle als `auszeit`, ohne sudo. Verknüpfung pro Gerät
interaktiv durchführen; keine Anmeldelinks oder Tokens im Repository speichern.
Zwei-Faktor-Authentifizierung wurde empfohlen, ihre Aktivierung ist noch nicht bestätigt.

Für die Aufbauphase wurde folgende sudo-Einstellung angeleitet, aber nicht
durch eine gesonderte Ausgabe bestätigt:
`/etc/sudoers.d/90-auszeit-setup`, Inhalt
`Defaults:auszeit timestamp_timeout=120`, root:root, Modus 0440, vor Installation
mit `visudo -cf` geprüft. Vor Übergabe/Image-Erstellung wieder entfernen.

## Behobene Probleme

- Anfangs `throttled=0x50005`: aktive und gespeicherte Unterspannung/Drosselung.
  Nach Korrektur der Versorgung meldete der Benutzer wiederholt `0x0`.
  Die genaue Netzteil-/Kabeländerung ist noch nicht dokumentiert.
- Chromium startete zunächst nicht (Crashpad-Verzeichnisfehler, Zygote-Abbruch).
  Der ursprüngliche `install -d`-Befehl konnte `.config` als root-Elternverzeichnis
  erzeugen. Nach expliziter Anlage/Korrektur von `.config`, `.config/chromium`,
  `.cache`, `.cache/chromium` mit Eigentümer player:player und Modus 0700 startete
  die Anzeige. In zukünftigen Installationsskripten alle Eltern explizit anlegen.

## Bestätigte Tests

- Vollbild mit laufender Uhr; 1920×1080, kein sichtbarer Overscan.
- Etwa fünf Minuten Testbetrieb: 463 MiB RAM genutzt, 1,3 GiB verfügbar,
  kein Swap genutzt, 54,5 °C, `throttled=0x0`.
- Freier Platz nach Grafikinstallation: 9,2 GB (Ausgabe von `df -h`).
- Browser-Hauptprozess gezielt mit SIGKILL beendet: automatische Rückkehr nach
  ungefähr sechs Sekunden; `NRestarts=1`, `ActiveState=active`, `SubState=running`.
- Pi-Neustart: Testseite erscheint ohne manuelle Anmeldung.
  `systemd-analyze time`: Kernel 2,308 s, Userspace 22,635 s, zusammen 24,944 s.
  Diese Messung enthält nicht die gesamte Firmware-/Browserstartzeit.
- Connect nach Neustart ohne vorherige SSH-Anmeldung wieder erreichbar.
  Eine unterbrochene Browserkonsole benötigt erwartungsgemäß „Reconnect“.

Test über Smartphone-Mobilfunk wurde vorgeschlagen, aber noch nicht bestätigt.
Ebenso offen: Zugriff aus dem Café-Gastnetz, Prüfung unter echten Folien,
Langzeittest, Offline-Kaltstart, Renderer-Hänger und Stromausfalltests.

## Lokale Tests und nächste Schritte

Nachtrag 23. September: Der Benutzer hat den lokalen Wechseltest, die Endlosschleife
nach Neustart und anschließend den korrigierten flackerfreien Folienwechsel über
mehr als fünf Minuten am Pi bestätigt. Zwei abwechselnd sichtbare iframes verhindern
das kurzzeitige Aufblitzen der Ersatzseite während des Ladens. Der Installer prüft
die geschützte Browserdienst-Datei inzwischen mit sudo und meldet fehlende Voraussetzungen.

Ein WLAN-Ausfall wurde lokal durch Neuverbinden behoben. Energiesparen war aktiv;
es wurde im aktuellen Heim-WLAN-Profil deaktiviert und sofort auf `off` gesetzt.
Das beweist noch nicht die Ursache und noch keine dauerhafte Stabilität. Für das
spätere Café-Profil muss die Einstellung gesondert übernommen werden.

Das separate Labor `player/update_test/` testet nun geprüften Paketdownload und
einen atomaren Aktivierungszeiger in einem isolierten Testbestand. Es schaltet
die laufende Anzeige nicht um. Alle sechs Prüfungen wurden vom Benutzer auf dem
Anzeige-Pi erfolgreich bestätigt (Testbestand `run-2ok5shj2`).

Die folgende Stufe `player/package_test/` verbindet synthetische geprüfte Pakete
mit der sichtbaren Wiedergabe auf einem separaten Loopback-Dienst (Port 8081).
Neue Stände werden an Foliengrenzen übernommen, relative Assets sind über die
Release-ID gebunden. Bisheriger Wechseltest auf Port 8080 bleibt für Rückkehr
erhalten. Der Benutzer hat folgende Schritte am Pi bestätigt:

- Stand 1 rotiert sauber; beim Update endet B aus Stand 1 regulär und danach
  beginnt A aus Stand 2, ohne Schwarzbild oder Ersatzseite.
- Ein absichtlich beschädigtes Paket wird abgewiesen; Stand 2 läuft ungestört weiter.
- Nach Neustart startet Stand 2 selbstständig aus dem lokalen Speicher.
- Auch nach Neustart mit FRITZ!Box-Internetsperre erscheint Stand 2. WLAN und
  Heimnetz blieben verfügbar; kein Nachweis eines Starts ohne WLAN oder eines
  Kaltstarts nach Stromtrennung. Nach Aufheben der Sperre ist Connect wieder erreichbar.

Beim Browserstart blitzte die Ersatzseite kurz auf. Die Playeroberfläche hält sie
nun bis zum Ergebnis des ersten Ladevorgangs verborgen; bei leerem Plan oder
Ladefehler wird sie weiterhin eingeblendet. Während des erfolgreichen Ladens ist
nur der ruhige Hintergrund sichtbar. Hardwareabnahme dieser Korrektur steht aus.

Der lokale Wechseltest unter `player/local_test/` ist inzwischen im Repository
implementiert und auf Windows getestet: synthetische A/B/C-Folien, 20 Sekunden,
Gültigkeitsintervalle, Ersatzseite und Loopback-HTTP-Dienst. Acht neue Tests und
die vollständige Suite (48 Tests) bestanden. Testfolie und Ablauf zur Ersatzseite
wurden im Browser geprüft; Textgrenzen zusätzlich bei 1920×1080 kontrolliert.
Installation und Abnahme des lokalen Wechseltests am Anzeige-Pi sind inzwischen
bestätigt, siehe Nachtrag oben. Mit der Paketwiedergabe bestehen aktuell 67 Python-
und zehn Browser-Tests auf Windows; auch die Bash-Syntax des neuen Installers
wurde geprüft.
Die Anleitung einschließlich Rückkehr zur Uhr steht in `player/local_test/README.md`.

Noch offen sind persistente echte Playlist, vollständiger Download, atomare Aktivierung,
Rollback, Gültigkeitsregeln, Statusmeldungen/Empfänger, Wiedergabe-Lebenszeichen,
begrenzte Logs, endgültiges Bootbild und Ausblenden des Mauszeigers.
Raspberry Pi Connect ist Fernwartung, kein Ersatz für diese Komponenten.

## Voraussetzungen für ein wiederverwendbares Image

Vor Image-Erstellung einen separaten dokumentierten Bereinigungslauf entwickeln
und testen. Kein rohes Abbild des angemeldeten Geräts als Vorlage weitergeben.

- Basis-OS mit Dateiname und SHA-256 erfassen; Installationsskripte und Paketstand
  versionieren, Aktualisierungspfad und Wiederherstellung beschreiben.
- Gerätespezifische SSH-Hostschlüssel, Maschinen-ID, Hostname und Geräte-ID bei
  Erststart neu erzeugen. Administrationszugriff je Gerät provisionieren.
- Heim-/Café-WLAN-Zugangsdaten, Connect-Anmeldestatus, Geräte-/Status-Tokens,
  Browserprofile, Shell-Historien und private Betriebsdaten nicht ins Basisimage.
- Das temporäre sudo-Timeout zurücknehmen. Keine privaten Windows-SSH-Schlüssel
  auf den Pi übertragen. Auch erlaubte öffentliche Wartungsschlüssel bewusst
  als Provisionierung behandeln, nicht als unausgesprochene Image-Vorgabe.
- Connect je Gerät neu verknüpfen; Bereinigung der Vorlage darf nicht ungewollt
  die bereits genutzte Instanz aus der Fernwartung entfernen.
- Vorlage auf einem zweiten Datenträger prüfen: eindeutige Identitäten,
  Erststart, Stromausfall, Netzverlust und Wiederanmeldung.

Dieses Dokument führt keine Bereinigung, kein Flashen und kein Deployment aus.

## Offizielle Referenzen

- [Raspberry Pi OS und Updates](https://www.raspberrypi.com/documentation/computers/os.html)
- [Kiosk-Grundlagen](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/)
- [labwc-Konfiguration](https://labwc.github.io/getting-started.html)
- [systemd-Dienste](https://manpages.debian.org/trixie/systemd/systemd.service.5.en.html)
- [Connect und dauerhaft verfügbare Fernkonsole](https://www.raspberrypi.com/documentation/services/connect.html)
