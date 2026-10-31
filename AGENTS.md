# AGENTS.md – Arbeitsanleitung für Coding-Agenten

Diese Datei richtet sich an Coding-Agenten (Claude Code, Codex und andere) und an Menschen, die am Projekt
arbeiten. Sie gilt für das ganze Repository.

## Worum es geht

Eine private, lokale Analyse der öffentlichen Daten der Stadt Essen. Begonnen mit Geo- und Umweltdaten
(Hitze, Grün, Lärm, Wasser, Luft), erweiterbar auf alle offenen Daten zu Essen. Es gibt drei Teile:

1. **Datenkatalog** (`katalog/*.yaml`): 39 Quellen und 53 Datensätze mit Lizenz und Download-Angaben.
2. **Paket `essen`** (`src/essen/`): Laden, Untersuchen, Rechnen, Karten.
3. **Oberflächen**: Kommandozeile `essen` und eine Streamlit-App, die nur auf `localhost` läuft.

Aufbau und Datenfluss: `docs/architektur.md`. Festlegungen mit Begründung: `docs/entscheidungen.md`.
Was als Nächstes kommt und was offen ist: `docs/fahrplan.md`.

## Grundregeln

- **Keine Daten ins Repository.** Geladene Dateien liegen in `data/` (oder `data_test/`), beides steht in `.gitignore`. Jede Person lädt selbst aus der Originalquelle.
- **Der Katalog ist die einzige Quelle für Adressen und Lizenzen.** Keine URLs im Code. Neue Quellen nur über `katalog/*.yaml` (Skill `neue-datenquelle`).
- **Nichts erfinden.** Keine geratenen URLs, Dateinamen, Stations-IDs oder Lizenzen. Unbestätigtes bekommt `status: ungeprueft` und einen Hinweis. Fehlt etwas, im Katalog als offene Frage notieren.
- **Erst inspizieren, dann rechnen.** Unbekannte Daten mit `uv run essen inspizieren ID` ansehen, bevor eine Analyse sie liest (Skill `daten-inspizieren`). Rasterkodierungen und Feldbedeutungen nie stillschweigend raten (E-009): lieber mit einer klaren Meldung abbrechen.
- **Logik ins Paket, nicht in die Oberfläche.** App-Seiten und CLI rufen nur Funktionen aus `essen` auf (Skill `app-erweitern`).
- **Lokal und privat.** Die App bleibt auf `localhost`, Telemetrie aus. Nichts veröffentlichen oder hochladen. Vor jeder Weitergabe: Skill `lizenz-pruefen`.
- **Testdaten sind erfunden** und müssen so gekennzeichnet bleiben. Nie Testdaten als echte Ergebnisse ausgeben.
- **Ehrliche Kennzahlen.** Modellwerte als Modellwerte bezeichnen, Fläche nicht als Bevölkerung ausgeben, Mindest-Bezugsflächen beachten (E-006, E-007).

## Befehle

```bash
uv sync                                   # Umgebung einrichten (Python 3.12, Pakete aus uv.lock)
uv run pytest                             # alle Tests, nur mit erfundenen Testdaten, ohne Internet
uv run ruff check src tests               # Stil und typische Fehler (Regeln in pyproject.toml)
scripts/pruefen.sh                        # vor dem Einchecken: ruff, Katalog, Tests (samt erzeugter Doku)
uv run essen katalog --pruefen            # Katalog prüfen
uv run essen katalog --doku               # docs/datenquellen.md neu erzeugen (nach jeder Katalogänderung)
uv run essen katalog [--thema klima]      # Datensätze auflisten
uv run essen info ID                      # alles zu einem Datensatz
uv run essen laden ID [ID …]              # aus der Originalquelle laden (--neu, --datei NAME, --ja)
uv run essen einlesen ID DATEI            # von Hand geladene Datei übernehmen
uv run essen status [--aufraeumen]        # Platz; entpackte Ordner nach Rückfrage löschen
uv run essen aktualisieren [ID …]         # neuere Stände bei den Quellen? (lädt nichts)
uv run essen inspizieren ID|PFAD          # Bericht nach data/inspektion/
uv run essen dienst ID                    # Ebenen eines WMS / Objektarten eines WFS
uv run essen analyse [ID] [-p k=v] [--export]
uv run essen vorbereiten [--ja]            # alle nötigen Daten laden und alle Themen rechnen
uv run essen pruefen-ergebnisse           # Analysen neu rechnen, mit docs/referenzwerte.yaml vergleichen
uv run essen schnell ID [--layer L]       # Vektordaten auf Stadtteile verteilen
uv run essen testdaten                    # erfundene Testdaten nach data_test/
uv run essen --testdaten BEFEHL           # Befehl mit den Testdaten
uv run essen app [--testdaten]            # App starten (http://localhost:8501)
```

