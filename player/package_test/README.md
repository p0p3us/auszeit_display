# Gespeicherte Testpakete auf dem Fernseher

Diese Stufe verbindet `update_test` mit dem flackerfreien `local_test`.
Nur synthetische Testinhalte; Inhaltsserver, FTP und Webspace bleiben unverändert.

## Installation

In Windows-PowerShell, außerhalb von SSH:

```powershell
scp -r -i "$env:USERPROFILE\.ssh\auszeit-player" "C:\Users\marku\OneDrive\02_ChatGPT Orga\06_Auszeit DS\player" auszeit@192.168.178.55:~/
```

Auf dem Anzeige-Pi als `auszeit`:

```bash
bash ~/player/package_test/install.sh
```

Der Installer prüft den Hostnamen, installiert Code root-eigen unter
`/opt/auszeit-player-package-test` und lädt Teststand 1 über einen temporären
Loopback-Feed mit dem geprüften Downloader. Der Feed wird danach beendet.
Bei erneuter Installation bleibt ein vorhandener, gültiger Testbestand erhalten.
Der Speicher liegt unter `/var/lib/auszeit-player-package-test`, Eigentümer `player`.
Keine vorhandenen Laborverzeichnisse werden gelöscht oder übernommen.

Ein neuer Dienst `auszeit-player-packages.service` läuft als `player` mit
schreibgeschütztem Dateisystem und bedient nur `127.0.0.1:8081`. Der Browser erhält
ein zusätzliches Drop-in `packages-test.conf`. Dieses überschreibt alphabetisch
die bisherige URL aus `local-test.conf`; andere lokale Drop-ins vorab berücksichtigen.
Der Neustart von getty startet auch die grafische Sitzung neu. Danach sollen
Folien A/B/C mit „Inhaltsstand 1“ jeweils 20 Sekunden lang erscheinen.

## Folgende Abnahmeschritte

Nach Sichtprüfung von Stand 1 auf dem Pi:

```bash
cd /opt/auszeit-player-package-test
sudo -u player python3 -m player.package_test.publish 2
```

Die aktuelle Folie soll ihre Laufzeit beenden. An der nächsten Foliengrenze
erscheint Stand 2, ohne Browserneustart und ohne Aufblitzen der Ersatzseite.
Bei jeder Übernahme werden Manifest und alle Dateien erneut geprüft. Dateipfade
enthalten die Release-ID; relative CSS-Verweise bleiben im selben Stand.
Die zuvor bedienten Dateien bleiben für auslaufende Frames erreichbar.

Danach absichtlich ungültiges Paket anbieten:

```bash
sudo -u player python3 -m player.package_test.publish broken
```

Erwartet: Meldung „Paket abgewiesen“ und Exitcode 1. Stand 2 rotiert weiter.
Die Meldung ist bei diesem absichtlichen Fehlertest das richtige Ergebnis.
Ein Neustart des Players soll Stand 2 wieder laden, ohne einen Feed zu starten.
Ein echter Kaltstart ohne WLAN ist als eigener Hardwaretest noch durchzuführen.

Diagnose:

```bash
systemctl status auszeit-player-packages.service --no-pager
curl -s http://127.0.0.1:8081/api/state
```

## Rückkehr zum bisherigen lokalen Wechseltest

```bash
sudo rm -f /home/player/.config/systemd/user/auszeit-browser.service.d/packages-test.conf
sudo systemctl restart getty@tty1.service
sudo systemctl disable --now auszeit-player-packages.service
```

Nur das neue URL-Drop-in wird entfernt. `local-test.conf`, der bisherige Dienst
auf Port 8080 und beide Paketstände bleiben erhalten.

## Grenzen dieser Teststufe

- Unterstützt werden die hier erzeugten HTML-/CSS-Testpakete mit relativen Assets.
  Echte Exportfolien verwenden auch `/auszeit-display/...`; deren sichere
  Zuordnung zu einem Release erfordert noch die im Schnittstellenentwurf
  vorgesehenen getrennten Inhalts-Origins. Keine beliebigen Exportpakete einspeisen.
- Hashprüfung bestätigt Dateivollständigkeit, noch keine erfolgreiche Darstellung.
  Rendererprobe, Wiedergabebestätigung und Rollback nach Rendererfehlern fehlen.
- Beim Start mit beschädigtem aktivem Stand kann ein vollständig geprüfter
  vorheriger Stand angezeigt werden. Das ist noch kein bestätigter Produktionsrollback;
  der gespeicherte Aktivierungszeiger bleibt zur Diagnose unverändert.
- Der neue Zeiger wird an Foliengrenzen gelesen. Ein ungültiger neuer Stand wird
  für die Laufzeit des Diensts nicht erneut versucht; die bisherige Rotation läuft.
- Statische Testfolien haben kein Ablaufdatum. Gültigkeitsauswahl und Browser-
  Ablauftimer werden wiederverwendet; Uhrvertrauen bei Offline-Kaltstart bleibt offen.
- Keine periodischen Downloads, Telemetrie, Bereinigung alter Pakete oder
  Änderungen an WLAN, Connect, Zugangsdaten und Imagevorbereitung.

Die Kopie unter `~/player` dient nur dem Transfer. Ausgeführt wird danach
ausschließlich der installierte Code unter `/opt/auszeit-player-package-test`.
