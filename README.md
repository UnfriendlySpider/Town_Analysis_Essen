# Essen-Daten

Private Analyse der öffentlichen Geo-, Umwelt- und Stadtdaten für Essen. Das Projekt bringt einen
Katalog von 39 Quellen und 49 Datensätzen mit, lädt Daten auf Knopfdruck direkt bei den Anbietern,
untersucht sie und rechnet Kennzahlen je Stadtteil. Alles läuft auf dem eigenen Rechner; im Projekt liegen
keine Daten.

Bisher eingebaut:
- **Nächtliche Überwärmung je Stadtteil** aus der Klimaanalyse NRW 2026
- **Hitzetage und Tropennächte** an der DWD-Station Essen-Bredeney
- **Schnellanalyse**: jeden Vektordatensatz auf die Stadtteile verteilen

## Einrichten

Du brauchst [uv](https://docs.astral.sh/uv/). Python holt uv selbst.

```bash
# macOS und Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Dann im Projektordner:

```bash
uv sync
```

## Starten

```bash
uv run essen app
```

Der Browser öffnet `http://localhost:8501`. Die App ist nur auf diesem Rechner erreichbar und sendet keine
Nutzungsstatistik. Beenden mit Strg+C im Terminal.

Zum Ausprobieren ohne Downloads gibt es erfundene Testdaten (in einem eigenen Ordner `data_test/`):

```bash
uv run essen testdaten
uv run essen app --testdaten
```

## Erste Schritte mit echten Daten

In der App unter **Datenkatalog** auf *Herunterladen* klicken, oder im Terminal:

```bash
uv run essen laden stadtteile klimaanalyse-nacht-raster klimaanalyse-beschreibung   # rund 380 MB
uv run essen inspizieren klimaanalyse-nacht-raster     # wie sind die Klassen im Raster kodiert?
uv run essen analyse hitze-nacht --export              # rechnen, Seite nach data/export/
uv run essen laden dwd-klima-essen-aktuell dwd-klima-essen-historisch
uv run essen analyse hitzetage-station
```

Erkennt die Analyse die Kodierung des Rasters nicht sicher, bricht sie ab und legt eine Vorlage nach
`data/zuordnungen/`. Den Inspektionsbericht aus `data/inspektion/` kannst du weitergeben; er enthält keine
persönlichen Daten.

### Dateien aus dem ersten Durchstich übernehmen

Wer die Dateien aus `umwelt-essen/data/raw/` schon hat, muss sie nicht neu laden:

```bash
uv run essen einlesen stadtteile ../umwelt-essen/data/raw/Stadtteile_WGS84.geojson
uv run essen einlesen klimaanalyse-nacht-vektor ../umwelt-essen/data/raw/Klimaanalyse-Nacht_2026_EPSG25832_GeoPackage.zip
```

Für die Hitzeanalyse fehlt dann noch das Raster (`uv run essen laden klimaanalyse-nacht-raster`), denn das
GeoPackage enthält keine Temperaturklassen.

## Kommandozeile

| Befehl | Wofür |
| --- | --- |
| `uv run essen katalog [--thema klima] [suchwort]` | Datensätze auflisten |
| `uv run essen info ID` | alles zu einem Datensatz, mit Quellenangabe |
| `uv run essen laden ID …` | aus der Originalquelle laden (`--neu`, `--datei NAME`, `--ja` ohne Nachfrage bei großen Dateien) |
| `uv run essen einlesen ID DATEI` | von Hand geladene Datei übernehmen |
| `uv run essen status [--aufraeumen]` | was geladen ist; entpackte Ordner nach Rückfrage löschen |
| `uv run essen aktualisieren [ID …]` | bei den Quellen nachsehen, ob es neuere Stände gibt (lädt nichts) |
| `uv run essen inspizieren ID` | Bericht über Inhalt und Aufbau |
| `uv run essen dienst ID` | Ebenen eines Kartendienstes |
| `uv run essen analyse [ID] [-p name=wert] [--export]` | Analysen auflisten oder rechnen |
| `uv run essen vorbereiten` | alle Daten laden, die die Themen brauchen, und alle Themen berechnen |
| `uv run essen pruefen-ergebnisse [--festschreiben]` | alle Analysen neu rechnen und mit den Referenzwerten in `docs/referenzwerte.yaml` vergleichen |
| `uv run essen schnell ID` | Vektordaten je Stadtteil zählen |
| `uv run essen --testdaten …` | jeden Befehl mit den Testdaten |

## Aufbau

```
katalog/      Quellen, Datensätze, Lizenzen (YAML) – die einzige Stelle für Adressen und Lizenzen
src/essen/    Paket: laden, geo, inspizieren, kennzahlen, analysen/, karte, bericht, app/, cli
docs/         Architektur, Entscheidungen, Methodik, Fahrplan, Datenquellen
tests/        pytest mit erfundenen Testdaten, ohne Internet
data/         geladene Daten und Ergebnisse (nicht im Repository)
```

Mehr: [docs/architektur.md](docs/architektur.md), [docs/datenquellen.md](docs/datenquellen.md),
[docs/fahrplan.md](docs/fahrplan.md), [docs/entscheidungen.md](docs/entscheidungen.md).

## Weiterentwickeln

```bash
scripts/pruefen.sh            # vor dem Einchecken: Stil (ruff), Katalog, Tests
uv run pytest                 # alle Tests
uv run ruff check src tests   # Stil und typische Fehler
uv run essen katalog --pruefen
uv add PAKET                  # Paket hinzufügen (pyproject.toml und uv.lock)
```

Für Coding-Agenten (Claude Code, Codex und andere) steht die Arbeitsanleitung in [AGENTS.md](AGENTS.md),
Anleitungen für wiederkehrende Aufgaben in `.claude/skills/`. Hinweise für Cloud-Sitzungen:
[docs/cloud.md](docs/cloud.md).

## Lizenzen und Weitergabe

Für das private Arbeiten gelten keine Lizenzpflichten. Vor jeder Weitergabe von Ergebnissen die Lizenzen
prüfen (Skill `lizenz-pruefen`, App-Seite **Methodik und Lizenzen**). Die Daten gehören den jeweiligen
Anbietern; die Lizenz steht bei jedem Datensatz im Katalog.
