# Überflutung bei Starkregen je Stadtteil

**Frage:** Welcher Anteil der Landfläche eines Stadtteils (ohne Gewässer) steht nach einem 100-jährlichen Starkregen 25 cm oder tiefer unter Wasser?

**Code:** `src/essen/analysen/starkregen.py` · **Aufruf:** `uv run essen analyse starkregen`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `starkregen-essen` | Starkregengefahrenkarte der Stadt Essen (`Ueberflutung_Kategorien.shp`, EPSG:4647, erstellt 2022) |
| `landbedeckung-nrw` (optional) | Gewässer (Layer `lb_binnengewaesser`, Gruppe `wasser` der geprüften Zuordnung), werden abgezogen (E-017) |

## Rechenweg

1. Die Karte zeigt die Einstautiefe unmittelbar nach einem 100-jährlichen Starkregen, ohne Wirkung der Kanalisation, in drei Klassen (Beschreibung im Portal). Jede Fläche trägt die Klasse als Zahl (`gridcode`) und als Text (`Einstautie`):

   | gridcode | Einstautiefe | Fläche in der Karte |
   | --- | --- | --- |
   | 1 | 0 bis unter 0,05 m | 17.289 ha |
   | 2 | 0,05 bis unter 0,25 m | 1.969 ha |
   | 3 | 0,25 m und mehr | 778 ha |

   Die Zuordnung steht in `katalog/zuordnungen/starkregen-essen.yaml`. Die Analyse prüft vor dem Rechnen, dass jeder Code beschrieben ist und Zahl und Text zusammenpassen; sonst bricht sie ab (E-009).
2. Klasse 1 ist im Original eine einzige Fläche mit 3,3 Millionen Ecken und 206.820 Löchern, die sich praktisch nicht verschneiden lässt. Gelesen werden deshalb nur die Klassen 2 und 3 (499.610 Flächen).
3. `kennzahlen.flaechen_nach_klasse` zählt Flächen, die ganz in einem Stadtteil liegen, direkt; nur die übrigen werden verschnitten.
4. **Gewässer abziehen (E-017, Standard seit 12.10.2026):** Die Gewässerflächen der Landbedeckung werden vereinigt; `kennzahlen.schnitt_mit` schneidet nur die Einstauflächen, die sie berühren. Die Teile in Gewässern (`tief_gewaesser_ha`) werden von `tief_ha` und `flach_ha` abgezogen. Die Landfläche ist `land_ha = flaeche_ha − gewaesser_ha`.
5. Je Stadtteil: Fläche ab 25 cm und ab 5 cm an Land, bezogen auf die **Landfläche des Stadtteils**. Ohne Landbedeckung (oder mit `-p gewaesser=mitzaehlen`) wie vor E-017: Gewässer zählen mit, Bezug ist die ganze Fläche. Die Karte deckt laut `Shape_Area` 95,3 % der Stadtfläche ab; der Rest ist nicht modelliert und zählt als ohne Einstau.
6. Unter 5 ha Bezugsfläche bleibt der Anteil leer (Parameter `min_flaeche_ha`). Der stadtweite Wert ist das mit der Landfläche gewichtete Mittel.

## Prüfung mit echten Daten (12.10.2026, mit Gewässerabzug)

- Stadtweit 3,0 % der Landfläche ab 25 cm (605,7 ha von 20.515,6 ha Land), 10,4 % ab 5 cm. Gewässer im Stadtgebiet: 511,4 ha.
- Abgezogen wurden 124,1 ha der Flächen ab 25 cm, genau der Wert des Abgleichs vom 10.10.2026 (unten); Heisingen 17,3 ha, Kettwig 27,9 ha, Werden 18,0 ha ebenfalls gleich.
- Am stärksten betroffen (ab 25 cm, an Land): Werden 8,5 %, Rellinghausen 5,8 %, Steele 4,5 %, Dellwig 4,4 %, Frintrop 4,3 %. Am wenigsten: Schuir 1,6 %, Huttrop und Haarzopf je 1,8 %. Heisingen fällt von 4,7 auf 2,4 %, Kettwig von 4,5 auf 2,8 %.
- Mehrfachbelastung (E-008): weiter 8 Stadtteile mit mindestens zwei Themen. Im obersten Fünftel beim Starkregen sind jetzt Altenessen-Nord, Stoppenberg und Katernberg statt Heisingen, Kettwig, Burgaltendorf und Borbeck-Mitte.
- Rechenzeit etwa 2 Minuten (Lesen der Gewässer aus dem 7-GB-GeoPackage).

## Prüfung mit echten Daten (10.10.2026, vor E-017)

- Stadtweit 3,5 % der Fläche ab 25 cm, 12,3 % ab 5 cm.
- Unabhängige Gegenrechnung (Klasse 3 vereinigt und mit dem ganzen Stadtgebiet geschnitten, ohne Stadtteile): 729,5 ha = 3,47 %.
- Am stärksten betroffen (ab 25 cm): Werden 12,1 %, Rellinghausen 8,0 %, Heisingen 4,7 %, Kettwig 4,5 %, Steele 4,5 %. Am wenigsten: Schuir 1,7 %, Huttrop und Haarzopf je 1,8 %.
- **Gewässer:** Abgleich mit der Landbedeckung (Layer `lb_binnengewaesser`): 124 der 730 ha ab 25 cm liegen in Gewässern (17 %). In Heisingen sind es 17,3 von 32,0 ha, in Kettwig 27,9 von 69,3 ha, in Werden 18,0 von 49,5 ha. Bei den Stadtteilen an der Ruhr ist der Wert also zu einem großen Teil Wasser in Ruhr, Baldeneysee und Bächen. Umgekehrt sind von 511 ha Gewässern nur 124 ha als tief eingestuft.
- Zusammenhang mit anderen Themen über die 50 Stadtteile: Korrelation mit Versiegelung −0,16, Grünanteil 0,08, Lärm −0,17, Hitze in der Nacht −0,10. Starkregen misst also etwas weitgehend Eigenes.
- Rechenzeit etwa 40 Sekunden (vorher über 20 Minuten mit Klasse 1).
- Einwohner (Zensus-Gitter, optional, 11.10.2026): geschätzt 13.600 von 570.632 (2,4 %) wohnen anteilig in Flächen ab 25 cm Einstau. Verfahren nach E-013.

## Grenzen

- Modell ohne Kanalisation: Für häufige, kleinere Regen überschätzt die Karte den Einstau; für das seltene Extremereignis ist das gewollt.
- Kein Flusshochwasser (Ruhr, Emscher), nur Oberflächenabfluss.
- Gewässer sind abgezogen, soweit die Landbedeckung sie als Binnengewässer führt; schmale Gräben unterhalb ihrer Auflösung bleiben drin.
- Stand 2022; Baumaßnahmen seitdem sind nicht berücksichtigt.
- Bezug ist die Fläche, nicht die Zahl der Betroffenen (E-007).

## Ergebnis

`data/processed/starkregen/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/starkregen.html`.
