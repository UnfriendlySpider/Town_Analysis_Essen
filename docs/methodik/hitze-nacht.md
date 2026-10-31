# Nächtliche Überwärmung je Stadtteil

**Frage:** Welcher Anteil der bebauten Fläche eines Stadtteils ist um 4 Uhr nachts wärmer als 20 °C?

**Code:** `src/essen/analysen/hitze_nacht.py` · **Aufruf:** `uv run essen analyse hitze-nacht`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `klimaanalyse-nacht-raster` | Lufttemperatur um 4 Uhr im Wirkraum, `PL_KY_NACHT_LT_EXT.tif` bzw. `_TYP.tif` (Standard) |
| `klimaanalyse-beschreibung` | Methodik und Nomenklatur als PDF; Beleg für die Zuordnung (optional) |
| `klimaanalyse-nacht-vektor` | Abgrenzung des Wirkraums bei reinen Temperaturrastern (optional); als Grundlage nur mit `-p quelle=vektor` |

## Rechenweg

1. Die Klimaanalyse NRW 2026 (LANUK, Modell FITNAH-3D, 25-m-Raster) beschreibt eine sommerliche Strahlungsnacht um 4 Uhr MEZ, in zwei Szenarien: typischer und extremer Sommertag. Das Raster enthält für den Wirkraum (Siedlungsgebiet) die Lufttemperatur in °C; Grün- und Freiflächen haben dort den Fehlwert −999 und stehen in einer eigenen Datei (Kaltluftvolumenstromdichte). Die acht Klassen bildet die Analyse aus der Temperatur, nach Methodik Karte Nacht, Tabelle 1 (gleich LANUK Fachbericht 171, Tabelle 6):

   | Klasse | Lufttemperatur um 4 Uhr | Bezeichnung |
   | --- | --- | --- |
   | 1 | bis 14 °C | sehr niedrige nächtliche Lufttemperaturen |
   | 2 | über 14 bis 15,5 °C | niedrige nächtliche Lufttemperaturen |
   | 3 | über 15,5 bis 17 °C | keine nächtliche Überwärmung |
   | 4 | über 17 bis 18,5 °C | schwache nächtliche Überwärmung |
   | 5 | über 18,5 bis 20 °C | mäßige nächtliche Überwärmung |
   | 6 | über 20 bis 21,5 °C | starke nächtliche Überwärmung |
   | 7 | über 21,5 bis 23 °C | sehr starke nächtliche Überwärmung |
   | 8 | über 23 °C | extreme nächtliche Überwärmung |

   Szenario mit `-p szenario=extrem` (Standard) oder `-p szenario=typisch`. Standard ist der extreme Sommertag, weil im typischen Szenario in Essen praktisch keine Fläche über 20 °C liegt (höchster Wert 20,04 °C) und die Kennzahl dann überall 0 wäre. Das Szenario steht in jedem Ergebnis.

