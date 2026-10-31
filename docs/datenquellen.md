# Datenquellen für Essen

Diese Seite wird aus `katalog/` erzeugt: `uv run essen katalog --doku`. Änderungen bitte im Katalog machen.

Stand: 12.10.2026 · 39 Quellen · 53 Datensätze, davon 43 automatisch ladbar.

## Datensätze nach Thema

Status: **geprüft** = Adresse bestätigt, **ungeprüft** = eingetragen, aber noch nicht bestätigt, **manuell** = von Hand laden und mit `essen einlesen` übernehmen, **Dienst** = nur Kartendienst.

### Klima und Hitze

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Klimaanalyse NRW 2026 – Klimaanalysekarte Nacht (Raster)](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/analyse-nacht/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | GeoTIFF im ZIP, 363,5 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-nacht-raster` |
| [Klimaanalyse NRW 2026 – Nachtsituation (GeoPackage)](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/analyse-nacht/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | GeoPackage im ZIP, 62,6 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-nacht-vektor` |
| [Klimaanalyse NRW 2026 – Datenbeschreibung](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/analyse-nacht/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | ZIP, 13,2 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-beschreibung` |
| [Klimaanalyse NRW 2026 – Tagsituation](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/analyse-tag/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | GeoPackage im ZIP, 32,5 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-tag` |
| [Klimaanalyse NRW 2026 – Klimaanalysekarte Tag (Raster)](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/analyse-tag/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | GeoTIFF im ZIP, 246 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-tag-raster` |
| [Klimaanalyse NRW 2026 – Klimatopkarte](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/klimatop/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | GeoPackage im ZIP, 541 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-klimatope` |
| [Klimaanalyse NRW 2026 – Planungshinweiskarte](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/planunghinweis/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | GeoPackage im ZIP, dazu ein kleines TIFF, 604,9 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-planungshinweise` |
| [Klimaanalyse NRW 2026 – Betroffenheitsanalyse](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/betroffenheit/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | GeoPackage im ZIP, 2968,5 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-betroffenheit` |
| [Klimaanalyse NRW 2026 – Regionalkarte](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/klimaanalyse/regionalkarte/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | GeoPackage im ZIP, 25,7 MB | DL-DE Zero 2.0 | geprüft | `essen laden klimaanalyse-regionalkarte` |
| [Klimaanalyse Metropole Ruhr – Synthetische Klimafunktionskarte](https://geodaten.metropoleruhr.de/klima/synth_klima_fk_v8) | Regionalverband Ruhr (RVR) | WFS | CC BY-NC 4.0 | manuell | von Hand |
| [DWD Tageswerte, Station Essen-Bredeney (aktuell)](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/recent/) | Deutscher Wetterdienst (DWD) | Text (Semikolon) im ZIP | CC BY 4.0 | geprüft | `essen laden dwd-klima-essen-aktuell` |
| [DWD Tageswerte, Station Essen-Bredeney (historisch)](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/historical/) | Deutscher Wetterdienst (DWD) | Text (Semikolon) im ZIP | CC BY 4.0 | geprüft | `essen laden dwd-klima-essen-historisch` |
| [DWD Stationsliste Tageswerte Klima](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/recent/) | Deutscher Wetterdienst (DWD) | Text | CC BY 4.0 | geprüft | `essen laden dwd-stationen-kl` |
| [DWD Jahresraster heiße Tage (1 km)](https://opendata.dwd.de/climate_environment/CDC/grids_germany/annual/hot_days/) | Deutscher Wetterdienst (DWD) | ESRI-ASCII-Gitter (gzip), 9 MB | CC BY 4.0 | geprüft | `essen laden dwd-raster-heisse-tage` |
| [DWD Jahresraster Sommertage (1 km)](https://opendata.dwd.de/climate_environment/CDC/grids_germany/annual/summer_days/) | Deutscher Wetterdienst (DWD) | ESRI-ASCII-Gitter (gzip), 12 MB | CC BY 4.0 | geprüft | `essen laden dwd-raster-sommertage` |
| [DWD Jahresraster Lufttemperatur, Jahresmittel (1 km)](https://opendata.dwd.de/climate_environment/CDC/grids_germany/annual/air_temperature_mean/) | Deutscher Wetterdienst (DWD) | ESRI-ASCII-Gitter (gzip), 40 MB | CC BY 4.0 | geprüft | `essen laden dwd-raster-jahresmittel` |
| [Kühlorte in Essen](https://opendata.essen.de/dataset/kühle-orte-essen) | Stadt Essen | GeoJSON (WGS84), 0,4 MB | DL-DE BY 2.0 | geprüft | `essen laden kuehlorte` |

### Luft

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Luftqualität NRW, Messwerte der letzten 24 Stunden](https://www.opengeodata.nrw.de/produkte/umwelt_klima/luftqualitaet/luqs/aktuelle_luftqualitaet/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | CSV | DL-DE Zero 2.0 | geprüft | `essen laden luqs-aktuell` |
| [Luftdaten des Umweltbundesamts (Essener Stationen)](https://luftdaten.umweltbundesamt.de/) | Umweltbundesamt | JSON über REST-API | DL-DE BY 2.0 | geprüft | `essen laden uba-luftdaten` |
| [Jahresbilanzen der Luftmessstationen (UBA)](https://luftdaten.umweltbundesamt.de/) | Umweltbundesamt | JSON über REST-API, 0,9 MB | DL-DE BY 2.0 | geprüft | `essen laden uba-jahresbilanzen` |
| [Umweltzone Essen](https://opendata.essen.de/dataset/umweltzone-essen) | Stadt Essen | GeoJSON (WGS84), Shape, 0,3 MB | DL-DE BY 2.0 | geprüft | `essen laden umweltzone` |
| [Feinstaubsensoren von Bürgerinnen und Bürgern (Sensor.Community)](https://sensor.community/) | Sensor.Community | JSON | ODbL 1.0 | geprüft | `essen laden sensor-community-essen` |

### Lärm

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Lärmkarte Essen (Umgebungslärm)](https://opendata.essen.de/dataset/lärmkarte-essen) | Stadt Essen, FB 59 Umweltamt und FB 62 Amt für Geoinformation, Vermessung und Kataster | Shape im ZIP (EPSG:4647), teils auch GeoJSON (WGS84), 31 MB | DL-DE BY 2.0 | geprüft | `essen laden laermkarte-essen` |
| [Umgebungslärmkartierung NRW, Runde 4](https://www.opengeodata.nrw.de/produkte/umwelt_klima/laerm/umgebungslaerm2022/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | ASCII-Grid im ZIP (10-m-Raster), dazu Shape; WMS, 103,9 MB | DL-DE Zero 2.0 | geprüft | `essen laden laermkarten-nrw` |

### Wasser und Starkregen

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Hinweiskarte Starkregengefahren](https://gdz.bkg.bund.de/index.php/default/wms-hinweiskarte-starkregengefahren-wms-starkregen.html) | Bundesamt für Kartographie und Geodäsie (BKG) | WMS; Download als GeoTIFF-Kacheln | DL-DE BY 2.0 | Dienst | von Hand |
| [Starkregengefahrenkarte Essen](https://opendata.essen.de/dataset/starkregenkarte) | Stadt Essen | ZIP (Geodaten in EPSG:4647), 31,7 MB | DL-DE BY 2.0 | geprüft | `essen laden starkregen-essen` |
| [Pegel an Bundeswasserstraßen im Umkreis von Essen](https://pegelonline.wsv.de/webservice/dokuRestapi) | Wasserstraßen- und Schifffahrtsverwaltung des Bundes | JSON | DL-DE Zero 2.0 | geprüft | `essen laden pegel-essen` |
| [Hydrologische Rohdaten NRW (HYGON)](https://www.opengeodata.nrw.de/produkte/umwelt_klima/wasser/oberflaechengewaesser/hygon/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | CSV im ZIP (ganz NRW), Stationslisten als Text und Shape, 1 MB | DL-DE Zero 2.0 | geprüft | `essen laden hygon` |

### Grün, Natur und Boden

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Landbedeckung NRW](https://www.opengeodata.nrw.de/produkte/geobasis/lusat/akt/lb_nrw/) | Land NRW, Geobasis NRW | GeoPackage, 849,5 MB | DL-DE BY 2.0 | geprüft | `essen laden landbedeckung-nrw` |
| [Bodenversiegelung NRW](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/boden/bodenversiegelung/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK), Projekt EBOVE | GeoTIFF im ZIP (Ausschnitt je Kreis oder kreisfreie Stadt), 24,9 MB | DL-DE Zero 2.0 | geprüft | `essen laden bodenversiegelung-nrw` |
| [Bodenversiegelung NRW, satellitenbasiert 2006 bis 2018](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/boden/bodenversiegelung/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK), Projekt EBOVE | GeoTIFF im ZIP (Ausschnitt je Kreis oder kreisfreie Stadt), 10 MB | DL-DE Zero 2.0 | geprüft | `essen laden bodenversiegelung-sat-nrw` |
| [Stadtbäume Essen](https://opendata.essen.de/dataset/stadtbäume) | Stadt Essen, Grün und Gruga | WFS (GML) | DL-DE BY 2.0 | geprüft | `essen laden stadtbaeume` |
| [Naturschutzgebiete NRW](https://www.opengeodata.nrw.de/produkte/umwelt_klima/naturschutz/linfos/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK), LINFOS | Shape im ZIP (ganz NRW), 8,9 MB | DL-DE Zero 2.0 | geprüft | `essen laden naturschutzgebiete-nrw` |
| [Gründachkataster NRW](https://www.opengeodata.nrw.de/produkte/umwelt_klima/klima/gruendachkataster/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | Esri File-Geodatabase im ZIP, Ausschnitt Essen, 138,8 MB | DL-DE Zero 2.0 | geprüft | `essen laden gruendachkataster-nrw` |
| [Grünflächen und Wald aus OpenStreetMap](https://www.openstreetmap.org/) | OpenStreetMap-Mitwirkende | über die Overpass-API | ODbL 1.0 | manuell | von Hand |

### Energie und Klimaschutz

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Marktstammdatenregister, Anlagen in Essen](https://www.marktstammdatenregister.de/) | Bundesnetzagentur | XML-Gesamtexport, SOAP-API | DL-DE BY 2.0 | manuell | von Hand |
| [Solarkataster NRW, Dachflächen](https://www.opengeodata.nrw.de/produkte/umwelt_klima/energie/solarkataster/photovoltaik/) | Landesamt für Natur, Umwelt und Klima NRW (LANUK) | Shape im ZIP, Ausschnitt Essen, 107 MB | DL-DE Zero 2.0 | geprüft | `essen laden solarkataster-nrw` |
| [Öffentliche Ladepunkte (Ladesäulenregister)](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/Ladesaeulenkarte/start.html) | Bundesnetzagentur | CSV (ganz Deutschland), 53 MB | CC BY 4.0 | geprüft | `essen laden ladesaeulen` |
| [Treibhausgasbilanz der Stadt Essen](https://opendata.essen.de/dataset/klimadashboard-essen) | Stadt Essen | CSV (Indikatoren des Klimadashboards), 0,2 MB | DL-DE BY 2.0 | geprüft | `essen laden treibhausgasbilanz` |

### Geobasis, Gebäude und Grenzen

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Stadtteilgrenzen Essen](https://opendata.essen.de/dataset/verwaltungsgrenzen-der-stadt-essen) | Stadt Essen | GeoJSON | DL-DE BY 2.0 | geprüft | `essen laden stadtteile` |
| [Stadtbezirksgrenzen Essen](https://opendata.essen.de/dataset/verwaltungsgrenzen-der-stadt-essen) | Stadt Essen | GeoJSON (WGS84), 3,7 MB | DL-DE BY 2.0 | geprüft | `essen laden stadtbezirke` |
| [Amtliche Hauskoordinaten Essen](https://opendata.essen.de/dataset/amtliche-hauskoordinaten-essen) | Stadt Essen, Amt für Geoinformation, Vermessung und Kataster | WFS (GML, EPSG:25832 auf Anfrage), GeoJSON (WGS84, Stand 01.04.2024) | DL-DE BY 2.0 | geprüft | `essen laden hauskoordinaten` |
| [basemap.de Web Raster grau](https://basemap.de/) | GeoBasis-DE / BKG | Kartenkacheln (WMTS) | CC BY 4.0 | Dienst | – |
| [3D-Gebäudemodelle NRW (LoD1, LoD2)](https://www.bezreg-koeln.nrw.de/geobasis-nrw/produkte-und-dienste/3d-gebaeudemodelle) | Bezirksregierung Köln, Geobasis NRW | OGC API Features, CityGML, 3D Tiles | DL-DE Zero 2.0 | manuell | von Hand |

### Bevölkerung und Soziales

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Zensus 2022, Gitterdaten](https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Zensus2022/_inhalt.html) | Statistische Ämter des Bundes und der Länder | CSV je Merkmal, 18 MB | DL-DE BY 2.0 | geprüft | `essen laden zensus-2022-gitter` |
| [Privathaushalte nach Stadtteilen](https://opendata.essen.de/dataset/privathaushalte-essen) | Stadt Essen, Amt für Statistik | CSV, 0,05 MB | DL-DE BY 2.0 | geprüft | `essen laden privathaushalte-stadtteile` |
| [KomMonitor-Indikatoren](https://www.essen.de/dasistessen/connected_essen_1/connected_essen_kommonitor_1.de.html) | Stadt Essen | Export aus der Webanwendung | prüfen | manuell | von Hand |
| [Landesdatenbank NRW, Tabellen für Essen](https://www.landesdatenbank.nrw.de/) | IT.NRW | CSV, GENESIS-REST | DL-DE BY 2.0 | manuell | von Hand |

### Mobilität

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [VRR-Sollfahrplan (GTFS)](https://www.opendata-oepnv.de/ht/de/organisation/verkehrsverbuende/vrr/openvrr/datensaetze) | Verkehrsverbund Rhein-Ruhr (VRR) | GTFS (ZIP) | widersprüchlich | manuell | von Hand |
| [metropolradruhr-Stationen (GBFS)](https://www.mobilitaetsdaten.nrw/api/ckan/en/dataset/nextbike-nrw) | NRW.Mobidrom | GBFS | prüfen | manuell | von Hand |
| [StadtLastenRad Essen, Stationen (GBFS)](https://www.nextbike.de/stadtlastenrad/de) | nextbike GmbH | GBFS (JSON) | CC0 1.0 | geprüft | `essen laden nextbike-essen` |

### Wahlen und Politik

| Datensatz | Anbieter | Format | Lizenz | Status | Laden |
| --- | --- | --- | --- | --- | --- |
| [Bundestagswahl 2025 in Essen](https://webapps-extern.essen.de/wahlergebnisse/BW2025/05113000/praesentation/opendata.html) | Stadt Essen, Amt für Statistik und Wahlen | CSV (Semikolon), 0,01 MB | prüfen | geprüft | `essen laden wahl-bundestag-2025` |
| [Kommunalwahl 2025 in Essen (amtlich)](https://www.wahlergebnisse.nrw/kommunalwahlen/2025/aktuell/a113000kw2500.shtml) | IT.NRW | Text (Semikolon), 0,01 MB | prüfen | geprüft | `essen laden wahl-kommunal-2025` |

## Quellen nach Ebene

### Stadt Essen

- **[Open-Data-Portal Stadt Essen](https://opendata.essen.de/)** · opendata.essen.de. Zentrales Portal der Stadt, seit 2019 online und laufend gepflegt. Zwölf Themenkategorien, die größten sind Geo, Politik und Wahlen, Infrastruktur und Verkehr.
  Themen: Bevölkerung und Soziales, Wahlen und Politik, Geobasis, Gebäude und Grenzen, Mobilität, Klima und Hitze, Luft, Wasser und Starkregen, Grün, Natur und Boden, Wirtschaft und Arbeit, Verwaltung und Haushalt, Kultur und Freizeit. Lizenz: je Datensatz (DL-DE-Zero-2.0 (überwiegend); Einzelne Datensätze unter DL-DE-BY-2.0, z. B. Verwaltungsgrenzen). Zugang: DKAN-API (CKAN-Stil), Datastore-Abfrage, CSV · GeoJSON · SHP; ohne Konto.
  - Lizenz jeder Ressource im Feld license auslesen und für BY-Daten die Quellenangabe erzeugen.
  - Rate Limits sind nicht dokumentiert. Abrufe zwischenspeichern.
  - Quartalsdateien erscheinen teils verspätet. Vor dem Einbau die neuesten Zeiträume prüfen.
- **[Geodienste der Stadt Essen](https://www.essen.de/dasistessen/geoportal/uebersicht.de.html)** · Geoportal · Amt 62. Karten- und Objektdienste des Amts für Geoinformation, Vermessung und Kataster. Die offenen Dienste sind als Ressourcen im Open-Data-Portal verlinkt.
  Themen: Geobasis, Gebäude und Grenzen, Grün, Natur und Boden, Lärm, Energie und Klimaschutz. Lizenz: DL-DE Zero 2.0 (meist DL-DE-Zero-2.0; Angabe je Datensatz prüfen). Zugang: WMS, WFS, GeoJSON (WGS84); ohne Konto.
  - Die Dienst-URLs stehen in den Ressourcen der jeweiligen Datensätze auf opendata.essen.de.
  - Für Webkarten das GeoJSON in WGS84 nehmen. Das Koordinatensystem des Hauskoordinaten-WFS macht in QGIS und R Probleme.
  - Das Geoportal A–Z zeigt viele weitere Fachkarten (Baustellen, Lärm, Solardachkataster, Stadtbäume, Umweltzonen, Wärmeplanung). Nicht jede hat einen offenen Dienst.
- **[KomMonitor Essen](https://www.essen.de/dasistessen/connected_essen_1/connected_essen_kommonitor_1.de.html)** · kleinräumiges Monitoring. Open-Source-Monitoringsystem mit rund 361 offen freigegebenen Indikatoren (Stand 06.2026) zu Demografie, Sozialstruktur, Wohnen und Umwelt, auf Stadtteil- und Baublockebene mit Zeitreihen.
  Themen: Bevölkerung und Soziales, Grün, Natur und Boden. Lizenz: prüfen (offen freigegebene Indikatoren; Lizenz je Indikator prüfen). Zugang: Webanwendung, Export, REST-API (geschützt); nur auf Anfrage.
  - Inhaltlich die beste Quelle für einen Sozialatlas. Der technische Zugang ist der Engpass.
  - Für einen API-Zugang direkt beim Amt für Geoinformation, Vermessung und Kataster anfragen.
- **[Wahlergebnisse Essen](https://webapps-extern.essen.de/wahlergebnisse/BW2025/05113000/praesentation/opendata.html)** · votemanager · Amt für Statistik. Je Wahl eine Open-Data-Seite mit CSV-Dateien für alle Gebietsebenen bis zum Stimmbezirk, dazu Wahllokale und Straßenzuordnung.
  Themen: Wahlen und Politik. Lizenz: prüfen (offen, Lizenz je Wahl prüfen). Zugang: CSV (Semikolon, UTF-8); ohne Konto.
  - Für Live-Dashboards am Wahlabend geeignet, da die Dateien laufend aktualisiert werden.
  - Wahlbezirks-Shapes (z. B. Kommunalwahl 2025) liegen auf opendata.essen.de.
  - Stadt und IT.NRW runden teils verschieden (SPD Ratswahl 2025: 22,7 % bzw. 22,6 %). Quelle im Dashboard angeben.
- **[Ratsinformationssystem Essen](https://ris.essen.de/)** · ris.essen.de · OParl. SD.NET RIM 4 mit OParl-Schnittstelle. Liefert Sitzungen, Gremien, Vorlagen und Beschlüsse als verlinktes JSON.
  Themen: Wahlen und Politik, Verwaltung und Haushalt. Lizenz: prüfen (öffentliche RIS-Daten, Lizenz nicht ausgewiesen). Zugang: OParl-JSON; ohne Konto.
  - Die exakte Basis-URL über den Menüpunkt „Schnittstelle OParl“ im Browser ablesen. Die Seite sperrt automatisierte Abrufe.
  - Das Community-Tool oparl-cli führt Essen als bekannten Server.

### Metropole Ruhr

- **[Open Data Portal Ruhr](https://opendata.ruhr/)** · opendata.ruhr · RVR. CKAN-Portal des Regionalverbands Ruhr mit 3.133 Datensätzen, davon 111 der Stadt Essen. Spiegelt die Essener Daten und erlaubt Vergleiche zwischen Ruhrgebietsstädten über eine einzige API.
  Themen: Bevölkerung und Soziales, Geobasis, Gebäude und Grenzen, Mobilität, Klima und Hitze, Grün, Natur und Boden, Wahlen und Politik. Lizenz: je Datensatz (je Datensatz). Zugang: CKAN-API, DCAT (TTL, JSON-LD); ohne Konto.
  - Ideal, wenn das Dashboard Essen mit Bochum, Duisburg oder Dortmund vergleichen soll.
  - Die Klimaanalysekarten des RVR (WFS geodaten.metropoleruhr.de) stehen unter CC BY-NC 4.0, also nicht kommerziell.

### Land NRW

- **[Open.NRW](https://open.nrw/)** · Landeskatalog NRW. Zentraler CKAN-Katalog des Landes mit LANUK-Daten, Geobasisdaten, kommunalen Datensätzen und dem landesweiten ÖPNV-Sollfahrplan (GTFS, monatlich).
  Themen: Geobasis, Gebäude und Grenzen, Klima und Hitze, Luft, Lärm, Wasser und Starkregen, Grün, Natur und Boden, Mobilität, Verwaltung und Haushalt. Lizenz: DL-DE Zero 2.0 (meist DL-DE-Zero-2.0; Angabe je Datensatz prüfen). Zugang: CKAN-API; ohne Konto.
  - Gut als Suchindex. Für Abrufe meist direkt beim Originalanbieter bleiben.
- **[Geobasis NRW](https://www.bezreg-koeln.nrw.de/geobasis-nrw/produkte-und-dienste/3d-gebaeudemodelle)** · Bezirksregierung Köln · GEOportal.NRW. Amtliche Geobasisdaten für ganz NRW: ALKIS, Orthophotos, Höhenmodelle, topografische Karten und 3D-Gebäudemodelle in LoD1 und LoD2.
  Themen: Geobasis, Gebäude und Grenzen, Energie und Klimaschutz. Lizenz: DL-DE Zero 2.0 (DL-DE-Zero-2.0; Jede Nutzung ohne Bedingungen zulässig). Zugang: OGC API Features, WMS/WFS, I3S · 3D Tiles, Download; ohne Konto.
  - LoD2-Grundlage ist der Laserscan-Stand 2019 bis 2024.
  - Gut für 3D-Stadtansichten, Gebäudebestand und Solarpotenzial.
- **[Landesdatenbank NRW](https://www.landesdatenbank.nrw.de/)** · IT.NRW · GENESIS. Amtliche Statistik auf Gemeindeebene für Essen (AGS 05113000): Bevölkerung, Bautätigkeit, Gewerbe, Tourismus und Finanzen.
  Themen: Bevölkerung und Soziales, Wirtschaft und Arbeit, Verwaltung und Haushalt. Lizenz: DL-DE BY 2.0 (DL-DE-BY-2.0). Zugang: GENESIS-REST, CSV-Tabellen; kostenlose Registrierung.
  - Außer whoami brauchen alle Anfragen eine Anmeldung. Request-Limits laut Doku Kap. 1.7.
  - Das R-Paket restatis (CorrelAid) spricht Landesdatenbank NRW, Destatis, Regionalstatistik und Zensus 2022 an.
- **[wahlergebnisse.nrw](https://www.wahlergebnisse.nrw/kommunalwahlen/2025/aktuell/a113000kw2500.shtml)** · IT.NRW. Amtliche Ergebnisse der Kommunal- und Landtagswahlen, darunter die Kommunalwahl 2025 für die kreisfreie Stadt Essen.
  Themen: Wahlen und Politik. Lizenz: prüfen (amtlich, Lizenz nicht ausgewiesen). Zugang: HTML-Tabellen, Downloads; ohne Konto.
  - Gut als amtlicher Abgleich für die städtischen CSV-Daten.
- **[LANUK – Landesamt für Natur, Umwelt und Klima NRW](https://www.opengeodata.nrw.de/produkte/umwelt_klima/luftqualitaet/luqs/aktuelle_luftqualitaet/index.html)** · vormals LANUV · Klima, Luft, Lärm, Wasser, Boden. Landesumweltamt NRW. Veröffentlicht die Klimaanalyse NRW, das Luftqualitätsmessnetz (LUQS mit 52 Stationen im Basismessnetz und rund 100 weiteren Messstellen), die Umgebungslärmkartierung, hydrologische Daten und Bodendaten. Downloads über OpenGeodata.NRW, Karten über wms.nrw.de.
  Themen: Klima und Hitze, Luft, Lärm, Wasser und Starkregen, Grün, Natur und Boden. Lizenz: DL-DE Zero 2.0 (DL-DE-Zero-2.0 für die Downloads auf OpenGeodata.NRW; einzelne Fachdaten (z. B. Solarkataster) prüfen). Zugang: Downloads (OpenGeodata.NRW), WMS (wms.nrw.de), CSV (Luftqualität, letzte 24 h); ohne Konto.
  - Die Werte sind vorläufig und nicht validiert. Im Dashboard so kennzeichnen.
  - Die Datei OpenKontiLUQS_aktuelle-messwerte-24h.csv war bei der Prüfung im Oktober 2026 seit dem 21.08.2026 nicht aktualisiert.
- **[mobilitaetsdaten.nrw](https://www.mobilitaetsdaten.nrw/api/ckan/en/dataset/nextbike-nrw)** · NRW.Mobidrom. Landesplattform für Mobilitätsdaten. Bündelt die GBFS-Feeds von nextbike NRW, darunter metropolradruhr mit Stationen in Essen.
  Themen: Mobilität. Lizenz: prüfen (siehe Datensatzseite). Zugang: GBFS 2.3 / 3.0, DATEX II Parken (Profil); öffentlich genannter Schlüssel.
  - Client Credentials: Client-ID gbfs-api, Token-URL und Secret stehen auf der Datensatzseite.
  - Ob Essener Parkhäuser über das DATEX-II-Parkprofil liefern, ist nicht geprüft.
- **[BORIS.NRW](https://www.boris.nrw.de/)**. Bodenrichtwerte
  Themen: Wirtschaft und Arbeit, Geobasis, Gebäude und Grenzen. Lizenz: prüfen (Lizenz prüfen). Zugang: Webdienste, Download; unklar.
  - Lizenz prüfen
- **PKS NRW**. Polizeiliche Kriminalstatistik
  Themen: Verwaltung und Haushalt. Lizenz: prüfen (Bezugsebene prüfen). Zugang: Berichte, Tabellen; unklar.
  - Bezugsebene prüfen
  - Primärquelle noch nicht ermittelt.
- **[OpenGeodata.NRW](https://www.opengeodata.nrw.de/produkte/)** · Download-Plattform des Landes NRW. Dateiserver für die offenen Geodaten des Landes, unter anderem Geobasis NRW und LANUK. Jeder Ordner hat eine Datei index.json mit Dateinamen, Größen und Zeitstempeln.
  Themen: Geobasis, Gebäude und Grenzen, Klima und Hitze, Luft, Lärm, Wasser und Starkregen, Grün, Natur und Boden. Lizenz: je Datensatz (meist DL-DE-Zero-2.0, Geobasis teils DL-DE-BY-2.0; je Produkt prüfen). Zugang: Dateien (HTTPS), index.json je Ordner; ohne Konto.
  - Das Projekt löst Dateinamen über index.json auf, damit neue Dateistände automatisch gefunden werden.

### Bund

- **[UBA Luftdaten-API](https://luftdaten.umweltbundesamt.de/)** · Umweltbundesamt. Messwerte, Luftqualitätsindex, Prognosen und Jahresbilanzen aller deutschen Messstationen, darunter die Essener Stationen mit dem Präfix DENW.
  Themen: Luft. Lizenz: DL-DE BY 2.0 (DL-DE-BY-2.0; Quellenangabe nach UBA-Vorgabe). Zugang: REST v4 (v3 parallel), JSON · CSV; ohne Konto.
  - Daten ab 2016. Werte des laufenden Jahres sind ungeprüft, finale Daten folgen im Juni des Folgejahres.
  - Die Stationscodes für Essen über den stations-Endpunkt ermitteln.
- **[Pegelonline](https://pegelonline.wsv.de/webservice/dokuRestapi)** · Wasserstraßen- und Schifffahrtsverwaltung. Wasserstände und Abflüsse an Bundeswasserstraßen mit Zeitreihen der letzten 30 Tage.
  Themen: Wasser und Starkregen. Lizenz: DL-DE Zero 2.0 (DL-DE-Zero-2.0). Zugang: REST v2 JSON/CSV, WMS/WFS; ohne Konto.
  - Deckt nur Bundeswasserstraßen ab. Die Ruhrpegel im Stadtgebiet betreiben überwiegend Land und Ruhrverband. Per Umkreisabfrage prüfen, was enthalten ist.
- **[Destatis GENESIS-Online](https://www.destatis.de/DE/Service/OpenData/genesis-api-webservice-oberflaeche.html)** · Statistisches Bundesamt. Bundesstatistik. Die Weboberfläche ist ohne Registrierung nutzbar, die REST-Schnittstelle braucht Login oder Token (Doku 5.1 vom 01.06.2026).
  Themen: Bevölkerung und Soziales, Wirtschaft und Arbeit. Lizenz: DL-DE BY 2.0 (DL-DE-BY-2.0). Zugang: GENESIS-REST (JSON); kostenlose Registrierung.
  - Für Essen-spezifische Werte meist die Landesdatenbank NRW oder Regionalstatistik nutzen.
- **[Statistik der Bundesagentur für Arbeit](https://statistik.arbeitsagentur.de/DE/Statischer-Content/Service/API/API-BST.html)** · BA-Statistik. Arbeitsmarktdaten für die kreisfreie Stadt Essen. Seit Dezember 2025 auch per Schnittstelle, zum Beispiel die Eckwerte Beschäftigung.
  Themen: Wirtschaft und Arbeit. Lizenz: prüfen (Nutzungsbedingungen der BA). Zugang: Eckwerte-API, Tabellen; unklar.
  - Kleinräumige Daten nach Stadtteilen gibt es nur für Kommunen, auf Vertragsbasis und kostenpflichtig. Die Essener Stadtstatistik bezieht sie; aggregierte Werte dort anfragen.
  - Die inoffiziell dokumentierte Jobsuche-API ist für den Produktivbetrieb nicht zu empfehlen.
- **[Marktstammdatenregister](https://www.marktstammdatenregister.de/)** · Bundesnetzagentur. Register aller Strom- und Gaserzeugungsanlagen und Speicher mit Standort. Zeigt etwa den PV-Zubau, Batteriespeicher und BHKW in Essen.
  Themen: Energie und Klimaschutz. Lizenz: DL-DE BY 2.0 (DL-DE-BY-2.0; Pflichtangabe: Marktstammdatenregister, © Bundesnetzagentur, dl-de/by-2-0). Zugang: täglicher Gesamtexport (XML), SOAP-API; kostenlose Registrierung.
  - Bis zu 100.000 Webdienst-Aufrufe pro Tag für registrierte Nutzer.
  - Das Python-Paket open-mastr lädt den Gesamtexport in eine Datenbank. Danach nach Gemeindeschlüssel filtern.
- **[GovData.de](https://www.govdata.de/)**. Bundesweiter Datenkatalog
  Themen: Verwaltung und Haushalt, Geobasis, Gebäude und Grenzen. Lizenz: je Datensatz (Lizenz je Datensatz). Zugang: CKAN-API; unklar.
  - Lizenz je Datensatz
- **[Regionalstatistik.de](https://www.regionalstatistik.de/)**. Regionaldatenbank für Kreise und Gemeinden
  Themen: Bevölkerung und Soziales, Wirtschaft und Arbeit. Lizenz: DL-DE BY 2.0 (Registrierung für API). Zugang: GENESIS, R-Paket restatis; unklar.
  - Registrierung für API
- **[Bundesamt für Kartographie und Geodäsie](https://basemap.de/)** · BKG · basemap.de · Geodatenzentrum. Hintergrundkarten (basemap.de), Verwaltungsgebiete und Fachdienste wie die Hinweiskarte Starkregengefahren.
  Themen: Geobasis, Gebäude und Grenzen, Wasser und Starkregen. Lizenz: je Datensatz (basemap.de unter CC BY 4.0 („© GeoBasis-DE / BKG (Jahr) CC BY 4.0“); Starkregen-Hinweiskarte unter DL-DE-BY-2.0 („© BKG (Jahr des letzten Datenbezugs) dl-de/by-2-0“)). Zugang: WMTS, WMS, Downloads; ohne Konto.
- **[Zensus 2022](https://ergebnisse.zensus2022.de/)**. Zensusergebnisse, auch als Gitterdaten
  Themen: Bevölkerung und Soziales. Lizenz: DL-DE BY 2.0 (Gitter erlaubt kleinräumige Karten). Zugang: GENESIS, R-Paket restatis; unklar.
  - Gitterdaten (100 m) unter DL-DE-BY-2.0.
  - Ob es auf dem 100-m-Gitter einen Anteil der Menschen ab 65 Jahren gibt, ist ungeprüft.
- **[Deutscher Wetterdienst – Open Data (Climate Data Center)](https://opendata.dwd.de/)** · opendata.dwd.de. Mess- und Klimadaten des DWD als Dateien, darunter die Station Essen-Bredeney mit Tageswerten seit dem 19. Jahrhundert.
  Themen: Klima und Hitze. Lizenz: CC BY 4.0 (CC BY 4.0, Quellenangabe Deutscher Wetterdienst). Zugang: Dateiserver; ohne Konto.
  - Rohdaten als Text im ZIP; Fehlwerte sind mit -999 markiert.
  - Die Stations-ID von Essen-Bredeney (01303) in der Stationsliste bestätigen.
- **[Autobahn-API](https://autobahn.api.bund.dev/)**. Baustellen und Sperrungen auf A40 und A52
  Themen: Mobilität. Lizenz: prüfen (inoffiziell dokumentiert). Zugang: REST; unklar.
  - inoffiziell dokumentiert
- **[DB API Marketplace](https://developers.deutschebahn.com/)**. Stationen und Fahrpläne der Bahn
  Themen: Mobilität. Lizenz: Anbieterbedingungen (Registrierung). Zugang: REST; unklar.
  - Registrierung
- **Ladesäulenregister**. Öffentliche Ladepunkte (Bundesnetzagentur)
  Themen: Energie und Klimaschutz, Mobilität. Lizenz: prüfen (Quelle bei der Bundesnetzagentur suchen). Zugang: Download; unklar.
  - Quelle bei der Bundesnetzagentur suchen
  - Primärquelle noch nicht ermittelt.
- **Krankenhausverzeichnis**. Krankenhäuser mit Fachabteilungen
  Themen: Bevölkerung und Soziales. Lizenz: prüfen (Quelle prüfen). Zugang: Download; unklar.
  - Quelle prüfen
  - Primärquelle noch nicht ermittelt.

### Verkehrsverbund und Betreiber

- **[VRR-Sollfahrplan (GTFS)](https://www.opendata-oepnv.de/ht/de/organisation/verkehrsverbuende/vrr/openvrr/datensaetze)** · OpenVRR · inkl. Ruhrbahn. Verbundweiter Fahrplan als GTFS, ein monatliches Abbild im Beta-Status. Enthält Linien, Haltestellen und Takt der Ruhrbahn.
  Themen: Mobilität. Lizenz: widersprüchlich (CC-BY laut VRR, „geschlossen“ laut Open.NRW). Zugang: GTFS-ZIP; ohne Konto.
  - Vor kommerzieller Nutzung die Lizenz beim VRR schriftlich bestätigen lassen.
  - Auch über opendata.ruhr verfügbar (CKAN-ID 496eea5d-d6ef-4dc2-aeb0-d15c4fbf3178).
- **[VRR-OpenService](https://www.opendata-oepnv.de/ht/de/api)** · EFA · TRIAS. Abfahrtsmonitor, Verbindungsauskunft und Störungsmeldungen mit Echtzeitdaten für das gesamte VRR-Gebiet. Derzeit die einzige offene Live-Quelle mit voller Abdeckung.
  Themen: Mobilität. Lizenz: prüfen (Nutzungsvereinbarung API). Zugang: EFA rapidJSON/XML, TRIAS; ohne Konto für private Nutzung.
  - Für Produktivbetrieb eine Projektbeschreibung an den VRR schicken und die Produktivserver mit Registrierung nutzen.
  - Zugangsdaten dürfen nicht weitergegeben werden. efa.vrr.de ist kein dokumentierter Open-Data-Endpunkt.
- **[VRR Infrastrukturplattform](https://mip.vrr.de/vrr-api/rest/stop/all/infrastructure)** · MIP · Aufzugsstatus. Status von Aufzügen und weiterer Haltestelleninfrastruktur im VRR. Nützlich für Dashboards zur Barrierefreiheit.
  Themen: Mobilität. Lizenz: CC BY 4.0 (CC BY 4.0). Zugang: REST (JSON); öffentlich genannter Schlüssel.
  - Den öffentlichen API-Key aus der Dokumentation des VRR übernehmen.
- **[nextbike Live-API](https://sharedmobility.github.io/Nextbike.html)** · metropolradruhr. Eigene Live-Schnittstelle des Betreibers mit Stationen und verfügbaren Rädern, alternativ GBFS-Feeds je System.
  Themen: Mobilität. Lizenz: prüfen (Bedingungen von nextbike). Zugang: JSON, GBFS; ohne Konto.
  - Die City- bzw. System-ID für Essen ist nicht geprüft.
  - Für den Produktivbetrieb eher das NRW-Bündel auf mobilitaetsdaten.nrw nutzen.

### Community und Drittanbieter

- **[gtfs.de Realtime](https://gtfs.de/en/realtime/)** · Drittanbieter. Deutschlandweiter GTFS-Realtime-Feed mit TripUpdates und ServiceAlerts, alle 10 Sekunden aktualisiert.
  Themen: Mobilität. Lizenz: CC BY-SA 4.0 (CC BY-SA 4.0). Zugang: GTFS-RT (Protobuf); ohne Konto.
  - Beta ohne Verfügbarkeitsgarantie. Im VRR sind die Busse unvollständig.
  - Einen offiziellen offenen GTFS-RT von VRR oder Ruhrbahn gibt es derzeit nicht.
- **[bund.dev](https://bund.dev/)** · Community-Dokumentation. OpenAPI-Beschreibungen und Clients für Schnittstellen von Bundesbehörden, etwa UBA-Luftqualität oder Autobahn-API.
  Themen: Luft, Mobilität, Wirtschaft und Arbeit. Lizenz: prüfen (abhängig von der Ursprungs-API). Zugang: OpenAPI-Specs; ohne Konto.
  - Keine Behörde. Stabilität und Nutzungsrechte hängen an der jeweiligen Ursprungs-API.
- **[Bright Sky](https://brightsky.dev/)**. JSON-API auf Basis der DWD-Daten
  Themen: Klima und Hitze. Lizenz: prüfen (Community-Projekt). Zugang: REST; unklar.
  - Community-Projekt
- **[OpenStreetMap](https://www.openstreetmap.org/)**. Wege, Gebäude, Points of Interest
  Themen: Geobasis, Gebäude und Grenzen, Mobilität, Grün, Natur und Boden. Lizenz: ODbL 1.0 (ODbL; Namensnennung „© OpenStreetMap-Mitwirkende“). Zugang: Overpass, Nominatim; unklar.
  - ODbL, Namensnennung „© OpenStreetMap-Mitwirkende“
- **[Wikidata](https://query.wikidata.org/)**. Stadtteile, Orte, Personen, Bauwerke
  Themen: Geobasis, Gebäude und Grenzen, Kultur und Freizeit. Lizenz: CC0 1.0 (CC0). Zugang: SPARQL; unklar.
  - CC0
- **[Sensor.Community](https://sensor.community/)**. Feinstaubsensoren von Bürgerinnen und Bürgern
  Themen: Luft. Lizenz: ODbL 1.0 (Messqualität schwankt). Zugang: JSON-API; unklar.
  - Messqualität schwankt

## Lücken und offene Fragen

| Art | Thema | Stand | Weg |
| --- | --- | --- | --- |
| fehlt | Parkhausbelegung in Echtzeit | Kein offener Feed für Essen gefunden. Köln und Münster veröffentlichen einen. | Bei der Stadt und den Parkhausbetreibern anfragen. |
| fehlt | Offizieller GTFS-Realtime-Feed | Weder VRR noch Ruhrbahn bieten einen offenen GTFS-RT an. | Live-Abfahrten über den VRR-OpenService abrufen. |
| kostenpflichtig | Arbeitsmarkt nach Stadtteilen | Kleinräumige BA-Daten gibt es nur für Kommunen auf Vertragsbasis. | Aggregierte Werte bei der Essener Stadtstatistik anfragen. |
| geschützt | KomMonitor-API | Die REST-Schnittstelle ist zugriffsgeschützt. | Beim Amt für Geoinformation, Vermessung und Kataster anfragen. |
| ungeprüft | OParl-Basis-URL des Essener RIS | Die Seite sperrt automatisierte Abrufe. | URL über den Menüpunkt „Schnittstelle OParl“ im Browser ablesen. |
| ungeprüft | System-ID von metropolradruhr | Für die nextbike-eigene API nicht bestätigt. | Das NRW-Bündel auf mobilitaetsdaten.nrw nutzen oder die ID in nextbike-live.json suchen. |
| kein Beleg | Ruhrbahn-eigene Daten, EBE-Abfuhrkalender, Mietspiegel- und Haushalts-Rohdaten | Keine Primärquelle gefunden. Das heißt nicht, dass es sie nicht gibt. | Gezielt über „Daten anfragen“ anstoßen. |

## Lizenzen

| Lizenz | Namensnennung | kommerziell | Hinweis |
| --- | --- | --- | --- |
| [DL-DE Zero 2.0](https://www.govdata.de/dl-de/zero-2-0) | nein | ja | Jede Nutzung ohne Bedingungen erlaubt. Eine Quellenangabe ist freiwillig, aber üblich. |
| [DL-DE BY 2.0](https://www.govdata.de/dl-de/by-2-0) | ja | ja | Zu nennen sind der Bereitsteller, der Lizenzname mit Link und ein Verweis auf den Datensatz. Veränderte Daten sind als „Daten geändert“ zu kennzeichnen. |
| [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | ja | ja | Urheber, Lizenz mit Link und Hinweis auf Änderungen nennen. |
| [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | ja | ja | Wie CC BY, abgeleitete Daten müssen zusätzlich unter CC BY-SA stehen. |
| [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) | ja | nein oder unklar | Nur nicht kommerzielle Nutzung. Für ein privates Projekt in Ordnung, vor einer Veröffentlichung mit Werbung oder Bezahlung klären. |
| [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) | ja | ja | Namensnennung (bei OpenStreetMap „© OpenStreetMap-Mitwirkende“). Abgeleitete Datenbanken unter ODbL weitergeben. |
| [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | nein | ja | Gemeinfrei, keine Bedingungen. |
| Anbieterbedingungen | ja | nein oder unklar | Keine offene Lizenz, sondern eigene Bedingungen des Anbieters (z. B. API-Nutzungsvereinbarung). Vor einer Weitergabe lesen. |
| je Datensatz | ja | nein oder unklar | Portal mit verschiedenen Lizenzen. Die Lizenz steht beim einzelnen Datensatz oder in dessen Ressourcen. |
| prüfen | ja | nein oder unklar | Keine Lizenz angegeben oder an Bedingungen gebunden. Privat nutzbar; vor jeder Weitergabe beim Anbieter klären. |
| widersprüchlich | ja | nein oder unklar | Verschiedene Portale nennen verschiedene Lizenzen. Beim Anbieter schriftlich bestätigen lassen. |
