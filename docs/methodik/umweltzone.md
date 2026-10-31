# Umweltzone je Stadtteil

**Frage:** Welcher Anteil der Fläche eines Stadtteils liegt in der Umweltzone?

**Code:** `src/essen/analysen/umweltzone.py` · **Aufruf:** `uv run essen analyse umweltzone`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `umweltzone` | Grenze der Umweltzone (GeoJSON, WGS84, Stand 2024 laut Katalog) |

## Rechenweg

1. Die Datei enthält drei Flächen ohne beschreibende Felder (nur `FID`, `OBJECTID`, `ID`, `SHAPE_AREA`, `SHAPE_LEN`): eine große mit 156,2 km² und 17 Löchern sowie zwei kleine im Norden (5,1 und 0,7 km²). Geprüft am 11.10.2026: Die Flächen überschneiden sich nicht und liegen nicht ineinander. Sie werden deshalb vereinigt; die Löcher (Aussparungen) zählen nicht zur Zone.
2. Je Stadtteil: Fläche in der Zone und Anteil an der Stadtteilfläche (`kennzahlen.flaechenanteil_je_gebiet`).
3. Unter 5 ha Fläche bleibt der Anteil leer (`min_flaeche_ha`).
4. Der stadtweite Wert ist das flächengewichtete Mittel.

## Prüfung mit echten Daten (11.10.2026)

- Stadtweit liegen 77,0 % der Fläche in der Umweltzone; 21 Stadtteile liegen ganz darin (ab 99,5 %).
- Ganz außerhalb liegen unter anderem Überruhr-Holthausen, Überruhr-Hinsel, Burgaltendorf und Horst; teilweise Byfang (0,8 %), Freisenbruch (22,5 %), Kettwig (31,9 %), Kupferdreh (39,0 %), Schuir (41,8 %).
- Werte knapp unter 100 % (etwa Rüttenscheid 98,0 %) stammen von den Aussparungen, meist Autobahnen.

## Grenzen

- Die Zone ist eine Verkehrsregel, keine Messung der Luftqualität. Für Messwerte siehe `luft-station`.
- Ob und wie die Zone heute gilt, steht beim Anbieter; der Datensatz nennt Stand 2024.
- Die Bedeutung der Löcher ist nicht als Feld beschrieben; sie werden als Aussparungen gelesen, weil sie geometrisch Teil der Zonengrenze sind.

## Ergebnis

`data/processed/umweltzone/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/umweltzone.html`.
