# Reproduzierbare Einrichtung des Referenzplayers

Der laufende Player ist eingerichtet. `install_base.sh` ist ausschließlich für
ein frisches System gedacht und verweigert den Start bei vorhandenem Benutzer
`player` oder bestehenden Installationsverzeichnissen. Kein Flashen und kein
Bereinigen des laufenden Geräts. Hardwareabnahme des Gesamtinstallers steht aus.

## Basis

Raspberry Pi 4, Raspberry Pi OS Lite 64-bit Trixie, microSD mindestens 16 GB.
OS-Image-Dateiname und SHA-256 vor dem Schreiben dokumentieren; Kartenziel und
Löschfreigabe vor jedem Flashvorgang separat prüfen. Der bisher benutzte genaue
Image-Download ist noch nicht erfasst. Gleiche Einrichtung bedeutet hier gleiche
Konfiguration, nicht bitidentische Paketversionen aus veränderlichen APT-Quellen.

Imager pro Gerät konfigurieren: Wartungsbenutzer `auszeit`, eigener SSH-Zugang,
WLAN, Europe/Vienna. Der aktuelle Referenzinstaller und die bestehenden Installer
sind auf `auszeit-player-01` beschränkt. Ein Ersatzgerät mit gleichem Hostnamen darf
nicht gleichzeitig mit dem Original im gleichen Netzwerk betrieben werden.
Mehrgeräte-Provisionierung mit anderen Hostnamen ist noch nicht implementiert.

Auf dem frischen Gerät Systemupdates installieren, neu starten und den geprüften
Git-Stand beziehen. Danach aus dem Repository `bash player/install_base.sh` als
Wartungsbenutzer ausführen. Der Installer installiert Grafik/Browser/Connect,
Benutzer und Startkonfiguration, lokalen HTTP-Player sowie Abruf-/Status-Timer.
Die bestätigte Kioskkonfiguration wird übernommen, direkt mit Port 8081 statt
früherer Uhr-/Port-8080-Testkonfiguration. Kein `--no-sandbox`.

Ohne Inhalte erscheint ausschließlich das lokale Notfallbild. Ein vorhandener
Bestand wird von den Updateinstallern erhalten. Auf einem frischen System werden
keine synthetischen A/B/C-Folien angelegt. Neustart nach Installation erforderlich,
unter anderem für die NetworkManager-Vorgabe `wifi.powersave=2`.

## Gerätebezogene Einrichtung

- Connect als `auszeit`: `rpi-connect on`, danach `rpi-connect signin` und die
  interaktive Kontoverknüpfung. Kein Connect-Anmeldestatus aus einem anderen Gerät.
- `/etc/auszeit-player/config.json` enthält eine neu erzeugte Geräte-ID. Feed-URL:
  `https://populorum.eu/auszeit-player-feed/`. Status-URL:
  `https://populorum.eu/auszeit-conf-status/status.php`.
- Zufälligen Statusschlüssel separat pro Gerät erzeugen, als root:player 0640
  unter `/etc/auszeit-player/status.token` speichern. Nur Geräte-ID und SHA-256-
  Prüfwert in die private Hostingkonfiguration aufnehmen. Siehe `operations/README.md`.
- Heim-/Café-WLAN und Administrationszugang separat provisionieren. Das temporäre
  sudo-Timeout des Aufbaugeräts gehört nicht zur Basisinstallation.

## Abnahme

Nach Neustart: Vollbild, 1920×1080, automatische Folien, aktiver Abruf-Timer,
`update_state: ok`, Statusübertragung, WLAN-Energiesparen aus. Danach Wiederanlauf
nach Browserabsturz sowie Wiedergabe mit getrenntem Netzwerk prüfen. Gerätetoken
und Connect-Zuordnung müssen eindeutig sein. Paket- und Bereinigungstests sind
vorhanden; frische OS-Installation ist durch Windows-Tests nicht nachgewiesen.

## Image-Vorlage – noch nicht freigegeben

Ein Abbild des laufenden Geräts enthält WLAN-Zugang, SSH-Hostschlüssel, machine-id,
Connect-Anmeldung, Browserprofil und Statusschlüssel. Es ist keine weitergebbare
Vorlage. Vor einer Image-Erstellung sind eine separate Karte, Offline-Bereinigung
und getestete Erststart-Provisionierung erforderlich. Dieser Installer entfernt
keine Identitäten und meldet kein bestehendes Gerät aus Connect ab.

Offen: Image-Build/Erststart, Begrenzung der Browser-/Grafiklogs, Verhalten bei
Grafiksitzungs-Hängern und zuverlässige Zeit nach Offline-Kaltstart. Zurückgestellt:
kurze schwarze Übergänge bestimmter Folien und Tagesmotive in der Wettervorschau.