## Aufbau des Pakets

| Modul | Aufgabe |
| --- | --- |
| `pfade.py` | alle Pfade; `ESSEN_DATEN` schaltet den Datenordner um |
| `katalog.py` | YAML lesen, prüfen, filtern, Quellenangaben, Markdown-Übersicht |
| `laden.py` | Downloads (`datei`, `verzeichnis`, `wfs`, `api`), Protokoll, Entpacken, Einlesen |
| `dienste.py` | WMS/WFS GetCapabilities lesen |
| `geo.py` | Stadtteile mit Feld-Erkennung, Stadtgebiet, CRS, `DatenFehlen` |
| `inspizieren.py`, `legenden.py` | Berichte über Vektor, Raster, Tabellen, ZIPs, Stildateien |
| `kennzahlen.py` | Flächen je Klasse (Vektor, Raster), Anteile, Zählungen, Mindestbezug |
| `analysen/` | `basis.py` (Analyse, Parameter, Ergebnis), eine Datei je Analyse, Registry in `__init__.py` |
| `einwohner.py` | Einwohner aus dem Zensus-Gitter in belasteten Flächen schätzen (E-013) |
| `zeitreihen.py` | Reihen, Trend und Vergleichswerte aus gespeicherten Stationsanalysen |
| `zeitkarte.py` | Karte über die Jahre: Jahrzehnt-Mittel, SVG-Pfade, Farben je Zeitpunkt (E-016); Anzeige in `app/zeitkarte.py` |
| `waechter.py` | Ergebnis-Wächter: stadtweite Kennzahlen gegen Referenzwerte prüfen |
| `begriffe.py`, `einordnung.py`, `hilfetexte.py` | Texte für Menschen: Glossar, Zahlen als Sätze, Hilfe je App-Seite |
| `datenerklaerung.py` | Datensätze in Worten (Katalogfeld `erklaerung`): Steckbrief für die Seite „Daten erklärt“, `docs/daten-erklaert.md` |
| `vorbereiten.py` | Alles vorbereiten: nötige Daten laden, alle Analysen rechnen |
| `steckbrief.py` | gespeicherte Kennzahlen je Stadtteil: Steckbrief, Vergleich zweier Themen, Korrelationen |
| `bezirke.py` | Kennzahlen je Stadtbezirk aus den gespeicherten Stadtteil-Ergebnissen (E-018) |
| `karte.py` | folium-Karten für die App (Kennzahlflächen, Umrisse, Punkte/Objekte, Rasterbild, WMS, Legende) |
| `diagramme.py` | altair-Diagramme: Punktleiste, sortierte Balken, Streudiagramm mit Feldern, Heatmap, kleine Karte |
| `vorschau.py` | Originaldaten ansehen: Dateiliste ohne Entpacken, Proben aus Vektor, Raster, CSV, JSON (E-014) |
| `punktebenen.py` | Punkte für die Karte: kühle Orte, Jungbäume, Ladesäulen, Lastenrad-Stationen, Pegel |
| `bericht.py` | eigenständige HTML-Seite mit MapLibre |
| `testdaten.py` | erfundene Daten im Format der echten |
| `cli.py`, `app/` | Oberflächen |

## Arbeitsweise

1. Vor dem Ändern `uv run pytest` laufen lassen, danach wieder. Neue Funktionen bekommen Tests in `tests/`, die ohne Internet laufen (lokaler HTTP-Server, Testdaten).
2. Für wiederkehrende Aufgaben die Skills unter `.claude/skills/*/SKILL.md` lesen und befolgen. Sie gelten auch für andere Agenten als Claude.
3. Nach Katalogänderungen `uv run essen katalog --pruefen` und `--doku`; der Test `test_doku_der_datenquellen_ist_aktuell` schlägt sonst fehl.
   Vor dem Einchecken `scripts/pruefen.sh` (empfohlen). `zip()` mit `strict=`, breite `except Exception` nur mit `# noqa: BLE001 - Grund`.
4. Neue Analysen tragen sich in `src/essen/analysen/__init__.py` ein, bekommen eine Methodik-Seite unter `docs/methodik/` und einen Eintrag in `docs/fahrplan.md`.
5. Oberfläche nach Änderungen ansehen: `uv run essen app --testdaten` und mit Playwright Screenshots machen (Skill `app-erweitern`).
6. Entscheidungen, die man später nicht umwerfen soll, in `docs/entscheidungen.md` anhängen.

