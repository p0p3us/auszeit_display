# Lokaler Paketexport mit variabler Playlist

Stand 28.09.2026. Implementierung: `python -m player.export_feed`.
Keine Änderungen an Serverdiensten, bisherigen Generatoren, FTP oder Webspace.

## Eingaben und Grenzen

`--snapshot` bezeichnet eine unveränderliche Quellkopie mit `templates/`, `data/`,
`static/` und `resources/`. Die sichere Erzeugung dieser Kopie im späteren
Publikationslauf ist noch anzubinden. Nicht gleichzeitig aktualisierte Produktions-
verzeichnisse als Snapshot behandeln. Der Export führt keine Netzwerkabrufe aus.
Er liest ausgewählte JSON-Dateien und rendert die vorhandenen Templates neu.
Vorhandene generierte HTML-Seiten und `menue_status.json` werden nicht als Beweis
für aktuelle Inhalte verwendet. Der alte öffentliche Export bleibt unverändert.

Unterstützte Kategorien aus dem bisherigen öffentlichen Export:

- Namenstag nur bei vorhandenen Namen, Bauernregel nur bei echtem Regeltext,
  Weisheit und Zitat nur bei gültigem ausgewähltem Datensatz.
- Menüübersicht und Wochenschmankerl nur bei echten Daten und aktuellem Zeitraum.
  Kein Ersatztext, wenn das Wochenschmankerl fehlt.
- Heute-Menü bis 14:00 exklusiv, Morgen-Menü ab 14:00 inklusiv bis Mitternacht;
  fehlende Einträge entfallen. Der Wechsel ist über `--menu-switch-at` konfigurierbar.
- Termine: alle gültigen Einträge, auch 0, 2, 6 oder mehr. Fehler werden pro Termin
  behandelt. Nach Ende des Veranstaltungstags entfällt die Folie spätestens.
- News: jede Meldung mit Titel; Wetter: Morgen, Morgen-Deluxe und 5-Tage-Vorschau.
  News-/Wetterquellen müssen vom aktuellen Tag stammen. Fehlende Teile entfallen.

Upload-HTML gehört bisher nicht zum öffentlichen Export und wird nicht blind aus
dem Server-Dateibaum übernommen. Dessen Auswahl und Abhängigkeiten benötigen einen
eigenen Adapter. Die Regel „fehlende Inhalte auslassen“ gilt auch dafür.

Vorläufige Reihenfolge: Namenstag, Bauernregel, Weisheit, Zitat, Menüs, Termine,
News, Wetter. Jeweils 20 Sekunden. Reihenfolge und längerfristige Gültigkeitsregeln
sind vor produktiver Anbindung noch abzustimmen; die lokale Vorbereitung veröffentlicht
nichts. `--expires-at` muss ausdrücklich angegeben werden und begrenzt alle Folien.
Tagesfolien und News/Wetter enden spätestens um Mitternacht. Zeitrechnung im CLI
verwendet Europe/Vienna einschließlich Sommerzeit. Die Windows-Zeitzonendaten
`tzdata` sind in `requirements.txt` festgehalten; Linux nutzt die OS-Zeitzonendaten.

## Dateien und fehlende Inhalte

HTML-Assetverweise und CSS-URLs werden rekursiv eingesammelt. Ein fehlendes Asset
entfernt die betroffene Folie vollständig. Unabhängige Folien bleiben erhalten.
Externe Ressourcen, CSS-Imports und nicht unterstützte eingebettete Inhalte werden
abgewiesen. In der Paketkopie werden Pfade relativ gebunden. Das Inline-Layoutskript
des Termin-Templates wird dort als eigene JS-Datei abgelegt, passend zur Player-CSP.
Dies ist eine Unterstützung der vorhandenen Templates, kein allgemeiner Crawler
für beliebiges HTML oder dynamisch nachgeladene JavaScript-Ressourcen. Vor einem
Produktionspaket bleibt die Offline-Rendererprüfung erforderlich.

Ausgaben: `latest.json`, unveränderliches Release mit Manifest/Hashes und
`report.json` mit aufgenommenen IDs und Fehlergründen. Nur tatsächlich verwendete
Assets werden aufgenommen. Ziel muss neu sein, bestehende Ausgabe wird abgewiesen.
`latest.json` wird zuletzt geschrieben. Eine produktive atomare Veröffentlichung
auf dem Webspace ist noch ein eigener Schritt.

