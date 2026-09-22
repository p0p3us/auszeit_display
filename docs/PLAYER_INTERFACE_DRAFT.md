# Eigenständiger Player – Schnittstellenentwurf

Stand: 22. September 2026. **Entwurf, noch nicht implementiert oder veröffentlicht.**
Ergänzung zu `DISPLAY_PLAYER.md`; eingerichteter Gerätestand siehe
`PLAYER_SETUP_PROGRESS.md`. Dieser Entwurf verändert weder Inhaltsserver,
Generatoren, Webinterface noch FTP-Publikation.

## Befund aus dem lokalen Repository

- `scripts/export_public.sh` erzeugt einen temporären Export und gleicht ihn
  anschließend mit `public_export/` ab. Es exportiert HTML, CSS und Bilder.
- `scripts/publish_public_ftp.sh` überträgt diesen Bestand mit
  `lftp mirror -R --delete`. Die Veröffentlichung ist kein atomarer Wechsel
  eines gesamten Inhaltsstands. Leser können währenddessen gemischte Dateien sehen.
- Es werden weder Playlist noch vollständige Dateiliste mit Prüfsummen exportiert.
  `data/menue_status.json` wird ebenfalls nicht exportiert.
- Die vier Tagesmodule werden als `namenstag/index.html`,
  `bauernregel/index.html`, `weisheit/index.html`, `zitat/index.html` veröffentlicht.
  Weitere HTML-Dateien liegen unter `news/`, `weather/`, `menue/`, `termine/`.
  Nicht jede `index.html` ist eine Folie: Wetter erzeugt etwa eine Linkübersicht.
  Deshalb darf der Player nicht einfach alle HTML-Dateien abspielen.
- Templates und CSS verwenden wurzelabsolute Pfade wie
  `/auszeit-display/resources/images/logo.png`. Eine HTML-Datei allein und
  `file://` reichen für diese Folien nicht.
- `scripts/export_menue.py` erzeugt `uebersicht.html`, `wochenschmankerl.html`,
  `heute.html`, `morgen.html`. Die Statusmetadaten nennen 13:00 als Wechselzeit.
  Das ist ein Befund, noch keine bestätigte Playerregel. Das Datum bei `tomorrow`
  bezeichnet den Menütag, nicht automatisch den Tag, an dem geworben werden soll.
- Die versionierte `data/menue_status.json` ist eine veraltete Momentaufnahme
  mit einem früheren Samstagseintrag. Sie ist keine Quelle für den neuen Vertrag.
- `scripts/generate_termine.py` erzeugt durchnummerierte `termin-N.html` und
  entfernt nicht mehr benötigte Dateien. Dateinamen sind keine stabilen Event-IDs.

Der Live-Webspace konnte mit dem Recherchewerkzeug nicht gelesen werden.
Diese Befunde stammen aus lokalem Code und belegen nicht den aktuellen Livebestand.

## Ziel und Rollentrennung

Der bestehende Server erzeugt Inhalte. Der neue Player lädt sie ausschließlich
ausgehend über HTTPS, speichert geprüfte Stände lokal und spielt sie über einen
an Loopback gebundenen HTTP-Dienst ab. Er bekommt keine FTP- oder Inhalts-API-Schlüssel.

Für einen verbindlichen Inhaltsstand ist ein zusätzlicher Paketproduzent nötig.
Er muss auf einen eingefrorenen, vollständig erzeugten Export zugreifen können.
Ein Crawler über die sich ändernden Live-Dateien kann diesen Zusammenhang nicht
garantieren, auch wenn jede heruntergeladene Datei einzeln lesbar ist.

Zunächst Entwicklung mit synthetischen, lokal erzeugten Testpaketen. Später kann
ein separat freigegebener Exportadapter Pakete liefern. Sein Betrieb auf dem
Inhaltsserver und jede produktive Veröffentlichung benötigen einen eigenen Schritt.

**Keine neuen Pakete ungeprüft in den bestehenden FTP-Spiegel legen:** dessen
`--delete` könnte sie beim nächsten Lauf entfernen. Vorgesehen ist eine gesonderte
Basis-URL außerhalb dieses Spiegelziels, beispielsweise `/auszeit-player-feed/`.
Dieser Pfad ist lediglich vorgeschlagen und noch nicht angelegt.

## Vertrag v1: unveränderliche Releases

Vorgeschlagene Struktur unter der zukünftigen Feed-Basis-URL:

```text
latest.json
releases/<release-id>/manifest.json
releases/<release-id>/content/auszeit-display/...
```

`latest.json` enthält `schema_version` (1), `release_id`, einen relativen
`manifest_path` und `manifest_sha256` (64 kleine Hexzeichen). Es wird erst nach
vollständigem Upload und Überprüfung des Releases veröffentlicht. Der Zeiger muss
auf dem Webspace atomar ersetzt werden können; das ist vor Deployment zu testen.
Releases dürfen nach Veröffentlichung nicht verändert oder IDs wiederverwendet werden.

Das Manifest enthält:

