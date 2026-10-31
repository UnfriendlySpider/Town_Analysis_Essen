# Stadtklima nach Klimatopen je Stadtteil

**Frage:** Welcher Anteil der Fläche eines Stadtteils gehört zu Klimatopen dichter Bebauung (Stadt-, Innenstadt- und dichtes Gewerbeklima)?

**Code:** `src/essen/analysen/klimatope.py` · **Aufruf:** `uv run essen analyse klimatope`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `klimaanalyse-klimatope` | Klimatopkarte der Klimaanalyse NRW 2026 (LANUK), Layer `PL_KY_KLIMATOP` |

## Rechenweg

1. Jede Fläche trägt den Klimatop als Zahl (`KT_R02_2`) und als Text (`Klimatoptyp`). Bedeutung laut Methodik der Klimatopkarte (LANUK, Stand 03/2026), Tabellen 2 und 3: 1 Gewässer-, Seeklima, 2 Freilandklima, 3 Waldklima, 4 Klima innerstädtischer Grünflächen, 5 Vorstadtklima, 6 Stadtrandklima (20–40 % überbaut), 7 Stadtklima (über 40 % überbaut), 8 Innenstadtklima, 9 Gewerbe-, Industrieklima offen, 10 dicht (über 70 % versiegelt und über 20 % überbaut), −999 Straßenverkehr, −99 Bahnverkehr, −9 keine Angabe.
2. Die Zuordnung (`katalog/zuordnungen/klimaanalyse-klimatope.yaml`) fasst sie zu Gruppen zusammen: Grün, Wald und Wasser (1–4), lockere Bebauung und offenes Gewerbe (5, 6, 9), dichte Bebauung und dichtes Gewerbe (7, 8, 10), Straßen und Bahn. Zahl und Text müssen zusammenpassen, sonst Abbruch (E-009).
3. Splitterflächen unter 1 m² fallen weg. Darunter sind 3 Flächen mit Code 0 ohne Text, den keine Tabelle der Methodik nennt; ein Code 0 mit Fläche würde die Analyse abbrechen.
4. Je Stadtteil: Fläche je Klimatop und Gruppe, bezogen auf die von der Karte bedeckte Fläche. Kennzahl ist der Anteil der dichten Gruppe; unter 5 ha kein Anteil. Der stadtweite Wert ist mit der Fläche gewichtet.

## Prüfung mit echten Daten (12.10.2026)

- 23.761 Flächen im Rechteck um Essen, 12 Klimatoptypen; Kreuztabelle Zahl × Text ohne Abweichung, „keine Angabe“ (−9) kommt nicht vor.
- Stadtweit 8,9 % dichte Klimatope, 46,9 % Grün, Wald und Wasser.
- Höchste Werte: Stadtkern 66,9 %, Westviertel 53,7 %, Nordviertel 38,1 %, Ostviertel 35,7 %, Bergeborbeck 34,6 %.
- Die Karte bedeckt 21.044 ha bei 21.027 ha Stadtfläche: Flächen überlappen sich geringfügig (0,08 %).
- Korrelation mit „Hitze in der Nacht“ über die Stadtteile: 0,77.

## Grenzen

- Beschreibt, wie dicht gebaut wird und welches Kleinklima dazu passt, nicht wie warm es tatsächlich wird (dafür Hitze in der Nacht und Hitze am Tag).
- Abgeleitet aus Nutzung, Überbauung und Versiegelung; keine Messung.
- Bezug ist die Fläche, nicht die Zahl der Menschen (E-007). Nicht Teil der Mehrfachbelastung (E-008).

## Ergebnis

`data/processed/klimatope/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`.
