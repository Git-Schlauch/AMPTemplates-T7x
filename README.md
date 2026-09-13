# AMPTemplates-T7x

Eigenes AMP Generic-Template für einen Black Ops III / T7x Dedicated Server auf Ubuntu x86_64 mit Wine im AMP-Container.

**Status: vorbereitete Erstversion, noch nicht auf einer echten AMP-Instanz getestet.** Die lokalen Prüfungen kontrollieren Dateiformate und interne Verweise, keine AMP-Kompatibilität oder Erreichbarkeit des Servers.

## Für GitHub vorbereiten

Im Projektordner PowerShell öffnen und deinen tatsächlichen GitHub-Namen einsetzen:

```powershell
./scripts/Prepare-Repository.ps1 -GitHubUser "DEIN_GITHUB_NAME"
```

Für einen anderen Repository-Namen zusätzlich `-Repository "MeinRepo"` angeben. Das Skript setzt Autor, URLs und einen persönlichen AMP-Prefix. Die eindeutigen IDs bleiben bei erneutem Ausführen erhalten. Es veröffentlicht nichts.

Auf GitHub ein leeres Repository namens `AMPTemplates-T7x` erstellen, ohne automatisch erzeugte README oder Lizenz. Anschließend:

```powershell
git add .
git commit -m "Add initial AMP T7x template"
git branch -M main
git remote add origin https://github.com/DEIN_GITHUB_NAME/AMPTemplates-T7x.git
git push -u origin main
```

Alternativ den bestehenden Projektordner in GitHub Desktop hinzufügen und veröffentlichen. Es sind keine Spieldateien, Zugangsdaten oder vorgefertigten Passwörter enthalten. Eine Lizenz für die Veröffentlichung wurde noch nicht festgelegt; fremde Software und Konfigurationen behalten ihre jeweiligen Bedingungen.

## Enthaltene Dateien

| Datei | Zweck |
| --- | --- |
| `manifest.json` | Identität des AMP-Repositorys |
| `bo3-t7x.kvp` | Prozess, Container, Pfade und Startparameter |
| `bo3-t7xconfig.json` | Auswahl Multiplayer/Zombies/Campaign und Mod-Ordner |
| `bo3-t7xports.json` | Port 27017, TCP und UDP reserviert |
| `bo3-t7xupdates.json` | SteamCMD, Konfigurationen, T7x und Wine-Initialisierung |
| `scripts/` | Personalisierung und statische Prüfung |

## In AMP einrichten

1. Ubuntu amd64/x86_64, AMP ab 2.6 und funktionsfähige Container-Bereitstellung voraussetzen. Das Template verlangt `cubecoders/ampbase:wine-stable`.
2. Im AMP-Hauptpanel unter **Configuration → Instance Deployment → Configuration Repositories** `DEIN_GITHUB_NAME/AMPTemplates-T7x:main` hinzufügen, **Fetch** ausführen und den Browser aktualisieren.
3. Eine Instanz mit **Call of Duty: Black Ops III - T7x** erstellen. Als Ausgangspunkt etwa 4 CPU-Threads und 4–8 GB RAM vorsehen; ausreichend freien Speicher für Server und zusätzliche Karten bereitstellen.
4. In der Instanz **Update** ausführen. SteamCMD lädt App `545990` für Windows anonym. Danach werden Dss0-Konfigurationen, T7x und der Wine-Prefix eingerichtet.
5. Im File Manager `server/UnrankedServer/zone/server.cfg` bearbeiten: Servername, Beschreibung, Spielerzahl und bei Bedarf Join-/RCON-Passwort setzen. Passwörter ausschließlich in der Instanz speichern.
6. **Configuration → T7x Server**: Multiplayer wählen, Mod-Feld zunächst leer lassen.
7. Den in AMP angezeigten Game-Port in Host-/Provider-Firewall und gegebenenfalls Router freigeben. Für das Spiel ist UDP relevant; dieses Template reserviert zusätzlich TCP. Bei weiteren Instanzen jeweils eigene Ports verwenden.
8. **Start** ausführen und mit dem T7x-Client über `/connect SERVER-IP:PORT` testen.

