# Version 5: Ezz-Masterserver, Live-Konsole und Spieler

## Was sich aendert

- **Server und Masterserver → Server-Software:** T7x oder EZZ BOIII. T7x bleibt Standard, damit eine bestehende Installation nicht ungefragt den Client wechselt. Nach einem Wechsel zuerst **Update**, dann starten.
- **Masterserver (nur EZZ):** Ezz, AlterWare oder beide. Die beiden letzten Optionen sind experimentell: eine Anmeldung garantiert weder die Annahme durch den Master noch Client-Kompatibilitaet. T7x behaelt seinen eingebauten Master. Keine DNS-/hosts-Manipulation.
- Ezz liest `boiii_players/user/master_servers.txt` einmal beim Prozessstart. Der Adapter schreibt diese Datei vor jedem Start aus der Auswahl und sichert eine vorherige Liste einmal als `.txt.before-amp`. Fuer oeffentliche Sichtbarkeit `Nur LAN` ausschalten; der Game-Port muss weiterhin erreichbar sein.
- Der Update-Schritt installiert Ezzs `boiii.exe` und kopiert die bereits vorhandenen `t7x`-Supportdateien nach `boiii`, ohne bestehende Dateien zu ersetzen. `-noupdate` verhindert Selbstupdates; Aktualisierungen erfolgen durch AMP. Die englischen Zombies-Dateien, die beim Nutzer funktionieren, beibehalten.

## Konsole und Spieleranzeige

AMP startet nun einen Python-Adapter, der Wine als Kindprozess betreut. Er liest neue Zeilen aus `identities/dedicatedpc/console_mp.log`; diese erscheinen mit `[GAME]`. Vorhandene alte Logs werden nicht erneut abgespielt. Wine-Ausgaben erscheinen mit `[WINE]`. Direkte Ausgabe und Dateilog koennen dieselbe Meldung enthalten.

Eingaben werden mit Quake-artigem UDP-RCON an **127.0.0.1 und den Game-Port** geschickt. Ein separates zufaelliges Kennwort wird pro Instanz in `.amp-rcon-secret` erzeugt. `zone/amp_control.cfg` setzt es nach der ausgewaehlten Spielkonfiguration. Das bisherige Feld `RCON-Passwort` ist damit nicht mehr massgeblich. Join-Passwoerter bleiben unveraendert. Kennwortdateien werden mit Modus 0600 angelegt und das Kennwort nicht als Prozessargument uebergeben. RCON ist damit am Spielserver aktiviert; die Anbindung sendet Befehle nur lokal. Wer zusaetzliche RCON-Werkzeuge nutzt, muss das neue lokale Kennwort verwenden.

Alle zehn Sekunden wird `status` abgefragt. Erkannte menschliche Spieler erzeugen AMP-Beitritts-/Austrittsereignisse; Bots werden ausgefiltert. Namen mit Leerzeichen und Farbcodes sind beruecksichtigt. Bei fehlender Antwort oder unbekanntem Ausgabeformat bleibt die letzte Liste stehen, statt faelschlich alle Spieler abzumelden. Eine Warnung erscheint hoechstens einmal pro Minute. Kurze Verbindungen zwischen zwei Abfragen koennen unbemerkt bleiben. Spieler-Chat wird noch nicht separat als AMP-Chatereignis erkannt.

`quit` im Panel beendet den Spielserver mit RCON. Falls er nicht reagiert, beendet der Adapter nach einer Wartezeit ausschliesslich seine Wine-Prozessgruppe. Er verwendet kein globales `wineserver -k` und beendet keine anderen Instanzen.

## Bestehende Instanz aktualisieren

Zuerst alle Repository-Aenderungen committen und nach GitHub pushen. **Die alte Anleitung fuer den alleinigen Austausch von metaconfig.json reicht fuer Version 5 nicht aus.**

