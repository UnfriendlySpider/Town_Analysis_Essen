# Versiegelte Fläche je Stadtteil

**Frage:** Welcher Anteil der Fläche eines Stadtteils ist versiegelt?

**Code:** `src/essen/analysen/versiegelung.py` · **Aufruf:** `uv run essen analyse versiegelung`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `bodenversiegelung-nrw` | Versiegelungsmaske 2024 für Essen, 0,5-m-Raster (`Versiegelungsmaske_2024_Essen.tif`) |
| `bodenversiegelung-sat-nrw` | optional, nur für den Verlauf: Versiegelungsgrad in % aus Satellitendaten (Copernicus), 2006, 2009, 2012, 2015 (20 m) und 2018 (10 m) |

## Rechenweg

1. Die luftbildbasierte Bodenversiegelung des LANUK (Projekt EBOVE, KI-Segmentierung von Luftbildern 2022 bis 2024) teilt jede Zelle von 0,5 × 0,5 m in „versiegelt“ und „nicht versiegelt“ ein. Fehlwert ist 3.
2. Welcher Rasterwert „versiegelt“ bedeutet, steht im Katalog unter `felder.versiegelt` (Wert 1). Die Methodik des Anbieters nennt die Codes nicht. Belegt ist die Zuordnung über die Gemeindetabelle des LANUK: Essen 36,5 % versiegelt, und genau so viele Zellen haben den Wert 1. Fehlt die Angabe im Katalog, bricht die Analyse ab.
3. Das Raster hat 1,4 Milliarden Zellen und wird in Streifen von 1.024 Zeilen gelesen (`kennzahlen.flaechen_nach_wert_rasterdatei`). Jede Zelle zählt zu dem Stadtteil, in dem ihr Mittelpunkt liegt.
4. Je Stadtteil: bewertete Fläche (Zellen mit 0 oder 1), versiegelte Fläche, Anteil versiegelt und Abdeckung (bewertete Fläche geteilt durch die Fläche des Stadtteils). Liegt die Abdeckung unter 99 %, nennt das Ergebnis den Stadtteil.
5. Unter 5 ha bewerteter Fläche bleibt der Anteil leer (Parameter `min_flaeche_ha`). Bei 50 Stadtteilen von 91 bis 1.535 ha tritt das in Essen nicht auf.
6. Der stadtweite Wert ist das flächengewichtete Mittel der Stadtteile.

## Prüfung mit echten Daten (10.10.2026)

- Stadtweit 36,47 % versiegelt. Die Gemeindetabelle des LANUK (`Bodenversiegelung-Luftbildbasiert-Gemeinde_2024`) nennt für Essen 36,5 %.
- Bewertet sind 21.021,4 ha von 21.026,9 ha. Die fehlenden 5,5 ha liegen am Stadtrand, wo die Grenze im Raster und die Stadtteilgrenzen leicht voneinander abweichen; die geringste Abdeckung eines Stadtteils ist 99,8 %.
- Am stärksten versiegelt: Stadtkern (91,9 %), Südviertel (77,5 %), Südostviertel (71,1 %), Holsterhausen (71,0 %), Westviertel (67,9 %). Am wenigsten: Fischlaken (9,5 %), Schuir (11,3 %), Heidhausen (12,3 %), Byfang (12,8 %).
- Rechenzeit etwa 30 Sekunden.

## Verlauf 2006 bis 2018 (Satellitendaten)

Ist `bodenversiegelung-sat-nrw` geladen (bei „Alles vorbereiten“ dabei), kommt eine zweite, getrennte Reihe dazu.
Sie steht in `jahreswerte.csv` und ist auf der Seite „Themen“ unter „Verlauf über die Jahre“ als Karte zu sehen.

1. Je Jahr gibt es ein Raster. Jahr und Zellgröße stehen im Dateinamen (`VG_20m_2006_Essen.tif`). Die Raster sind
   unterschiedlich aufgebaut (EPSG:3035 oder 25832, uint8, int8 oder float32); jedes wird in seiner eigenen
   Projektion gelesen.
2. Jede Zelle enthält den Versiegelungsgrad in Prozent, laut Methodik des LANUK von 0 bis 100. Andere Werte zählen
   nicht, etwa 254 im Raster 2012.
3. Je Stadtteil ist das Mittel der Zellen mit Mittelpunkt im Stadtteil der Wert (`kennzahlen.mittel_je_gebiet_rasterdatei`).
   Unter 5 ha gültiger Fläche bleibt er leer.

Prüfung (11.10.2026): Das Mittel für ganz Essen trifft die Gemeindewerte des Anbieters auf 0,01 Prozentpunkte.
Die Werte sind 2006 28,56 %, 2009 28,76 %, 2012 28,83 %, 2015 28,86 % und 2018 30,80 %. Von 2006 bis 2015 ändert sich in fast
allen Stadtteilen weniger als ein Prozentpunkt. Die Ausnahme ist das Westviertel (61,8 % auf 72,0 %, vor allem
2006 bis 2009).

Grenzen der Reihe:
- **Bruch 2018:** Der Wechsel von 20 auf 10 m Auflösung hebt die Werte. Laut LANUK kommt der Anstieg 2018 vor
  allem daher, nicht von neuer Bebauung. Der Stadtkern sinkt 2018 sogar (89,4 % auf 85,6 %).
- **Nicht mit 2024 vergleichbar:** Die Hauptkennzahl stammt aus Luftbildern (versiegelt ja/nein, 0,5 m). Die
  Satellitenreihe ist ein mittlerer Versiegelungsgrad aus 20-m-Zellen. Essen hat 36,5 % gegenüber 30,8 %, und das
  liegt an der Methode, nicht an der Zeit. Deshalb hängt die App 2024 nicht an die Reihe an.

## Grenzen

- Nur zwei Klassen: Teilversiegelung (Rasengittersteine, Schotter) ist nicht eigens ausgewiesen.
- KI-Erkennung aus Luftbildern: Bäume über Straßen verdecken Versiegelung, Dachbegrünung zählt als versiegelt. Die Luftbilder stammen aus 2022 bis 2024 (je Kachel verschieden, siehe Bildflugdatum beim Anbieter).
- Bezug ist die ganze Fläche des Stadtteils, auch Wald und Wasser. Ein Stadtteil mit großem Wald hat deshalb einen niedrigen Anteil, auch wenn seine Siedlung dicht bebaut ist.

## Ergebnis

`data/processed/versiegelung/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`, mit Satellitendaten auch `jahreswerte.csv`. Mit `--export` zusätzlich `data/export/versiegelung.html`.
