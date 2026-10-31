# Grünanteil je Stadtteil

**Frage:** Welcher Anteil der Fläche eines Stadtteils ist mit Vegetation bedeckt, und wie viel davon mit Bäumen?

**Code:** `src/essen/analysen/gruenanteil.py` · **Aufruf:** `uv run essen analyse gruenanteil`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `landbedeckung-nrw` | Landbedeckung NRW (Geobasis NRW), GeoPackage für den Regierungsbezirk Düsseldorf |

## Rechenweg

1. Die Landbedeckung teilt NRW lückenlos und überschneidungsfrei in Flächen ein, eine Klasse je Fläche. Grundlage sind Sentinel-2-Satellitenbilder (2023), Luftbilder, Höhenmodelle und Geobasisdaten. Das GeoPackage hat einen Layer je Hauptklasse (`lb_hochbau`, `lb_tiefbau`, `lb_krautigevegetation`, `lb_holzigevegetation`, `lb_lockermaterial`, `lb_binnengewaesser`); die Unterklassen stehen als Codes in `vegetationsmerkmal`, `blattform` und `fliesseigenschaft`.
2. Welcher Layer und Code zu welcher Gruppe gehört, steht in `katalog/zuordnungen/landbedeckung-nrw.yaml`. Die Bedeutung der Codes ist den mitgelieferten QGIS-Stildateien entnommen und mit der Legende des WMS abgeglichen (10.10.2026). Kommt ein Code ohne Zuordnung vor, bricht die Analyse ab.

   | Gruppe | Layer und Code | grün |
   | --- | --- | --- |
   | Bäume | holzige Vegetation 4000 (Laub und Nadel) | ja |
   | Gehölz, Büsche, Sträucher | holzige Vegetation 5000, 6000 | ja |
   | Gras | krautige Vegetation 1000 | ja |
   | Getreide, Stauden, Röhricht | krautige Vegetation 2000, 3000 | ja |
   | Hochbau, Tiefbau, Lockermaterial, Wasser | eigene Layer | nein |

3. Nur Flächen im Rechteck um Essen werden gelesen und dann mit den Stadtteilen verschnitten (EPSG:25832).
4. Je Stadtteil: erfasste Fläche, Fläche mit Vegetation und mit Bäumen, Anteil jeder Gruppe, Abdeckung (erfasste Fläche geteilt durch die Fläche des Stadtteils). Unter 99 % oder über 101 % Abdeckung nennt das Ergebnis den Stadtteil.
5. Unter 5 ha erfasster Fläche bleibt der Anteil leer (Parameter `min_flaeche_ha`).
6. Der stadtweite Wert ist das flächengewichtete Mittel der Stadtteile.

## Prüfung mit echten Daten (10.10.2026)

- Stadtweit 63,7 % Vegetation, 27,4 % Bäume. Eine unabhängige Rechnung (Layer einzeln mit dem Stadtgebiet geschnitten) ergibt dieselben Flächen: 13.400 ha Vegetation, 5.762 ha Bäume.
- Abdeckung je Stadtteil 99,9 bis 100 %; insgesamt 21.024 von 21.027 ha.
- Abgleich mit `versiegelung` (andere Quelle, Luftbilder 0,5 m): Der Anteil Hochbau plus Tiefbau korreliert über die 50 Stadtteile mit 0,988 mit dem versiegelten Anteil.
- Am grünsten: Schuir (89,5 %), Byfang (89,1 %), Heidhausen (88,2 %). Am wenigsten grün: Stadtkern (5,3 %), Südviertel (22,9 %), Ostviertel (25,1 %).
- Rechenzeit etwa eine Minute.

## Grenzen

- Vegetation ist nicht gleich öffentliches Grün: Äcker, private Gärten, Friedhöfe und Bahnböschungen zählen mit.
- Auflösung: Die Satellitenbilder haben 10 m. Einzelne Straßenbäume, Vorgärten und schmale Grünstreifen sind nur teilweise erfasst.
- Stand der Bilder 2022 bis 2023 je nach Kachel (`aktualitaetsstand`).
- Bezug ist die Fläche, nicht die Bevölkerung (E-007).
- Bei Weitergabe den Pflichtvermerk nennen: „Enthält modifizierte Copernicus Sentinel-2 Daten [2023], verarbeitet durch Geobasis NRW; dl-de/by-2-0 (www.govdata.de/dl-de/by-2-0); https://www.wms.nrw.de/geobasis/wms_nw_landbedeckung“.

## Ergebnis

`data/processed/gruenanteil/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/gruenanteil.html`.
