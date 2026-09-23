# Paketdownload-Labor

Stand: 23. September 2026. Getrennte Teststufe nach dem lokalen Folienwechsel.
**Nicht mit der laufenden Anzeige verbunden; kein produktiver Feed wird angefasst.**

## Implementiert

- Feedstruktur `latest.json`, `releases/<id>/manifest.json` und
  `releases/<id>/content/auszeit-display/...` gemäß Schnittstellenentwurf.
- Schema-, Playlist-, Zeitstempel-, Pfad- und Größenprüfung. Kein Lesen beliebiger
  Verzeichnisse, keine ZIP-Extraktion, keine durch ein Manifest vorgegebenen Fremd-URLs.
- Streamingdownload mit SHA-256 und exakten Größen, Netzwerk-Zeitlimits,
  höchstens 50 MiB je Datei, 512 MiB je Paket, 2.000 Dateien, 1 MiB JSON,
  verbleibender Speicherreserve von 1 GiB.
- HTTPS mit Standard-Zertifikatsprüfung und abgewiesenen Redirects. Nur im
  expliziten Labor darf unverschlüsseltes HTTP an die literale Adresse
  `127.0.0.1` verwendet werden. Keine Änderung am Gastnetz oder Router.
- Separater Stagingbereich; Dateien werden vor Aktivierung vollständig geprüft.
  Releaseverzeichnis und `active.json` werden auf demselben Dateisystem umbenannt.
  Auf Linux werden Dateien und Verzeichnisse mit fsync dauerhaft geschrieben.
- Automatisch freigegebene Prozesssperre verhindert parallele Schreiber.
  Wiederholte Release-IDs dürfen keine veränderten Inhalte erhalten.
- `active.json` enthält aktiven und vorherigen Stand samt Manifesthash. Vorhandene
  Releaseverzeichnisse werden bei Wiederverwendung erneut vollständig geprüft.
- Bei Fehlern vor dem Zeigerwechsel bleibt der alte Stand aktiv; fehlgeschlagene
  aktuelle Stagingverzeichnisse werden entfernt. Kein Löschen älterer Releases.

`active.json` ist hier nur der **Aktivierungszeiger des Testbestands**, keine
Umschaltung des Browserdiensts. Ein vollständiger Download beweist noch keine
korrekte Darstellung, vollständige HTML/CSS-Abhängigkeitsanalyse oder semantische
Aktualität der gelieferten Inhalte. Diese Prüfungen und die Integration folgen.

## Durchführung auf dem Player

Windows-PowerShell, außerhalb der SSH-Sitzung:

```powershell
scp -r -i "$env:USERPROFILE\.ssh\auszeit-player" "C:\Users\marku\OneDrive\02_ChatGPT Orga\06_Auszeit DS\player\update_test" auszeit@192.168.178.55:~/
```

Auf dem Anzeige-Pi als `auszeit`, **ohne sudo**:

```sh
python3 ~/update_test/exercise.py
```

Python 3.11 oder neuer, ausschließlich Standardbibliothek. Jeder Lauf erstellt
ein eigenes kleines Unterverzeichnis unter
`~/.local/state/auszeit-update-lab/run-...` und nennt dessen Pfad. Es wird kein
Dienst installiert und kein existierender Inhaltsstand überschrieben. Der
Inhaltsserver-Hostname `auszeit` wird vom Testprogramm ausdrücklich abgewiesen.

Der Test erstellt synthetisches HTML und CSS und liefert es über einen temporären
Loopback-HTTP-Server mit zufälligem freien Port. Erwartete sechs Schritte:

1. Paket `demo-1` vollständig laden und im Testbestand aktivieren.
2. Manipulierte CSS-Datei mit falscher Prüfsumme zurückweisen.
3. Paket mit fehlender CSS-Datei zurückweisen.
4. Vorzeitig abgebrochenen Dateidownload zurückweisen.
5. Gültiges Paket `demo-2` aktivieren; `demo-1` bleibt als vorheriger Stand erhalten.
6. Testserver abschalten, fehlgeschlagenen Updateversuch durchführen und den
   Testbestand neu öffnen. Beide gespeicherten Stände offline erneut prüfen.

Am Ende muss `PASS: Alle 6 Downloadtests bestanden. Laufende Anzeige unveraendert.`
erscheinen. Die Folien A/B/C sollen parallel weiterlaufen.

## Tests auf Windows

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_player_update.py -v
```

Zusätzlich getestet: fehlender Speicherplatz, Manipulation des gespeicherten
Bestands, falscher Manifesthash, doppelte JSON-Schlüssel, unzulässige Dateipfade,
ungültige Playlist, konkurrierende Schreiber und simulierte Unterbrechung vor
`os.replace` des Aktivierungszeigers. Der letzte Test ersetzt keinen realen
Stromausfalltest auf der SD-Karte. Windows prüft die Logik, Linux-spezifische
Dateisystempersistenz muss am Player getestet werden.

## Noch offen

- Anbindung an die sichtbare Wiedergabe und Wechsel nur an einer Foliengrenze.
- Prüfung aller HTML-/CSS-/Font-/Bildabhängigkeiten und Offline-Rendererprobe.
- Probestand, Rückkehr nach Wiedergabefehlern, Quarantäne fehlerhafter Releases.
- Periodischer Update-Dienst, Fehlerstatus und Aufräumen verwaister Stagingreste
  nach Stromausfall bzw. alter Releases mit Schutz von aktivem/vorherigem Stand.
- Produktiver HTTPS-Feed und dessen Zertifikats-/Netzwerktests. Aktuell wird nur
  Loopback-HTTP im Labor tatsächlich übertragen; keine Live-Webspace-Verbindung.
- Offline-Kaltstart des gesamten Players, Uhrvertrauen, Telemetrie und Imagebau.

Kein Nachweis von produktiver Offline-Wiedergabe allein durch diese sechs Tests.
Der nächste Schritt verbindet geprüfte Pakete mit der bestehenden Anzeige.