## Konventionen

- Sprache Deutsch. Bezeichner ohne Umlaute (`flaeche_ha`, `stadtteil`), Texte für Menschen mit Umlauten.
- Flächen in EPSG:25832, Webkarten in EPSG:4326. Einheiten als Endung: `_ha`, `_pct`, `_m2`, `_c`, `_mm`.
- Ergebnistabellen je Stadtteil haben `gebiet_id`, `stadtteil`, `stadtteil_nr`.
- Meldungen sagen, was zu tun ist. Fehlende Daten: `DatenFehlen` (nennt den Befehl zum Laden).
- Zahlen für Menschen deutsch formatieren (`essen.text.zahl`, `prozent`, `groesse`).
- Farben für Karten: nur geprüfte Stufen verwenden (Skill `karte-gestalten`).

## Cloud-Sitzungen

In Cloud-Umgebungen sind die Datenportale meist gesperrt. Der Hook in `.claude/settings.json` richtet die
Umgebung ein und erzeugt Testdaten (`scripts/cloud-setup.sh`). Gesperrte Adressen nicht umgehen, sondern mit
Testdaten arbeiten oder die Freigabe nach `docs/cloud.md` einrichten lassen. Downloads in der Cloud
verschwinden mit der Sitzung.

## Stand und offene Punkte (11. Oktober 2026)