2. Das Raster wird für das Stadtgebiet gelesen. Welche Datei, sagt die Zuordnung unter `dateien` je Szenario. Fehlt diese Angabe und liegen mehrere Raster im Datensatz, bricht die Analyse ab, statt eine Datei zu wählen (im echten ZIP liegen 14 Raster; das größte ist die Kaltluft). Wie die Klassen darin stecken, entscheidet in dieser Reihenfolge:
   - eine Zuordnung `zuordnungen/klimaanalyse-nacht-raster.yaml`, zuerst im Datenordner, dann in `katalog/` (Format in docs/katalog.md). Die geprüfte Zuordnung im Katalog liest die Werte als Temperatur (`lesart: temperatur`),
   - eine Legende aus einer Stildatei (QGIS `.qml`, `.sld`, `.lyrx`) in der Datenbeschreibung, über die Werte oder die Farben der Farbtabelle. Gibt es Stildateien mit „Nacht“ im Namen, zählen nur diese. Widersprechen sich Einträge für denselben Wert, wird der Wert nicht automatisch zugeordnet,
   - stetige Werte zwischen 5 und 35 werden als Temperatur in °C gelesen, Ganzzahlen von 50 bis 350 als Zehntelgrad; Werte unter 0 oder über 45 °C gelten als Fehlwert,
   - nur wenn es gar keine Legende gibt, werden die Werte 1 bis 8 direkt als Klassen gelesen (mit Hinweis, weil ungeprüft).

   Passt nichts davon, bricht die Analyse ab und schreibt eine Vorlage nach `data/zuordnungen/klimaanalyse-nacht-raster.vorlage.yaml`. Haben mehr als 1 % der Zellen keine Zuordnung, bricht sie ebenfalls ab und nennt die Werte. Es wird nie stillschweigend geraten.
   Das GeoPackage dient nie automatisch als Ersatz. Mit `-p quelle=vektor` werden nur Textfelder mit Klassennamen selbst erkannt; Zahlencodes oder Temperaturfelder brauchen `-p feld=… -p lesart=code|temperatur` und einen Beleg für ihre Bedeutung.
3. Mit `wirkraum: fehlwerte` in der Zuordnung (so bei den echten Daten) ist der Wirkraum genau die Menge der Zellen mit Wert. Im Stadtgebiet sind das 111,6 km²; die Kaltluftdatei deckt 93,7 km² ab, die übrigen 5,0 km² ohne Wert sind Gewässer. Ohne diese Angabe gibt es bei einem Temperaturraster keine Trennung von Wirkraum und Ausgleichsraum: Liegt das GeoPackage vor, werden Flächen aus Layern mit „Produktion“ (Kaltluftproduktion) oder „Wasser“ im Namen ausgeschlossen. Das ist eine Näherung und steht im Ergebnis als Hinweis.
4. Jede Rasterzelle zählt zu dem Stadtteil, in dem ihr Mittelpunkt liegt (Flächen in EPSG:25832). Bei 25 m Zellgröße liegt der Fehler an den Rändern weit unter einem Prozentpunkt.
5. Je Stadtteil: bebaute Fläche (Summe der Klassen 1 bis 8), Anteile jeder Klasse, Anteil über 20 °C (Klassen 6 bis 8) und über 21,5 °C (Klassen 7 und 8).
6. Hat ein Stadtteil weniger als 5 ha bebaute Fläche, bleibt der Anteil leer (Parameter `min_wirkraum_ha`), weil wenige Zellen den Wert stark verzerren.
7. Der stadtweite Wert ist das Mittel der Stadtteile, gewichtet mit ihrer bebauten Fläche (nur Stadtteile mit ausgewiesenem Anteil).
- Einwohner (Zensus-Gitter, optional, 11.10.2026): geschätzt 353.100 von 570.632 Einwohnern (61,9 %) wohnen in Fläche über 20 °C. Verfahren nach E-013 (`src/essen/einwohner.py`).

## Grenzen

- Modellwerte für eine sommerliche Strahlungsnacht (Szenario typisch oder extrem), keine Messungen und keine Häufigkeit von Hitzenächten.
- Gezählt wird Fläche, nicht Menschen. Eine Gewichtung mit dem Zensus-Gitter ist geplant (docs/fahrplan.md).
- Die Kodierung ist am 10.10.2026 mit Methodik-PDF und WMS-Legende abgeglichen (Beleg in der Zuordnung). Ändert das LANUK Dateinamen oder Aufbau, bricht die Analyse mit einer Meldung ab.
- Verkehrsflächen gehören zum Wirkraum, wenn das Raster dort Temperaturen hat; sie werden nicht eigens ausgeschlossen.

## Ergebnis

`data/processed/hitze-nacht/`: `tabelle.csv` (je Stadtteil), `gebiete.geojson` (mit Grenzen), `ergebnis.json` (Kennzahl, Hinweise, Quellen, Parameter). Mit `--export` zusätzlich `data/export/hitze-nacht.html`.
