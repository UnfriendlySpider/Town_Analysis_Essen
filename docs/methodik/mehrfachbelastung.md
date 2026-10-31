# Mehrfachbelastung je Stadtteil

**Frage:** In wie vielen Themen (Hitze in der Nacht, Lärm, Starkregen) liegt ein Stadtteil im obersten Fünftel Essens?

**Code:** `src/essen/analysen/mehrfachbelastung.py` · **Aufruf:** `uv run essen analyse mehrfachbelastung`

## Regel (E-008)

Festgelegt in `docs/entscheidungen.md`, E-008 (11.10.2026):

- **Themen:** Hitze in der Nacht (`hitze-nacht`, Anteil der bebauten Fläche über 20 °C), Lärm (`laerm`, Anteil der Fläche nachts über 55 dB(A)), Starkregen (`starkregen`, Anteil der Fläche mit 25 cm Einstau und mehr). Jeweils mit den Standard-Einstellungen der Analyse.
- **Schlechteste Klasse:** das oberste Fünftel der Stadtteile je Thema. Bei 50 Stadtteilen sind das die 10 mit den höchsten Werten; wer an der Grenze gleichauf liegt, zählt mit.
- **Zählen ohne Gewichtung:** Ergebnis ist die Zahl der Themen (0 bis 3), in denen ein Stadtteil oben liegt.

Warum nicht mehr Themen: Über die 50 Stadtteile korrelieren Hitze am Tag (0,80), Versiegelung (0,91) und Grünanteil (−0,92) eng mit der Hitze in der Nacht, Versiegelung und Grün untereinander mit −0,97. Sie messen denselben Block „dichte Bebauung“; mitgezählt würden dicht bebaute Stadtteile bis zu viermal belastet. Lärm hängt mäßig damit zusammen (0,77), Starkregen kaum (−0,10). Die Matrix steht in der App unter **Themen vergleichen**.

## Rechenweg

1. Für jedes Thema das gespeicherte Ergebnis lesen. Fehlt es oder passt es nicht zu den Standard-Einstellungen oder zu neueren Daten (`analysen.basis.veraltet`), wird es neu gerechnet und gespeichert.
2. Je Thema die Grenze des obersten Fünftels bestimmen und jeden Stadtteil markieren. Stadtteile ohne Wert zählen in diesem Thema nicht (Hinweis im Ergebnis).
3. Markierungen je Stadtteil zählen.

## Ergebnis mit echten Daten (11.10.2026)

- Grenzen des obersten Fünftels: Hitze in der Nacht ab 76,5 %, Lärm ab 36,0 %, Starkregen ab 3,8 % (11 Stadtteile wegen Gleichstand).
- 27 Stadtteile in keinem Thema oben, 15 in einem, 8 in zwei, keiner in allen drei.
- In zwei Themen: Stadtkern, Ostviertel, Westviertel, Südviertel, Bergeborbeck, Vogelheim (je Hitze und Lärm), Dellwig und Karnap (je Lärm und Starkregen).
- Starkregen liegt fast überall woanders als Hitze und Lärm: Werden, Rellinghausen, Heisingen, Kettwig, Steele sind nur dort oben. Bei den Stadtteilen an der Ruhr ist ein großer Teil der tiefen Fläche Gewässer (siehe `docs/methodik/starkregen.md`).

- Einwohner (E-013, Zensus-Gitter): In den 8 Stadtteilen mit mindestens zwei Themen wohnen geschätzt 52.700 von 570.632 Einwohnern (9,2 %). Das sind die Einwohner der Stadtteile, nicht nur die der belasteten Flächen.

## Grenzen

- **Relativ, nicht absolut:** Das oberste Fünftel gibt es immer, auch wenn ganz Essen wenig belastet wäre. „Oben“ heißt „im Essener Vergleich hoch“, nicht „über einem Grenzwert“.
- Die Einzelthemen haben eigene Grenzen (Modellwerte, Stand der Daten: Lärm 2011/2016, Starkregen 2022, Klimaanalyse 2026). Sie gelten hier mit.
- Bezug ist die Fläche, nicht die Zahl der Betroffenen (E-007).
- Luft fehlt noch; sobald es eine Kennzahl je Stadtteil gibt, kommt sie als viertes Thema dazu (E-008).

## Ergebnis

`data/processed/mehrfachbelastung/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/mehrfachbelastung.html`.