Bei aktivem UFW und Standardport:

```bash
sudo ufw allow 27017/udp
sudo ufw allow 27017/tcp
```

## Updates und Grenzen

Vor Updates die Instanz stoppen und eigene Konfigurationen sichern. Vorhandene Dateien unter `t7x/` und `zone/` werden durch den Kopierschritt nicht überschrieben. Neue Upstream-Änderungen an bestehenden Konfigurationen müssen bewusst übernommen werden. Das extrahierte Download-Verzeichnis `t7x-config/` bleibt zur Fehleranalyse erhalten.

Die Downloads folgen Dss0 `main` und dem aktuellen AlterWare-T7x-Binary. Diese Version ist daher nicht reproduzierbar auf feste Upstream-Versionen eingefroren. Der T7x-Download wird bei Updates ersetzt.

AMP meldet den Prozess mit `ApplicationReadyMode=Immediate` als gestartet; dies beweist noch keine spielbereite Map. Spielerzahlen und Beitrittsmeldungen werden noch nicht automatisch aus Logs erkannt. Ein kompletter Editor für `server.cfg`, Workshop-Downloads und automatische VC++-Runtime-Installation sind nicht enthalten.

Zombies und Campaign sind als Konfigurationsauswahl vorhanden, benötigen aber zusätzliche passende Dateien aus deiner eigenen BO3-Installation. Zuerst Multiplayer ohne Mods testen. Details zu zusätzlichen Zombie-Dateien stehen in der unten verlinkten Dss0-Anleitung.

## Fehler eingrenzen

- **Update fehlgeschlagen:** die erste fehlgeschlagene Stufe und deren vollständige Ausgabe prüfen. Installations- und Wine-Fehler werden nicht übersprungen.
- **Datei nicht gefunden:** tatsächliche SteamCMD-Verzeichnisstruktur mit `server/UnrankedServer/` vergleichen. Dieser Pfad muss auf der Zielinstanz verifiziert werden.
- **Fehlende Zone:** Konsolenausgabe und gegebenenfalls `server/UnrankedServer/identities/dedicatedpc/console_mp.log` prüfen; benötigte Kartendateien ergänzen.
- **DLL-/Wine-Fehler:** genaue fehlende Runtime anhand der Fehlermeldung im Container installieren. Das Template installiert VC++-Pakete nicht automatisch.
- **Keine Verbindung:** ausgewählten Port, Container-Portzuordnung, Firewalls und Client-Version prüfen.

Statische Prüfung erneut ausführen:

```powershell
./scripts/Validate-Template.ps1 -RequirePersonalized
```

GitHub Actions führt dieselbe Prüfung bei Push und Pull Request aus. Für die erste Betriebsprüfung müssen Update, Start, Client-Verbindung, Stop und ein erneutes Update mit erhaltener eigener Konfiguration auf Ubuntu erfolgreich sein.

## Quellen

- [CubeCoders: Generic-Modul und eigene Repositories](https://github.com/CubeCoders/AMP/wiki/Configuring-the-'Generic'-AMP-module)
- [CubeCoders: Wine-Template-Beispiel](https://github.com/CubeCoders/AMPTemplates/blob/main/carrier-command2.kvp)
- [CubeCoders: Update-Stufen-Beispiel](https://github.com/CubeCoders/AMPTemplates/blob/main/carrier-command2updates.json)
- [Dss0: T7-Serverkonfiguration und zusätzliche Spieldateien](https://github.com/Dss0/t7-server-config)
- [AlterWare: T7x-Download](https://alterware.dev/docs)

Ausgangspunkt ist die vom Nutzer bereitgestellte Anleitung. Die Download-Dateinamen wurden ausdrücklich gesetzt, Standardwerte ergänzt und Installationsfehler werden früher gemeldet. Es wird kein rekursiver Bereinigungsbefehl ausgeführt.