| Feld | Vertrag |
|---|---|
| `schema_version` | Integer 1; unbekannte Version zurückweisen |
| `release_id` | Eindeutige ID, nur ASCII-Buchstaben, Ziffern, Bindestrich und Unterstrich |
| `generated_at` | RFC-3339-Zeitstempel mit Zeitzonenoffset |
| `timezone` | Für diesen Player `Europe/Vienna` |
| `files` | Vollständige Liste aller benötigten Dateien einschließlich indirekter CSS-, Bild-, Font- und Skriptabhängigkeiten |
| `playlist` | Geordnete Liste der Folien, keine Verzeichniserkennung |

Ein Dateieintrag hat `path`, `bytes` und `sha256`. `path` ist ein eindeutiger
relativer POSIX-Pfad ab `content/`, z. B. `auszeit-display/weisheit/index.html`.
Keine absoluten URLs, führenden Slashes, Backslashes, Punktsegmente, Querys,
Fragmente, doppelten Pfade oder URL-kodierten Pfadtricks. SHA-256 bezieht sich auf
die unveränderten Dateibytes. HTTPS prüft die Gegenstelle; ein Hash allein ist
keine digitale Signatur und schützt nicht vor einem kompromittierten Herausgeber.

Ein Playlisteintrag hat:

| Feld | Bedeutung |
|---|---|
| `id` | Innerhalb des Manifests eindeutige Folien-ID |
| `path` | HTML-Pfad, der exakt in `files` vorkommt |
| `duration_seconds` | Integer 5 bis 300; vom Benutzer bestätigter Standard 20 |
| `valid_from` | RFC-3339-Zeitstempel einschließlich Offset, oder `null` |
| `valid_until` | Exklusive Obergrenze als RFC-3339-Zeitstempel, oder `null` |

Die Liste wird in ihrer Reihenfolge zyklisch abgespielt. Eine Folie ist nur im
Intervall `[valid_from, valid_until)` zulässig. Ein erreichtes Ablaufdatum beendet
auch eine gerade laufende Folie. Leere oder vollständig abgelaufene Listen führen
zur integrierten neutralen Auszeit-Seite, nicht zu einem schwarzen Bildschirm.
Wiederholungen können durch getrennte Einträge mit unterschiedlichen IDs erfolgen.

Version 1 verwendet explizite Zeitintervalle statt frei formulierter Kalenderregeln.
Der Paketproduzent muss die Intervalle aus fachlichen Regeln ableiten; generierte
Menüdateien dürfen nach Mitternacht nicht allein aufgrund ihres Namens als aktuell
gelten. Tagesfolien, Wetter und News brauchen ebenfalls eine definierte Gültigkeit.
Die fachlichen Gültigkeitsintervalle sind noch abzustimmen. Bestätigt sind
20 Sekunden Standarddauer und das Ausblenden abgelaufener Folien.

## Aktualisierung und Offlinebetrieb

Vorgeschlagener Ablauf, unabhängig von der Wiedergabe:

1. Alle fünf Minuten mit kleinem Zufallsversatz `latest.json` über HTTPS abrufen.
   Zeitlimits, begrenzte Wiederholungen und nur ein gleichzeitiger Downloadlauf.
2. Zeiger und Manifest strikt prüfen; Manifesthash vor Verwendung vergleichen.
3. Nur Dateien aus der zugelassenen Feed-Basis laden, Redirects außerhalb dieser
   Basis zurückweisen. Keine beliebigen vom Manifest benannten Netzwerkziele.
4. In einen neuen Stagingbereich auf demselben Dateisystem streamen; niemals
   direkt in den aktiven Stand schreiben. Downloadlängen, Dateianzahl, Manifestgröße
   und Gesamtgröße begrenzen. Vorläufig: 1 MiB Manifest, 2.000 Dateien,
   50 MiB je Datei, 512 MiB je Release; mindestens 1 GiB Reserve behalten.
5. Für jede Datei Größe und SHA-256 prüfen. Fehlende Dateien, HTML-Fehlerseiten
   anstelle von Bildern, ungültige Playlist oder fehlende Ressourcen verwerfen.
   Abhängigkeiten einschließlich CSS-URLs prüfen; ein Renderer-Test ohne Internet
   muss zusätzlich die tatsächliche Darstellung bestätigen. Kein bloßer HTTP-200-Test.
6. Geprüften Stand unveränderlich ablegen. Daten und Metadaten vor dem atomaren
   Aktivierungszeiger dauerhaft schreiben (`fsync` einschließlich Verzeichnissen).
   Bei Stromausfall bleibt der alte Zeiger oder der vollständig neue gültig.
7. An einer Foliengrenze umschalten und zunächst als Probestand behandeln.
   Nach erfolgreicher Wiedergabe bestätigen; bei ausbleibender Wiedergabe zum
   vorherigen bestätigten Release zurückkehren. Fehlgeschlagenes Release sperren,
   bis ein anderes Release oder ein ausdrücklich angeforderter Versuch folgt.
