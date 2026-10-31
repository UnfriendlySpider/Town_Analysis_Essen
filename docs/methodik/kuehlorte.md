# Kühle Orte in der Nähe je Stadtteil

**Frage:** Welcher Anteil der Fläche eines Stadtteils liegt höchstens 300 m Luftlinie von einem kühlen Ort entfernt?

**Code:** `src/essen/analysen/kuehlorte.py` · **Aufruf:** `uv run essen analyse kuehlorte [-p abstand_m=500] [-p orte=draussen]`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `kuehlorte` | Kühle Orte der Stadt Essen (GeoJSON, WGS84), 547 Punkte mit `ART`, `ORT` (Außen/Innen), `OEFFNUNGSZ`, `KOSTEN` |
| `zensus-2022-gitter` (optional) | Einwohner im Umkreis (E-013) |

## Rechenweg

1. Um jeden kühlen Ort wird ein Kreis mit dem Radius `abstand_m` gelegt (Standard 300 m, etwa fünf Minuten zu Fuß bei geradem Weg). Die Kreise werden vereinigt, damit sich überlappende Flächen einmal zählen.
2. Je Stadtteil: Fläche in den Kreisen (`kennzahlen.flaechenanteil_je_gebiet`), Anteil an der Stadtteilfläche, dazu die Zahl der Orte im Stadtteil.
3. Mit `orte=draussen` zählen nur Orte mit `ORT = Außen` (517 von 547).
4. Unter 5 ha Fläche bleibt der Anteil leer (`min_flaeche_ha`).
5. Ist das Zensus-Gitter geladen, schätzt `einwohner.in_flaeche` die Einwohner in den Kreisen. Hauptkennzahl bleibt die Fläche (E-013).
6. Der stadtweite Wert ist das flächengewichtete Mittel der Stadtteile.

## Prüfung mit echten Daten (11.10.2026)

- Stadtweit liegen 43,0 % der Fläche höchstens 300 m von einem kühlen Ort entfernt; nur Orte im Freien: 42,2 %.
- Am höchsten: Südostviertel (99,1 %), Stadtkern (97,1 %), Steele (83,7 %), Huttrop (81,1 %). Am niedrigsten: Schuir (3,8 %), Byfang (9,5 %), Bergeborbeck (10,9 %), Fischlaken (14,6 %).
- Geschätzt 416.800 von 570.632 Einwohnern (73,0 %) wohnen im Umkreis. Der Anteil der Menschen ist höher als der Anteil der Fläche, weil die Orte dort liegen, wo viele Menschen wohnen.

## Grenzen

- Luftlinie, nicht Fußweg: Straßen, Bahnlinien, Gewässer und Zäune verlängern den Weg.
- Jeder Ort zählt gleich, ob kleiner Spielplatz oder Grugapark. Öffnungszeiten und Eintritt (`OEFFNUNGSZ`, `KOSTEN`) zählen nicht.
- Bezug ist die ganze Fläche des Stadtteils, auch Wald und Felder. In waldreichen Stadtteilen ist der Wald selbst oft der kühle Ort, steht aber nicht in der Liste.

## Ergebnis

`data/processed/kuehlorte/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/kuehlorte.html`.