- Siebzehn Analysen rechnen mit echten Daten (dazu `kuehlorte`, `jungbaeume`, `umweltzone`, `hitzetage-raster`, `haushalte`, `klimatope`, `planungshinweise`, s. u.); die ersten zehn: `hitze-nacht`, `hitze-tag`, `versiegelung`, `gruenanteil`, `laerm`, `starkregen`, `betroffenheit`, `hitzetage-station`, `luft-station`, `mehrfachbelastung`. Kodierungen belegt (`katalog/zuordnungen/`), Ergebnisse gegengerechnet (Vermerke in den Methodik-Seiten).
- Mehrfachbelastung nach E-008 (festgelegt 11.10.2026): Hitze Nacht, Lärm, Starkregen; oberstes Fünftel je Thema. Hitze Tag, Versiegelung und Grün zählen nicht (korrelieren 0,8–0,97 mit Hitze Nacht).
- Lärm: acht Shapes der Stadt (Straßen 2011, sonst 2016), unterschiedlich aufgebaut; Download-Art `dateien` für mehrere Ressourcen. Starkregen: Klasse 1 der Karte (eine Riesenfläche) wird nicht gelesen.
- Einwohner nach E-013 (11.10.2026): `essen.einwohner` schätzt aus dem Zensus-Gitter (DL-DE BY 2.0) Einwohner in belasteten Flächen; Zusatzspalten in hitze-nacht, laerm, starkregen, mehrfachbelastung. Hauptkennzahlen bleiben Fläche.
- App (11.10.2026 für Einsteiger umgebaut): Bereiche „Essen entdecken“ (Start, Mein Stadtteil, Themen, Karte, Themen vergleichen, Entwicklung über die Jahre, Begriffe erklärt) und „Werkstatt“ (Alles vorbereiten, Daten laden, Neu berechnen, …). Jede Analyse hat Erklärfelder in einfacher Sprache, jede Seite eine Seitenhilfe; Anrede „Sie“. Außerdem: Analysen-Seite warnt vor veralteten Ergebnissen. Neue Befehle `essen aktualisieren` und `essen status --aufraeumen`.
- Stadtteilnummer ist `STADTT`, nicht `FID`. Klimaanalyse-Raster enthalten °C-Werte, Datei je Szenario unter `dateien` in der Zuordnung.
- Testdaten haben den Aufbau der echten Dateien und liegen innerhalb von `geo.essen_bbox`.
- Luft: `uba-jahresbilanzen` (49 API-Abfragen über `dateien` mit eigenen Namen; Downloads warten bei HTTP 429). Nur je Station, daher nicht in E-008.
- Ergebnis-Wächter: `essen pruefen-ergebnisse` vergleicht mit `docs/referenzwerte.yaml` (11.10.2026 festgeschrieben, alle zehn gleich; `kuehlorte`, `jungbaeume`, `umweltzone` am selben Tag ergänzt). Nach neuem Datenstand ausführen; `hitzetage-station` ändert sich mit jedem abgeschlossenen Jahr.
- Inspektion und `geo.vektordatei` lesen File-Geodatabases (`.gdb`-Ordner) als Vektorquelle.
- Lizenzen: Stand in `docs/fahrplan.md` (offen: Wahl 2025, VRR-GTFS, RVR, KoMonitor, nextbike NRW).
- Playwright ist Entwicklungsabhängigkeit (11.10.2026, mit dem Menschen abgestimmt). Screenshots: `uv run python .claude/skills/app-erweitern/screenshots.py [--echt]`; das Skript nimmt das vorhandene Chromium aus `~/.cache/ms-playwright`, nichts wird nachinstalliert.
- Oberfläche (11.10.2026, E-014): Diagramme mit altair, Klickkarte mit streamlit-folium, Werkstatt-Seite „Originaldaten ansehen“, Punktebenen auf der Karte. Drei neue Analysen: `kuehlorte`, `jungbaeume`, `umweltzone` (nicht in E-008). Screenshots warten auf Streamlit (`WARTEN_MS` verlängert die Wartezeit).
- Heiße Tage je Stadtteil (11.10.2026, E-015): `hitzetage-raster` aus den DWD-Jahresrastern (1 km; heiße Tage und Sommertage seit 1951, Jahresmittel seit 1881), flächengewichtet je Stadtteil; Jahreswerte in `Ergebnis.jahreswerte` (`jahreswerte.csv`). Modellwerte ohne Wärmeinsel, nicht in E-008. Seite „Entwicklung über die Jahre“ wählt den Stadtteil (`?stadtteil=`), vergleicht mit Essen gesamt und der Station Bredeney. Katalog: `download.alle: true` lädt alle passenden Dateien eines Ordners.
- Gestaltung (11.10.2026): Thema hell und dunkel in `.streamlit/config.toml`, Logo (`app/logo.svg`), Startseite mit Kopfbereich, Themenfarben und -symbole über `gemeinsam.thema_marke`/`kennzahl_kachel`. Feste Farben in Diagrammen nur, wo sie in beiden Modi lesbar sind (`punktleiste(dunkel=…)`). Screenshots auch mit `--dunkel`.
- Zeitliche Ansicht (11.10.2026, E-016): Karte über die Jahre (Abspielen, Schieber, kleine Karten je Jahrzehnt) über `Analyse.zeitachse` für `hitzetage-raster`, `versiegelung` (neuer Datensatz `bodenversiegelung-sat-nrw`, 2006–2018, getrennt von 2024), `jungbaeume` (Pflanzjahr) und die neue Analyse `haushalte` (2007–2025, nicht in E-008). Menü oben rechts wieder sichtbar (`toolbarMode = "viewer"`, dort hell/dunkel). `Ergebnis.laden` hält gelesene Ergebnisse im Speicher, bis sich die Dateien ändern.
- Daten erklärt (11.10.2026, Paket 7): Seite unter „Essen entdecken“, jeder Datensatz in Worten (herkunft, inhalt, nutzen, lesen) aus dem Katalogfeld `erklaerung`; `essen.datenerklaerung`, `docs/daten-erklaert.md` über `katalog --doku`. Texte nur aus Belegtem; Unbekanntes steht als unbekannt drin. Neue Datensätze bekommen die Erklärung gleich beim Eintragen.
- Starkregen ohne Gewässer (12.10.2026, E-017): Gewässer der Landbedeckung (optional) abgezogen, Anteil an der Landfläche; stadtweit 3,0 % statt 3,5 %. `-p gewaesser=mitzaehlen` rechnet wie vorher.
- Werte je Stadtbezirk (12.10.2026, E-018): `essen.bezirke` mittelt mit `Analyse.gewicht` wie der stadtweite Wert; Zuordnung aus `STADTBEZ` der Stadtteile (`felder.bezirk`); Namen nur „Stadtbezirk I–IX“.
- Klimatope und Planungshinweise (12.10.2026): neue Analysen `klimatope` und `planungshinweise` (nicht in E-008), Zuordnungen aus den Methodik-PDFs und an echten Daten geprüft; `kennzahlen.gueltig` repariert ungültige Flächen mit Rückfall auf „structure“; `Analyse.zusammensetzung` (gestapelte Balken) und `Analyse.verwandt` („Dazu passend“).
- Plan vom 10.10.2026 abgearbeitet. Offen: Luft als Kennzahl je Stadtteil (für E-008), offene Lizenzen. Details: `docs/fahrplan.md`.