8. Aktiven und vorherigen bestätigten Stand behalten. Nur unreferenzierte
   Stagingreste und ältere Player-Releases aufräumen, niemals Server-/Webinterfacedaten.

Wenn ein neuer Zeiger während des Downloads erscheint, darf ein bereits vollständig
geprüftes unveränderliches Release fertiggestellt werden. Der nächste Lauf holt das
neuere. Ein erneuter GET des Zeigers ersetzt keine serverseitige Snapshot-Garantie.

Browsercache ist nicht der Offlinebestand. Ein Kaltstart ohne Internet muss den
letzten bestätigten Bestand laden können. Ohne vorherigen Bestand erscheint die
eingebaute neutrale Seite. Vom Benutzer bestätigt: abgelaufene datumsabhängige Folien
überspringen und verbleibende gültige Folien weiterspielen.
Bei Kaltstart ohne verlässliche Uhrzeit keine zeitkritischen Folien anzeigen;
Pi 4 besitzt hier keine eingerichtete batteriegepufferte RTC.

## Lokale Darstellung ohne vermischte Ressourcen

Die bestehenden HTML-/CSS-Pfade bleiben unverändert. Ein bloßes Umschalten eines
gemeinsamen Ressourcenverzeichnisses bei laufender Folie wäre nicht ausreichend.
Jede geladene Folie muss einschließlich aller Assets an ihr Release gebunden sein.

Vorgeschlagene Umsetzung: eine lokale Playeroberfläche und je aktivem bzw.
vorbereitetem Release ein eigener Loopback-Port als Inhalts-Origin. Jeder
Inhalts-Origin bedient `/auszeit-display/...` ausschließlich aus einem festen Release.
Beim Wechsel lädt ein einzelner iframe den neuen Origin; der vorherige Origin bleibt
bis zum Ende der alten Anzeige erhalten. Alte Origins dürfen nicht unter laufenden
Seiten auf ein anderes Release umgestellt werden. Höchstens zwei Inhalts-Origins
gleichzeitig, kein Browserfenster oder Tab je Folie.

Folien dürfen keine externen Laufzeitressourcen benötigen. Inhalts-Origin mit
restriktiver CSP und iframe-Sandbox; vorhandene Inline-Skripte für Textanpassung
müssen funktionieren. Folien erhalten keine Wartungs-/Statuszugangsdaten und keinen
Zugriff auf lokale Steuerendpunkte. Lokale HTTP-Dienste nicht ans Gast-WLAN binden.

## Wiedergabeüberwachung und Status

Der bereits eingerichtete systemd-Dienst startet einen beendeten Chromium-Prozess
neu. Ein laufender Prozess beweist keine funktionierende Folie. Ergänzend braucht
der Player ein regelmäßiges Lebenszeichen der Wiedergabe mit Folien-ID und
Fortschritt; festhängende Renderer, leere Frames und Ladefehler getrennt behandeln.
Neustarts begrenzen bzw. verzögern und wiederholte Fehler sichtbar melden.

Vorgeschlagene Meldung alle fünf Minuten an einen noch festzulegenden HTTPS-Empfänger:

- Schema- und Player-Version, gerätespezifische `device_id`, Boot-ID.
- Aktives und vorheriges Release, letzte erfolgreiche Inhaltsprüfung und Aktivierung.
- Wiedergabezustand, aktuelle Folie, Zeitpunkt des letzten Browser-Lebenszeichens.
- Freier Speicher in Bytes, Temperatur in Grad Celsius, `get_throttled`-Flags.
- Uhrsynchronisation, Laufzeit, letzter Downloadfehler und Neustartzähler.

Der Empfänger ergänzt seine eigene Empfangszeit als verbindlichen letzten Kontakt.
Kein öffentlicher Schreibzugriff: separates widerrufbares Gerätetoken, TLS-Prüfung,
keine Tokens in URLs oder Logs. Meldeausfälle dürfen die Wiedergabe nicht blockieren;
lokale Statusdatei atomar und mit begrenzten Logs führen. Keine unbegrenzte Warteschlange.
Ein Fernwartungsdienst ersetzt weder diesen Empfänger noch fachliche Statusmeldungen.

## Nächster Entwicklungsschritt und Abnahme

Eigenständiges Player-Verzeichnis mit zwei synthetischen Releases und lokalem
Test-Feed; keine produktiven Exportänderungen. Zuerst Rotation und Gültigkeit,
danach geprüfter Download und Aktivierung, danach Telemetrieempfänger anbinden.

Erforderliche Tests: beschädigter/abgebrochener Download, fehlendes Asset,
Pfadtraversal/Redirect, Platzmangel, gleichzeitige Updates, Releasewechsel während
einer Folie, Tages-/Sommerzeitgrenzen, fehlende Uhrsynchronisation, leerer Plan,
Offline-Kaltstart, Stromunterbrechung bei Aktivierung, Browser- und Rendererfehler.
Hardwaretests für 1920×1080, Speicherverbrauch und Temperatur bleiben zusätzlich nötig.
