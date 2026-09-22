# Lokaler Wechseltest

Eigenständiger Prototyp für `auszeit-player-01`, ausschließlich synthetische Folien.
Kein Inhaltsdownload, kein Manifestverbraucher, keine Telemetrie, keine Änderung
am Inhaltsserver. Python-Standardbibliothek; keine neuen Python-Pakete nötig.

## Testablauf

Der erste Browserabruf startet einen gemeinsamen Testzeitraum für diesen
Serverprozess. `/healthz` startet den Zeitraum nicht.

| Zeit ab erstem Abruf | Erwartete Anzeige |
|---|---|
| 0 bis etwa 20 Sekunden | A (grün) |
| etwa 20 bis 40 Sekunden | B (rot) |
| etwa 40 bis 60 Sekunden | C (blau) |
| etwa 60 bis 65 Sekunden | nochmals A |
| ab 65 Sekunden | neutrale Auszeit-Ersatzseite |

Zusätzlich enthält die Testplaylist einen bereits abgelaufenen Eintrag, der nie
ausgewählt werden darf. B wird erst nach 20 Sekunden gültig. Die letzte Anzeige
von A wird beim Ablauf unterbrochen, obwohl ihre 20 Sekunden noch nicht um sind.
Prüftakt 500 ms zuzüglich lokaler Ladezeit; keine harte Echtzeitgarantie.
Die Ersatzseite bleibt absichtlich stehen. Ein Browserneustart setzt die Frist
nicht zurück; ein Neustart des Python-Diensts beginnt einen neuen Test.

Der Browser lädt über HTTP von `127.0.0.1:8080`, alle Dateien liegen auf dem Pi.
Es gibt genau einen iframe, eine feste Routenliste und keine Verzeichnisfreigabe.
Bei API-Ausfall wird die schon geladene lokale Ersatzseite sichtbar. Polling setzt
sich fort und kann nach Dienstwiederkehr automatisch wieder Folien anzeigen.
Die Folien sind sandboxed, externe Netzwerkressourcen per CSP ausgeschlossen.

## Auf Windows prüfen

Aus dem Repository:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_player_local.py -v
.\.venv\Scripts\python.exe player/local_test/server.py --port 8765
```

Danach im Browser `http://127.0.0.1:8765/` öffnen. Andere Browser/Tests teilen
denselben Zeitraum. `--scenario cycle` wählt eine endlose A/B/C-Rotation.

## Auf dem Anzeige-Pi installieren

Voraussetzung ist die bereits eingerichtete Grafiksitzung aus
`docs/PLAYER_SETUP_PROGRESS.md`, insbesondere der Browser-Benutzerdienst.
Der Installer bricht bei anderem Hostnamen als `auszeit-player-01` ab.
Der Paketinhalt ist bereits in Git versioniert; keine Geheimnisse übertragen.

Im Windows-PowerShell-Fenster (außerhalb einer SSH-Sitzung):

```powershell
scp -r -i "$env:USERPROFILE\.ssh\auszeit-player" "C:\Users\marku\OneDrive\02_ChatGPT Orga\06_Auszeit DS\player\local_test" auszeit@192.168.178.55:~/
```

Dann über SSH/Connect auf dem Anzeige-Pi:

```sh
bash ~/local_test/install.sh
```

Dateien werden nach `/opt/auszeit-player-test` kopiert, als root-eigene
schreibgeschützte Anwendungsdateien. Der Systemdienst läuft als `player`, bindet
nur Loopback und startet ohne Netzwerkabhängigkeit. Nach bestandenem Healthcheck
legt der Installer ausschließlich den Browser-Drop-in `local-test.conf` an und
startet die lokale Grafiksitzung neu. Der ursprüngliche Browserdienst, die Uhr und
der SSH-/Connect-Zugang bleiben erhalten. Kein Pi-Neustart erforderlich.

## Wiederholung und Dauerbetrieb

Test wiederholen:

```sh
sudo systemctl restart auszeit-player-test.service
```

Nach erfolgreichem Ablauf-/Fallbacktest endlos A/B/C zeigen:

```sh
printf '%s\n' 'AUSZEIT_TEST_SCENARIO=cycle' | sudo tee /etc/default/auszeit-player-test
sudo systemctl restart auszeit-player-test.service
```

Für den Ablauf-Test den Wert auf `expiry` setzen und den Dienst neu starten.
Der Installer überschreibt diese Wahl bei Wiederholung nicht.

## Diagnose und Rückkehr zur Uhr

```sh
systemctl status auszeit-player-test.service --no-pager
sudo journalctl -u auszeit-player-test.service -n 40 --no-pager
```

Rückkehr zur bisherigen Uhr ohne Löschen von Dateien:

```sh
sudo mv /home/player/.config/systemd/user/auszeit-browser.service.d/local-test.conf /home/player/.config/systemd/user/auszeit-browser.service.d/local-test.conf.disabled
sudo systemctl disable --now auszeit-player-test.service
sudo systemctl restart getty@tty1.service
```

Nur für eine installierte aktive Testkonfiguration ausführen. systemd lädt nur
Drop-ins mit Endung `.conf`. Eine erneute Installation aktiviert den Test wieder.

## Umfang und offene Grenzen

Der Prototyp verwendet die vereinbarten Zeitfelder und eine synthetische
In-Memory-Playlist. Ein Dateieditor, persistente Playlist, Feed-Download,
Prüfsummen, Releaseaktivierung und Offline-Kaltstart mit echten Inhalten folgen
separat. Bei Neustart des Diensts beginnen absichtlich neue relative Testfristen.
Absolute Zeit wird hier als synchronisiert vorausgesetzt; Behandlung einer
unzuverlässigen Uhr und Sommerzeitgrenzen braucht der spätere echte Player.
Ein Browserprozess-Neustart ist vorhanden; Renderer-Hänger werden noch nicht erkannt.

Vor endgültiger Integration muss auch ein aktiver Ablauf beim Serviceausfall
und unter hoher Last geprüft werden. Der lokale HTTP-Dienst ist ein begrenzter
Loopback-Prototyp, keine öffentlich erreichbare Webanwendung.
