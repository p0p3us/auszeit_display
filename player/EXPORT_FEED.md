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

## Player aktualisieren

Die beiden bestehenden Installer nehmen `emergency.png` und `emergency.css` mit.
Das Bild wird unverändert installiert und ohne Beschnitt im Seitenverhältnis 16:9
angezeigt. Es erscheint bei leerer/abgelaufener Playlist oder wenn keine nutzbare
Anzeige geladen werden kann; beim normalen Start bleibt es verborgen.
Der Paket-Installer behält einen vorhandenen Stand bei und akzeptiert nun auch
eine absichtlich leere Playlist als gesunden Dienstzustand.
