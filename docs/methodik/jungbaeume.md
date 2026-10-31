# Jungbäume der Stadt je Stadtteil

**Frage:** Wie viele Bäume hat die Stadt seit 2008 je Quadratkilometer eines Stadtteils gepflanzt?

**Code:** `src/essen/analysen/jungbaeume.py` · **Aufruf:** `uv run essen analyse jungbaeume`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `stadtbaeume` | WFS der Stadt Essen, Ebene `Stadtbaeume_Jungbaeume` (GML, EPSG:25832), 13.306 Punkte |

## Rechenweg

1. Die Punkte werden mit `geo.lies_vektor` gelesen. Fehlt das Feld `PFLANZJAHR`, bricht die Analyse ab, weil dann vermutlich eine andere Ebene geladen wurde.
2. Es zählen Bäume mit Pflanzjahr ab dem Parameter `ab_jahr` (Standard 2008, das früheste Jahr in den Daten).
3. Jeder Baum zählt zu dem Stadtteil, in dem er liegt (`kennzahlen.punkte_je_gebiet`). Bezug ist die ganze Fläche des Stadtteils in km².
4. Unter 5 ha Fläche bleibt der Wert leer (Parameter `min_flaeche_ha`); das tritt in Essen nicht auf.
5. Der stadtweite Wert ist die Zahl aller gezählten Bäume geteilt durch die Fläche aller Stadtteile.

## Prüfung mit echten Daten (11.10.2026)

- Stadtweit 63 Jungbäume je km², 13.306 Bäume; alle liegen in einem Stadtteil.
- Am meisten: Westviertel (541,7 je km²), Stadtkern (263,9), Altendorf (261,6), Nordviertel (239,5). Am wenigsten: Schuir (1,6), Byfang (2,9), Fischlaken (13,2), Kettwig (15,4).
- Die Verteilung ist schief (Median 60, Mittel 84): In dicht bebauten Stadtteilen pflanzt die Stadt an Straßen, in den waldreichen Stadtteilen im Süden kaum.

## Grenzen

- Der Datensatz enthält nur Jungbäume der Stadt (Hinweis im Katalog). Wald, Parkbäume, ältere Straßenbäume und private Bäume fehlen. Für das Grün insgesamt siehe `gruenanteil`.
- Viele neue Bäume können auch heißen, dass vorher Bäume gefällt wurden. Abgänge stehen nicht in den Daten.
- Das Feld `BEWÄSSERU` (J/N) wird nicht ausgewertet; seine genaue Bedeutung ist nicht belegt (E-009).

## Ergebnis

`data/processed/jungbaeume/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/jungbaeume.html`.