Leere Pakete sind gültig. Sie dürfen einen Stand mit inzwischen entfernten Inhalten
ersetzen. Die lokale Notfallgrafik gehört zum Player, nicht zur Inhaltsplaylist.
Bei einem Downloadfehler bleibt dagegen das alte gültige Paket erhalten.

## Aufrufbeispiel

Vom Repository-Hauptverzeichnis, Datum/Frist passend zum tatsächlichen Lauf wählen:

```powershell
.\.venv\Scripts\python.exe -m player.export_feed --snapshot "C:\Pfad\zur\eingefrorenen-Quellkopie" --output "C:\Pfad\zu\neuem-Paket" --expires-at "2026-09-29T00:00:00+02:00"
```

Kein fester Beispielpfad wird vom Programm selbst verwendet. Der Paketaufbau ist
mit variablen Terminzahlen, fehlendem Wochenschmankerl, fehlenden Bildern, alten
Quellen, Menüwechsel um 14:00 und leerem Paket einschließlich Wiederanlauf getestet.

## Regelmäßige Veröffentlichung auf dem Inhaltsserver

Auf `auszeit` aus dem Repository: `bash player/install_feed.sh`.
Der separate Dienst liest die vorhandene `config/publish.env`, verwendet aber als
festes Ziel ausschließlich `/auszeit-player-feed`. Bestehende Generatoren, Timer,
Webordner und Produktionsdaten werden nicht verändert. FTP verwendet wie der
bereits bestätigte Upload die bestehende unverschlüsselte Verbindung; Passwörter
werden nur als Prozessumgebung übergeben, nicht als Kommandozeilenargumente.

Lauf bei Minute 06 jeder Stunde und nach Boot. Der bisherige Export aktualisiert
die Quellen bei Minute 01; der Feed-Publisher stößt ihn nicht selbst an. Eine
Quellkopie wird vor/nach dem Kopieren per Prüfsummen verglichen; bei Änderungen
bricht der Lauf ab. Deshalb ist das kein Dateisystem-Snapshot mit Transaktionsgarantie.
Die nächste reguläre Ausführung versucht es erneut. Gesamtlauf maximal zehn Minuten.

Lokaler Pakettest und FTP-Rückleseprüfung gehen der Umbenennung von
`latest.json.uploading` nach `latest.json` voraus. Bei Fehlern vor dieser Umbenennung
bleibt der bisherige Paketzeiger erhalten. Lokale temporäre Kopien werden nach dem
Lauf entfernt; letzter Bericht unter `~/.local/state/auszeit-player-feed/last-publish.json`.
Nach erfolgreicher Veröffentlichung werden vollständige, bekannte Webspace-Releases
erst nach sieben Tagen entfernt. Geschützt bleiben neuer und unmittelbar vorheriger
Paketzeiger. FTP-Verzeichnisdatum und Manifestdatum müssen beide alt genug sein.
Die MLSD-Prüfung erlaubt nur die im Manifest erwarteten Dateien und Verzeichnisse;
unbekannte Dateien oder Links verhindern die Löschung. Fehlende MLSD-Unterstützung
oder Bereinigungsfehler werden im Bericht unter `cleanup.error` festgehalten und
machen eine zuvor erfolgreiche Veröffentlichung nicht rückgängig. Unvollständige
oder fremde Ordner werden nicht automatisch gelöscht. Player-Bereinigung siehe
`player/operations/README.md`.

Maximale Paketgültigkeit sieben Tage, zusätzlich gelten die kürzeren Folienfristen:
Tagesfolien/News/Wetter bis Mitternacht, Menüs bis Periodenende, Termine bis Ende
des Veranstaltungstags. Ein Ausfall des Inhaltsservers macht alte Quellen nicht
automatisch aktuell. Zwischen Mitternacht und dem ersten erfolgreichen neuen Lauf
können Tagesfolien fehlen; ohne andere gültige Folien erscheint das Notfallbild.

## Player aktualisieren (Darstellung)

Die beiden bestehenden Installer nehmen `emergency.png` und `emergency.css` mit.
Das Bild wird unverändert installiert und ohne Beschnitt im Seitenverhältnis 16:9
angezeigt. Es erscheint bei leerer/abgelaufener Playlist oder wenn keine nutzbare
Anzeige geladen werden kann; beim normalen Start bleibt es verborgen.
Der Paket-Installer behält einen vorhandenen Stand bei und akzeptiert nun auch
eine absichtlich leere Playlist als gesunden Dienstzustand.