Der Container braucht Python 3. Bei neuen Instanzen ist es als AMP-Containerpaket eingetragen. Bei bestehenden Instanzen muss es bereits vorhanden sein oder ueber die Containerpakete installiert werden. Mit `sudo docker ps --format 'table {{.ID}}\t{{.Names}}'` den aktuellen T7x01-Container identifizieren und darin `python3 --version` pruefen (`sudo docker exec CONTAINER-ID python3 --version`). Nicht die inzwischen geloeschte T7x03-ID verwenden.

Spielserver im Panel stoppen, dann auf Ubuntu:

```bash
sudo -iu amp ampinstmgr StopInstance CallofDutyBlackOpsIII-T7x01
sudo -iu amp
```

Erst bei bestaetigtem Stillstand weitermachen. Als Benutzer `amp` die aktuelle Repository-Version in einen neuen temporaeren Ordner holen:

```bash
work=$(mktemp -d)
git clone --depth 1 https://github.com/Git-Schlauch/AMPTemplates-T7x.git "$work/template"
python3 "$work/template/scripts/Upgrade-Instance.py" --instance-dir /home/amp/.ampdata/instances/CallofDutyBlackOpsIII-T7x01
```

Der letzte Befehl ist eine Vorschau. Wenn die vier erwarteten Dateien genannt werden:

```bash
python3 "$work/template/scripts/Upgrade-Instance.py" --instance-dir /home/amp/.ampdata/instances/CallofDutyBlackOpsIII-T7x01 --apply
ampinstmgr StartInstance CallofDutyBlackOpsIII-T7x01
exit
```

Das Skript sichert Dateien unter `amp-bo3-backup-DATUM`, behaelt eigene AppSettings und Ports und tauscht nur die benoetigten Runtime-Felder, Update-Stufen und Manifeste aus. Die Spieldateien werden nicht ersetzt. Dann Browser aktualisieren, **EZZ BOIII** und **Ezz** auswaehlen, **Update** ausfuehren und den Spielserver starten.

Rollback: AMP-Instanz stoppen, die gleichnamigen gesicherten Dateien aus dem ausgegebenen Backupordner zurueckkopieren, Instanz wieder starten. Der alte Startbefehl startet wieder direkt Wine. Keine Instanz loeschen.

## Abnahme auf dem echten Server

1. Nach Start muessen `[AMPBO3] Starting ezz` und neue `[GAME]`-Zeilen erscheinen.
2. In der Konsole `status` senden: Antwort mit Spielern oder leerer Tabelle erwarten. Bei keiner Antwort das neue Log pruefen; Befehle werden wegen unbekanntem Ausfuehrungszustand nicht automatisch wiederholt.
3. Mit Ezz verbinden; nach etwa zehn Sekunden den Spieler im AMP-Panel erwarten. Nach Verlassen soll er wieder verschwinden.
4. Im Ezz-Browser den Server suchen. Bei `both` beide Browser getrennt testen; Master-Annahme und Client-Kompatibilitaet sind nicht lokal testbar.
5. Stop/Start testen und danach kontrollieren, dass keine zweite Spielserver-Kopie auf demselben Port laeuft.

Lokal getestet sind Parser, Masterdateien, RCON-Paketformat mit simuliertem Socket, Log-Trunkierung, Exitcode und Migration. Ein echter Wine-/AMP-/Ezz-Integrationstest steht noch aus. Der Statusparser richtet sich nach Ezzs Quellcode und muss bei abweichender T7x-Statusausgabe angepasst werden. Keine Namen/Spielerzahlen werden ohne erkannte Antwort erfunden.

## Primaerquellen

- https://github.com/Ezz-lol/boiii-free/blob/main/src/client/component/server_list.cpp
- https://github.com/Ezz-lol/boiii-free/blob/main/src/client/component/dedicated/command.cpp
- https://github.com/Ezz-lol/boiii-free/blob/main/src/client/component/console.cpp
- https://github.com/Ezz-lol/boiii-free/blob/main/src/client/component/rcon.cpp
- https://github.com/Ezz-lol/boiii-free/blob/main/src/client/component/status.cpp

Downloads folgen weiterhin dem jeweils aktuellen Release; Aenderungen am Upstream koennen erneute Pruefungen erfordern.
