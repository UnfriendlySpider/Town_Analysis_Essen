# Heiße Tage je Stadtteil (DWD-Raster)

**Frage:** Wie viele heiße Tage gibt es in meinem Stadtteil, und wie hat sich das seit 1951 verändert?

**Code:** `src/essen/analysen/hitzetage_raster.py` · **Aufruf:** `uv run essen analyse hitzetage-raster`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `dwd-raster-heisse-tage` | Anzahl heißer Tage (Höchstwert ab 30 °C) je Jahr, 1951 bis Vorjahr |
| `dwd-raster-sommertage` | Anzahl Sommertage (Höchstwert ab 25 °C) je Jahr, optional |
| `dwd-raster-jahresmittel` | Jahresmittel der Lufttemperatur in 1/10 °C, 1881 bis Vorjahr, optional |
| `stadtteile` | 50 Stadtteile |

Alle drei Raster kommen vom Climate Data Center des DWD (CC BY 4.0), eine Datei je Jahr (`grids_germany/annual/…`).
Aufbau laut den Datensatzbeschreibungen im selben Ordner (Stand 18.12.2018): ESRI-ASCII-Gitter, 654 × 866 Zellen
zu 1 km, Gauß-Krüger 3. Streifen (EPSG:31467), Fehlwert −999. Zehn Dateien des Jahresmittels (1881 bis 1890) sind
trotz der Endung `.asc.gz` ZIP-Archive; der Leser erkennt das an den ersten Bytes.

## Rechenweg

1. Aus jeder Jahresdatei wird nur der Ausschnitt um Essen gelesen, also die Zeilen und Spalten, die das Rechteck
   um die Stadtteile berühren.
2. Jede Gitterzelle wird mit jedem Stadtteil verschnitten (in EPSG:31467). Der Wert eines Stadtteils ist das
   **flächengewichtete Mittel** der Zellen, die er berührt; Fehlwerte zählen nicht. Liegt weniger als die Hälfte
   der Fläche in gültigen Zellen, gibt es keinen Wert. „Essen gesamt“ ist dasselbe für die Vereinigung aller
   Stadtteile.
3. Jahresmittel: Rasterwert × 0,1 = °C.
4. Je Stadtteil: Mittel im Vergleichszeitraum (Standard 1961 bis 1990) und in den letzten zehn Jahren, dazu die
   Änderung. Hauptkennzahl ist das Mittel der heißen Tage in den letzten zehn Jahren.
5. Die Jahreswerte je Stadtteil liegen zusätzlich in `jahreswerte.csv` und speisen die Seite „Entwicklung über
   die Jahre“.

## Grenzen

- **Modellwerte.** Der DWD rechnet die Stationswerte auf Meeresniveau um, interpoliert sie (inverse
  Distanzwichtung) und rechnet sie auf die Höhe der Zelle zurück. Laut Beschreibung sind **städtische Wärmeinsel
  und Kaltluftabfluss nicht abgebildet**. Unterschiede zwischen Stadtteilen kommen vor allem von Höhe und Lage,
  nicht von der Bebauung. Für die Hitze in dicht bebauten Vierteln sind `hitze-tag` und `hitze-nacht` da.
- Eine Zelle ist 1 km² groß; viele Stadtteile berühren nur wenige Zellen. Benachbarte Stadtteile unterscheiden
  sich deshalb kaum (2016–2025: 9,3 bis 12,5 heiße Tage). Die Kartenstufen sind deshalb 2 Tage breit.
- Das Messnetz hat sich über die Jahre verändert; frühe Jahre beruhen auf weniger Stationen.

## Gegenrechnung (11.10.2026)

- Stadtteil Bredeney im Raster gegen die Station Essen-Bredeney (`hitzetage-station`), 75 gemeinsame Jahre
  1951–2025: Korrelation der heißen Tage 0,99, das Raster liegt im Mittel 0,35 Tage höher (höchstens 4 Tage).
  Jahresmittel: Korrelation 0,999, Raster im Mittel 0,13 °C wärmer. Die Station fließt selbst in das Raster ein,
  der Abgleich prüft also vor allem Lesen, Umrechnung und Lage, nicht die Güte des Modells.
- Essen gesamt: 1961–1990 im Mittel 4,3 heiße Tage im Jahr, 2016–2025 im Mittel 10,6.

## Ergebnisdateien

`data/processed/hitzetage-raster/`: `tabelle.csv` (je Stadtteil), `jahreswerte.csv` (je Stadtteil und Jahr,
dazu `essen`), `gebiete.geojson`, `ergebnis.json`.
