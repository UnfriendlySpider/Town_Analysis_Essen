# Handlungsbedarf bei Hitze je Stadtteil

**Frage:** Welcher Anteil der bebauten Fläche eines Stadtteils hat laut Planungshinweiskarte dringenden Handlungsbedarf wegen Hitze?

**Code:** `src/essen/analysen/planungshinweise.py` · **Aufruf:** `uv run essen analyse planungshinweise`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `klimaanalyse-planungshinweise` | Planungshinweiskarte der Klimaanalyse NRW 2026 (LANUK), Layer `PL_KY_PHK_HP` (Wirkraum) |
| `zensus-2022-gitter` (optional) | geschätzte Einwohner in Flächen mit dringendem Handlungsbedarf (E-013) |

## Rechenweg

1. Jede Fläche des Wirkraums trägt eine Handlungspriorität als Text („Handlungspriorität 1“ … „6“) und einen Planungshinweis, der mit der Stufe beginnt. Laut Methodik der Planungshinweiskarte (LANUK, Stand 03/2026) gilt: 1 + 2 dringender, 3 + 4 erweiterter, 5 mäßiger, 6 kein Handlungsbedarf. Grundlage ist die nächtliche Überwärmung in beiden Szenarien (typischer und extremer Sommertag, Tabelle 1 der Methodik).
2. Die Zuordnung steht in `katalog/zuordnungen/klimaanalyse-planungshinweise.yaml`. Die Analyse prüft, dass jede Priorität beschrieben ist und der Hinweistext mit der passenden Stufe beginnt; sonst bricht sie ab (E-009).
3. Gelesen werden nur Flächen mit `GN = 'Essen'`. 11 Flächen sind ungültig; `kennzahlen.gueltig` repariert sie, 5 davon haben danach keine Fläche mehr und fallen weg (0,5 ha).
4. Je Stadtteil: Fläche je Stufe, bezogen auf die bebaute Fläche (Wirkraum) des Stadtteils. Unter 5 ha Wirkraum kein Anteil (Parameter `min_wirkraum_ha`). Der stadtweite Wert ist mit dem Wirkraum gewichtet.

## Prüfung mit echten Daten (12.10.2026)

- 5.631 Flächen in Essen, Prioritäten 1 bis 5 (6 kommt nicht vor). Kreuztabelle Priorität × Hinweistext ohne Abweichung.
- Stadtweit 46,5 % der bebauten Fläche mit dringendem Handlungsbedarf (5.005 von 10.763 ha). Unabhängig aus der Karte gerechnet (ganze Flächen, ohne Stadtteile): ebenfalls 46,5 % (5.005,7 von 10.767,6 ha). NRW laut Methodik: 32,5 %.
- Höchste Werte: Stadtkern 100,0 %, Westviertel 99,6 %, Ostviertel 95,5 %, Nordviertel 90,0 %, Bergeborbeck 88,6 %. Niedrigste: Fulerum 1,4 %, Byfang 2,8 %, Margarethenhöhe 3,2 %.
- Einwohner: geschätzt 274.000 (48,0 %) wohnen anteilig in solchen Flächen. Die Karte selbst nennt 293.411 Einwohner in Flächen mit Priorität 1 oder 2; sie zählt ganze Flächen, die Schätzung hier teilt Zellen anteilig nach Fläche.
- Korrelation mit „Hitze in der Nacht“ über die Stadtteile: 0,97. Das Thema ist aus derselben Nachtrechnung abgeleitet und zählt deshalb nicht zur Mehrfachbelastung (E-008).

## Grenzen

- Eine Empfehlung für die Planung, aus einem Modell der Nacht; keine Messung und kein Grenzwert.
- Bezug ist die bebaute Fläche, nicht die Zahl der Menschen (E-007).
- Die Karte sagt nicht, was im Stadtteil schon geplant oder umgesetzt ist.

## Ergebnis

`data/processed/planungshinweise/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`.
