# Wärmebelastung am Tag je Stadtteil

**Frage:** Welcher Anteil der Fläche eines Stadtteils hat um 14 Uhr eine extrem starke Wärmebelastung (PET über 41 °C)?

**Code:** `src/essen/analysen/hitze_tag.py` · **Aufruf:** `uv run essen analyse hitze-tag [-p szenario=typisch]`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `klimaanalyse-tag-raster` | PET um 14 Uhr, `PL_KY_TAG_EXT.tif` bzw. `PL_KY_TAG_TYP.tif` |
| `klimaanalyse-beschreibung` | Methodik und Nomenklatur als PDF; Beleg für die Zuordnung (optional) |

## Rechenweg

1. Die Klimaanalyse NRW 2026 (LANUK, Modell FITNAH-3D, 25-m-Raster) gibt für 14 Uhr MEZ die physiologisch äquivalente Temperatur (PET) in °C an, für einen typischen und einen extremen Sommertag. PET fasst Lufttemperatur, Strahlung, Wind und Feuchte zu der Temperatur zusammen, die eine Person im Freien empfindet.
2. Welche Datei je Szenario gilt, steht in `katalog/zuordnungen/klimaanalyse-tag-raster.yaml` (geprüft am 10.10.2026). Fehlt die Angabe, bricht die Analyse ab.
3. Klassen nach VDI 3787 Blatt 2 (Methodik Karte Tag, Tabelle 1). Die Klassen bis 23 °C sind zusammengefasst, weil sie in Essen kaum vorkommen:

   | Klasse | PET | Belastung |
   | --- | --- | --- |
   | 1 | bis 23 °C | kein thermischer Stress oder kühler |
   | 2 | über 23 bis 29 °C | leichte Wärmebelastung |
   | 3 | über 29 bis 35 °C | moderate Wärmebelastung |
   | 4 | über 35 bis 41 °C | starke Wärmebelastung |
   | 5 | über 41 °C | extrem starke Wärmebelastung |

4. Am Tag trennt die Klimaanalyse nicht nach Wirk- und Ausgleichsraum. Bezug ist deshalb die ganze Fläche des Stadtteils mit Wert (in Essen alle Zellen bis auf eine), einschließlich Wald, Wiesen und Wasser.
5. Jede Zelle zählt zu dem Stadtteil, in dem ihr Mittelpunkt liegt (EPSG:25832). Je Stadtteil: bewertete Fläche, Anteil jeder Klasse, Anteil über 41 °C und über 35 °C, mittlere PET.
6. Unter 5 ha bewerteter Fläche bleibt der Wert leer (Parameter `min_flaeche_ha`). Bei 50 Stadtteilen von 91 bis 1.535 ha tritt das in Essen nicht auf.
7. Der stadtweite Wert ist das flächengewichtete Mittel der Stadtteile.

Standard ist wie bei `hitze-nacht` der extreme Sommertag: Im typischen Szenario liegen nur 4,3 % der Stadtfläche über 41 °C, im extremen 43,0 %.

## Grenzen

- Modellwerte für einen sommerlichen Strahlungstag, keine Messungen und keine Häufigkeit heißer Tage (dafür `hitzetage-station`).
- 25 m Auflösung: Schatten in Straßenschluchten oder unter einzelnen Bäumen bildet die Karte nicht ab (Methodik Karte Tag, Fazit).
- Die Kennzahl bezieht sich auf Fläche, nicht auf Menschen (E-007). Ein Stadtteil mit viel Wald hat einen niedrigen Anteil, auch wenn seine bebauten Teile stark belastet sind.
- Am Tag ist die Belastung vor allem eine Frage der Strahlung. Freiflächen ohne Schatten (Äcker, Brachen, Gewerbe) können ebenso hoch belastet sein wie Innenstädte.

## Ergebnis

`data/processed/hitze-tag/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/hitze-tag.html`.

Erster Lauf mit echten Daten (10.10.2026, extremer Sommertag): stadtweit 43,0 % der Fläche über 41 °C. Am höchsten liegen Stadtkern (95,9 %), Ostviertel (86,2 %), Südviertel (76,8 %), Westviertel (76,4 %) und Holsterhausen (74,6 %).
