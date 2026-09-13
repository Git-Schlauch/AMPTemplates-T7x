# Zombies-Einstellungen in einer bestehenden Instanz

Version 3 stellt alle 19 `set`-Werte und die drei Regeldatei-Pfade aus Dss0s `server_zm.cfg` bereit. Kartenwahl: 14 Einzelkarten oder alle Karten als Rotation. Beliebige eigene Rotationen bleiben im bisherigen manuellen Zombies-Modus moeglich. Neue Maps werden nicht heruntergeladen. Der Game-Port wird weiterhin ueber AMP verwaltet.

## Installation

Zuerst die lokalen Aenderungen nach GitHub pushen. Danach in AMP **Fetch** und die Konfiguration der bestehenden Instanz aktualisieren. Nicht die Instanz loeschen.

Falls die Template-Aktualisierung in der Oberflaeche nicht erreichbar ist, lassen sich die zwei Manifeste direkt austauschen. Diese Alternative setzt den bereits bekannten Instanznamen voraus. Sie aktualisiert nur die Einstellungsoberflaeche und den Konfigurationsgenerator, nicht das gesamte Template. Zuerst den Spielserver in AMP stoppen, dann auf Ubuntu:

```bash
sudo -iu amp ampinstmgr StopInstance CallofDutyBlackOpsIII-T7x01
sudo -iu amp
```

Erst weiter, wenn die Instanz gestoppt ist. Folgenden Block als Benutzer `amp` ausfuehren:

```bash
(
set -eu
cd /home/amp/.ampdata/instances/CallofDutyBlackOpsIII-T7x01
test -f GenericModule.kvp
backup="zombies-ui-backup-$(date +%Y%m%d-%H%M%S)"
mkdir "$backup"
cp configmanifest.json "$backup/"
if [ -f metaconfig.json ]; then cp metaconfig.json "$backup/"; fi
curl --fail --location --output "$backup/new-config.json" https://raw.githubusercontent.com/Git-Schlauch/AMPTemplates-T7x/main/bo3-t7xconfig.json
curl --fail --location --output "$backup/new-meta.json" https://raw.githubusercontent.com/Git-Schlauch/AMPTemplates-T7x/main/bo3-t7xmetaconfig.json
python3 -m json.tool "$backup/new-config.json" >/dev/null
python3 -m json.tool "$backup/new-meta.json" >/dev/null
cp "$backup/new-config.json" configmanifest.json
cp "$backup/new-meta.json" metaconfig.json
echo "Backup: $PWD/$backup"
)
```

Nur bei erfolgreicher Ausfuehrung neu starten (weiterhin als `amp`):

```bash
ampinstmgr StartInstance CallofDutyBlackOpsIII-T7x01
exit
```

Wenn der Block scheitert, Fehlermeldung pruefen; keine weiteren Dateien ersetzen. Die Sicherung enthaelt die alten Manifeste. Zum Rueckgaengigmachen die Instanz stoppen und diese zurueckkopieren; gab es vorher keine `metaconfig.json`, die neu angelegte Datei zur Sicherung verschieben. Spieldateien bleiben erhalten.

## Verwendung und erster Test

1. Browser neu laden, bei erneutem Anzeigeproblem die bereits bekannte Browser-/Cookie-Ursache pruefen.
2. **T7x Server → Server Mode → Zombies - AMP-Einstellungen** auswaehlen.
3. Unter **Zombies - Allgemein / Karten / Netzwerk / Spielregeln / Experten** die Werte setzen. Bestehende Namen, Passwoerter und LAN-Einstellungen werden NICHT aus `server_zm.cfg` importiert. Vorher ins Interface uebertragen. Fuer LAN `Nur LAN` aktivieren.
4. Namen und Passwoerter ohne doppelte Anfuehrungszeichen und Zeilenumbrueche verwenden. Passwoerter werden im Panel maskiert, stehen aber in der Server-CFG im Klartext.
5. Spielserver starten. Im File Manager `UnrankedServer/zone/amp_zombies.cfg` pruefen: drei `exec`-Zeilen, 19 `set`-Zeilen, gewaehlter Name und Kartenrotation. Die Datei wird von AMP verwaltet; manuelle Aenderungen dort koennen ueberschrieben werden.
6. Name/Karte im Interface aendern, Spielserver neu starten und die erzeugte Datei sowie die tatsaechlich geladene Map kontrollieren. Aenderungen sind nicht live.

Die GUI-Erweiterung ist lokal statisch geprueft; die Integration und das Schreiben der Datei durch AMP muessen auf der Zielinstanz bestaetigt werden. Bei Problemen auf den bisherigen Modus **Zombies** mit `server_zm.cfg` zurueckschalten. Die Originaldatei wird nicht ueberschrieben.
