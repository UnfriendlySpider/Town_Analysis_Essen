"""Erfundene Testdaten im Format der echten Dateien.

Für Tests und für Cloud-Sitzungen, in denen die Datenportale gesperrt sind. Die Testdaten
landen in einem eigenen Datenordner (Standard: data_test/) und sind dort mit der Datei
.testdaten markiert. App und Berichte zeigen dann einen deutlichen Hinweis.

Erzeugt werden:
- 50 „Testgebiete“ als Stadtteile (Felder FID, OBJECTID, STADTTEILE, STADTT, STADTBEZ, STAT_NR wie in der echten Datei)
- Klimaanalyse Nacht wie das echte ZIP: Lufttemperatur (LT) und Kaltluftvolumenstromdichte (KVSD) als
  float32-GeoTIFF mit Fehlwert -999, je ein Szenario EXT und TYP, dazu ein Strömungsraster
- Klimaanalyse Tag wie das echte ZIP: PET in °C (PL_KY_TAG_EXT/TYP), flächendeckend
- Versiegelungsmaske wie das echte ZIP für Essen (uint8, 1 = versiegelt, Fehlwert 3), gröber als 0,5 m
- Landbedeckung wie das echte GeoPackage (Layer lb_*, Codes in vegetationsmerkmal, blattform, fliesseigenschaft)
- Klimaanalyse Nacht als GeoPackage mit denselben Layern und Feldern wie das echte (ohne Wirkraumklassen)
- Datenbeschreibung ohne Stildatei (das echte ZIP enthält nur PDFs);
  `klassenraster_mit_legende()` baut für Tests ein Klassenraster mit QGIS-Legende
- DWD-Tageswerte für eine erfundene Station 01303, historisch und aktuell
- DWD-Jahresraster wie die echten (ESRI-ASCII, gzip, EPSG:31467, 1 km, Fehlwert -999) für heiße Tage,
  Sommertage und Jahresmittel in 1/10 °C, aber nur ein Ausschnitt um das Testgebiet; eine Jahresmittel-Datei
  ist wie beim DWD ein ZIP mit der Endung .asc.gz
- Lärmkarte Essen wie die acht echten ZIPs (EPSG:4647): Straßen und DB als verschachtelte Isophonen-Flächen
  (WERT bzw. KLASSE X,01), Ruhrbahn als Bänder (ISOV1/ISOV2), Industrieanlagen als Bänder (WERT)
- Starkregengefahrenkarte wie das echte Starkregen_0.zip (Ueberflutung_Kategorien.shp, EPSG:4647, gridcode 1 bis 3
  mit Textfeld Einstautie), mit Lücken wie beim Original
- Betroffenheitsanalyse wie das echte GeoPackage (Layer _komplett und _HP, senstvt 1 bis 4 mit Textfeld
  Betroffenheit, Feld gemeind), dazu Blöcke einer Nachbargemeinde, die nicht zählen dürfen
- UBA-Jahresbilanzen wie die echten API-Antworten (stationen.json, jahr_JJJJ_no2|pm10|pm25.json mit headers),
  erfundene Stationen „Essen Teststraße“ und eine Station außerhalb
- Zensus-2022-Gitter wie das echte ZIP (Zensus2022_Bevoelkerungszahl_100m-Gitter.csv, EPSG:3035, Semikolon),
  nur Zellen mit Einwohnern
- Punkte und Flächen wie die echten Dateien: Kühle Orte (GeoJSON), Jungbäume (GML, EPSG:25832),
  Ladesäulenregister (CSV mit Vorspann, ganz Deutschland, darunter ein Ort „Essen“ in Berlin), StadtLastenRad
  (GBFS-JSON), Pegel (Pegelonline-JSON), Umweltzone (GeoJSON, drei Flächen, die große mit Loch)

Keine Zahl darin ist echt.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import shutil
import zipfile
from dataclasses import asdict
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from shapely.geometry import MultiPoint, Point, Polygon

from . import pfade
from .laden import ABRUF_DATEI, Abruf

MITTE_X, MITTE_Y = 361500, 5703000  # Mitte des Rechtecks geo.essen_bbox, damit nichts abgeschnitten wird
FEHLWERT = -999.0
RASTER_ZIP = "Klimaanalyse-Karte-Nacht_2026_EPSG25832_TIFF.zip"
TAG_ZIP = "Klimaanalyse-Karte-Tag_2026_EPSG25832_TIFF.zip"
VERSIEGELUNG_ZIP = "bodenversiegelung-lb_Essen_05113000_2024_EPSG25832_TIFF.zip"
VERSIEGELUNG_SAT_ZIP = "bodenversiegelung-sat_Essen_05113000_2006-2018_EPSG25832_TIFF.zip"
GRENZEN_C = [14.0, 15.5, 17.0, 18.5, 20.0, 21.5, 23.0]
WIRKRAUM_LABEL = {
    1: "<= 14 °C sehr niedrige nächtliche Lufttemperaturen",
    2: "> 14 - 15,5 °C niedrige nächtliche Lufttemperaturen",
    3: "> 15,5 - 17 °C keine nächtliche Überwärmung",
    4: "> 17 - 18,5 °C schwache nächtliche Überwärmung",
    5: "> 18,5 - 20 °C mäßige nächtliche Überwärmung",
    6: "> 20 - 21,5 °C starke nächtliche Überwärmung",
    7: "> 21,5 - 23 °C sehr starke nächtliche Überwärmung",
    8: "> 23 °C extreme nächtliche Überwärmung",
}
AUSGLEICH_LABEL = {
    11: "Kaltluftvolumenstromdichte <= 5 m³/(s·m)",
    12: "Kaltluftvolumenstromdichte > 5 - 10 m³/(s·m)",
    13: "Kaltluftvolumenstromdichte > 10 - 20 m³/(s·m)",
    14: "Kaltluftvolumenstromdichte > 20 - 40 m³/(s·m)",
    15: "Kaltluftvolumenstromdichte > 40 m³/(s·m)",
}
FARBEN = {1: (44, 123, 182), 2: (110, 166, 205), 3: (171, 217, 233), 4: (255, 255, 191), 5: (254, 224, 144),
          6: (253, 174, 97), 7: (244, 109, 67), 8: (165, 0, 38),
          11: (237, 248, 233), 12: (199, 233, 192), 13: (161, 217, 155), 14: (116, 196, 118), 15: (49, 163, 84)}


def _umriss() -> Polygon:
    winkel = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    radien = 8200 + 1500 * np.sin(3 * winkel + 0.6) + 900 * np.cos(5 * winkel) + 600 * np.sin(7 * winkel + 1.3)
    return Polygon([(MITTE_X + r * np.cos(w) * 0.85, MITTE_Y + r * np.sin(w) * 1.05) for r, w in zip(radien, winkel, strict=True)])


def _gebiete(umriss: Polygon, anzahl: int, rng) -> list[Polygon]:
    punkte: list[Point] = []
    abstand = 900 if anzahl > 20 else 2500
    versuche = 0
    while len(punkte) < anzahl and versuche < 100_000:
        versuche += 1
        r = abs(rng.normal(0, 4200))
        w = rng.uniform(0, 2 * np.pi)
        p = Point(MITTE_X + r * np.cos(w), MITTE_Y + r * np.sin(w))
        if umriss.buffer(-600).contains(p) and all(p.distance(q) > abstand for q in punkte):
            punkte.append(p)
    zellen = shapely.voronoi_polygons(MultiPoint(punkte), extend_to=umriss.buffer(5000))
    gebiete = [z.intersection(umriss) for z in zellen.geoms]
    gebiete = [g for g in gebiete if not g.is_empty]
    gebiete.sort(key=lambda g: (-round(g.centroid.y, -3), g.centroid.x))
    return gebiete


def _abruf(kennung: str, dateien: list[str], lizenz: str, quelle: str) -> None:
    ordner = pfade.roh(kennung)
    abruf = Abruf(datensatz=kennung, dateien=dateien, url="Testdaten (erfunden)",
                  zeit=dt.datetime.now().isoformat(timespec="seconds"),
                  bytes=sum((ordner / d).stat().st_size for d in dateien), lizenz=lizenz, quelle=quelle,
                  testdaten=True, hinweis="erzeugt mit essen.testdaten")
    (ordner / ABRUF_DATEI).write_text(json.dumps(asdict(abruf), ensure_ascii=False, indent=2), encoding="utf-8")


def erzeuge(ziel: Path | None = None, zellgroesse: float = 25.0, anzahl_gebiete: int = 50, seed: int = 7) -> dict:
    """Schreibt alle Testdaten in den Datenordner `ziel` (Standard: data_test/) und gibt Prüfwerte zurück."""
    import os

    ziel = Path(ziel) if ziel else pfade.projekt() / pfade.TESTDATEN_ORDNER
    alt = os.environ.get("ESSEN_DATEN")
    os.environ["ESSEN_DATEN"] = str(ziel.resolve())
    try:
        if ziel.exists() and not ziel.is_dir():
            raise ValueError(f"{ziel} ist eine Datei, kein Ordner.")
        if ziel.exists() and any(ziel.iterdir()):
            if not (ziel / pfade.TESTDATEN_MARKE).exists():
                raise ValueError(f"{ziel} ist nicht leer und kein Testdaten-Ordner. Nichts gelöscht; "
                                 "bitte einen leeren Ordner oder den Standard data_test/ nehmen.")
            shutil.rmtree(ziel)
        ziel.mkdir(parents=True, exist_ok=True)
        (ziel / pfade.TESTDATEN_MARKE).write_text(
            "Dieser Ordner enthält erfundene Testdaten (essen testdaten). Keine Zahl darin ist echt.\n", encoding="utf-8")
        rng = np.random.default_rng(seed)
        umriss = _umriss()
        from .geo import essen_bbox
        if not shapely.box(*essen_bbox("EPSG:25832")).contains(umriss):
            raise ValueError("Der Umriss der Testdaten ragt über geo.essen_bbox hinaus; Daten würden abgeschnitten.")
        gebiete = _gebiete(umriss, anzahl_gebiete, rng)
        _stadtteile(gebiete)
        erwartet = _klimaanalyse(umriss, gebiete, zellgroesse, rng)
        _beschreibung()
        _dwd(rng)
        _dwd_raster(umriss, rng)
        _laerm(gebiete)
        _starkregen(umriss, gebiete, rng)
        _zensus(umriss, rng)
        _uba_jahresbilanzen(rng)
        _betroffenheit(umriss, gebiete, rng)
        _klimatope(umriss, gebiete, rng)
        _planungshinweise(umriss, gebiete, rng)
        _orte(umriss, rng)
        _haushalte(len(gebiete))
        _erwartet_starkregen(gebiete)
        return {"gebiete": len(gebiete), "erwartet": erwartet, "ordner": ziel}
    finally:
        if alt is None:
            os.environ.pop("ESSEN_DATEN", None)
        else:
            os.environ["ESSEN_DATEN"] = alt


def _stadtteile(gebiete: list[Polygon]) -> None:
    nach_wgs = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)

    def wgs(g):
        g = shapely.segmentize(g, 50)
        return shapely.transform(g, lambda xy: np.column_stack(nach_wgs.transform(xy[:, 0], xy[:, 1])))

    ordner = pfade.roh("stadtteile")
    ordner.mkdir(parents=True)
    gdf = gpd.GeoDataFrame(
        {"FID": list(range(len(gebiete))), "OBJECTID": [i + 1 for i in range(len(gebiete))],
         "STADTTEILE": [f"Testgebiet {i + 1:02d}" for i in range(len(gebiete))],
         "STADTT": [i + 1 for i in range(len(gebiete))], "STADTBEZ": [i % 9 + 1 for i in range(len(gebiete))],
         "STAT_NR": [(i % 9 + 1) * 100 + i + 1 for i in range(len(gebiete))]},
        geometry=[wgs(g) for g in gebiete], crs="EPSG:4326")
    gdf.to_file(ordner / "Stadtteile_WGS84.geojson", driver="GeoJSON")
    _abruf("stadtteile", ["Stadtteile_WGS84.geojson"], "dl-de-by-2.0", "essen-opendata")


def _klimaanalyse(umriss: Polygon, gebiete: list[Polygon], zellgroesse: float, rng) -> pd.DataFrame:
    import rasterio
    from rasterio.transform import from_origin

    minx, miny, maxx, maxy = umriss.buffer(1000).bounds
    minx, miny = np.floor(minx / 100) * 100, np.floor(miny / 100) * 100
    breite = int(np.ceil((maxx - minx) / zellgroesse))
    hoehe = int(np.ceil((maxy - miny) / zellgroesse))
    transform = from_origin(minx, miny + hoehe * zellgroesse, zellgroesse, zellgroesse)
    spalten, zeilen = np.meshgrid(np.arange(breite), np.arange(hoehe))
    cx = minx + (spalten + 0.5) * zellgroesse
    cy = miny + hoehe * zellgroesse - (zeilen + 0.5) * zellgroesse
    mitten = shapely.points(cx.ravel(), cy.ravel())
    innen = shapely.contains(umriss, mitten).reshape(cx.shape)
    d = np.hypot(cx - MITTE_X, (cy - MITTE_Y) * 0.9) / 1000
    baum = shapely.STRtree(gebiete)
    gebiet = np.full(cx.size, -1)
    treffer = baum.query(mitten, predicate="within")
    gebiet[treffer[0]] = treffer[1]
    gebiet = gebiet.reshape(cx.shape)
    rand = sorted(range(len(gebiete)), key=lambda i: -gebiete[i].centroid.distance(Point(MITTE_X, MITTE_Y)))
    ohne_bebauung = {rand[0], rand[3]} if len(gebiete) > 4 else set()
    bebaut_p = np.clip(0.97 - 0.085 * d, 0.12, 0.97)
    gruenzug = np.abs(np.sin((cx - MITTE_X) / 2600.0) + np.cos((cy - MITTE_Y) / 3400.0)) < 0.22
    bebaut = (rng.uniform(size=cx.shape) < bebaut_p) & ~gruenzug & ~np.isin(gebiet, list(ohne_bebauung)) & innen
    temperatur_extrem = (22.6 - 0.8 * d + rng.normal(0, 0.8, cx.shape)).astype("float32")
    temperatur_typisch = (temperatur_extrem - 4.1).astype("float32")  # wie beim LANUK rund 4 K kühler
    kvsd = np.clip(2.5 * d + rng.gamma(1.5, 8.0, cx.shape), 0.4, 80).astype("float32")  # echt: 0,4 bis 76
    wirkraum = bebaut  # innerhalb des Umrisses; Grün- und Freiflächen sind Ausgleichsraum
    ausgleich = innen & ~bebaut

    # Raster als ZIP wie beim LANUK: stetige Werte, float32, Fehlwert -999, je Szenario eine Datei
    def tif(werte: np.ndarray, maske: np.ndarray, baender: int = 1) -> bytes:
        werte = np.where(maske, werte, FEHLWERT).astype("float32")
        puffer = io.BytesIO()
        with rasterio.MemoryFile() as speicher:
            with speicher.open(driver="GTiff", width=werte.shape[1], height=werte.shape[0], count=baender,
                               dtype="float32", crs="EPSG:25832", transform=transform, nodata=FEHLWERT,
                               compress="lzw", tiled=True) as ds:
                for band in range(1, baender + 1):
                    ds.write(werte, band)
            puffer.write(speicher.read())
        return puffer.getvalue()

    ordner = pfade.roh("klimaanalyse-nacht-raster")
    ordner.mkdir(parents=True)
    with zipfile.ZipFile(ordner / RASTER_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("PL_KY_NACHT_LT_EXT.tif", tif(temperatur_extrem, wirkraum))
        zf.writestr("PL_KY_NACHT_LT_TYP.tif", tif(temperatur_typisch, wirkraum))
        # die Kaltluft ist die größte Datei, wie im echten ZIP
        zf.writestr("PL_KY_NACHT_KVSD_EXT.tif", tif(kvsd, ausgleich))
        zf.writestr("PL_KY_NACHT_KVSD_TYP.tif", tif(kvsd * 0.98, ausgleich))
        zf.writestr("PL_KY_NACHT_Stroemungsrichtung_1000m_EXT.tif", tif(np.full(cx.shape, 180.0), innen, baender=2))
    _abruf("klimaanalyse-nacht-raster", [RASTER_ZIP], "dl-de-zero-2.0", "lanuk")

    # Klimaanalysekarte Tag wie beim LANUK: PET in °C, flächendeckend, je Szenario eine Datei
    pet_extrem = (45.5 - 1.3 * d - 6.0 * gruenzug + rng.normal(0, 1.5, cx.shape)).astype("float32")
    pet_typisch = (pet_extrem - 5.0).astype("float32")
    ordner = pfade.roh("klimaanalyse-tag-raster")
    ordner.mkdir(parents=True)
    with zipfile.ZipFile(ordner / TAG_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("PL_KY_TAG_EXT.tif", tif(pet_extrem, innen))
        zf.writestr("PL_KY_TAG_TYP.tif", tif(pet_typisch, innen))
    _abruf("klimaanalyse-tag-raster", [TAG_ZIP], "dl-de-zero-2.0", "lanuk")

    # Bodenversiegelung wie das echte ZIP für Essen: uint8, 1 = versiegelt, 0 = nicht versiegelt, Fehlwert 3
    versiegelt_p = np.clip(0.9 - 0.08 * d, 0.05, 0.9) * np.where(gruenzug, 0.2, 1.0)
    maske = np.where(innen, (rng.uniform(size=cx.shape) < versiegelt_p).astype("uint8"), 3).astype("uint8")
    puffer = io.BytesIO()
    with rasterio.MemoryFile() as speicher:
        with speicher.open(driver="GTiff", width=breite, height=hoehe, count=1, dtype="uint8", crs="EPSG:25832",
                           transform=transform, nodata=3, compress="lzw", tiled=True) as ds:
            ds.write(maske, 1)
        puffer.write(speicher.read())
    ordner = pfade.roh("bodenversiegelung-nrw")
    ordner.mkdir(parents=True)
    with zipfile.ZipFile(ordner / VERSIEGELUNG_ZIP, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("Versiegelungsmaske_2024_Essen.tif", puffer.getvalue())
    _abruf("bodenversiegelung-nrw", [VERSIEGELUNG_ZIP], "dl-de-zero-2.0", "lanuk")

    # Satellitenreihe 2006 bis 2018 wie das echte ZIP: Versiegelungsgrad 0–100 %, je Jahr anders gespeichert
    # (EPSG:3035 bzw. 25832, uint8, float32 mit einzelnen Zellen 254, 2018 int8 mit Fehlwert −128 und 10 m)
    grad = np.clip(100 * versiegelt_p, 0, 100)
    lagen = {"VG_20m_2006_Essen.tif": (0.0, "uint8", None), "VG_20m_2012_Essen.tif": (1.0, "float32", None),
             "VG_20m_2015_Essen.tif": (1.5, "uint8", None), "VG_10m_2018_Essen.tif": (4.0, "int8", -128)}
    ordner = pfade.roh("bodenversiegelung-sat-nrw")
    ordner.mkdir(parents=True)
    with zipfile.ZipFile(ordner / VERSIEGELUNG_SAT_ZIP, "w", zipfile.ZIP_STORED) as zf:
        for name, (zuwachs, typ, fehlwert) in lagen.items():
            werte = np.clip(grad + zuwachs, 0, 100)
            if typ == "float32":
                werte[:3, :3] = 254
            werte = np.where(innen, werte, fehlwert if fehlwert is not None else 0).astype(typ)
            puffer = io.BytesIO()
            with rasterio.MemoryFile() as speicher:
                with speicher.open(driver="GTiff", width=breite, height=hoehe, count=1, dtype=typ, crs="EPSG:25832",
                                   transform=transform, nodata=fehlwert) as ds:
                    ds.write(werte, 1)
                puffer.write(speicher.read())
            zf.writestr(name, puffer.getvalue())
    _abruf("bodenversiegelung-sat-nrw", [VERSIEGELUNG_SAT_ZIP], "dl-de-zero-2.0", "lanuk")

    # Landbedeckung wie das echte GeoPackage: ein Layer je Hauptklasse, Unterklassen als Textcodes
    _landbedeckung(umriss, gebiete, rng)

    # GeoPackage mit den Layern und Feldern des echten Datensatzes (ohne Wirkraumklassen)
    ordner = pfade.roh("klimaanalyse-nacht-vektor")
    ordner.mkdir(parents=True)
    gpkg = ordner / "Klimaanalyse-Nacht_2026_EPSG25832.gpkg"
    crs = "EPSG:25832"
    strassen = [shapely.box(MITTE_X - 7000, MITTE_Y - 60, MITTE_X + 7000, MITTE_Y + 60),
                shapely.box(MITTE_X - 60, MITTE_Y - 8000, MITTE_X + 60, MITTE_Y + 8000)]
    # KT_R02_2: Klimatop-Code, -999 Straßenverkehr, -99 Bahnverkehr, 1 Gewässer
    gpd.GeoDataFrame({"KT_R02_2": [-999.0, -99.0]}, geometry=[s.intersection(umriss) for s in strassen], crs=crs).to_file(
        gpkg, layer="PL_KY_Verkehr", driver="GPKG")
    gpd.GeoDataFrame({"KT_R02_2": [1.0]}, geometry=[Point(MITTE_X + 3000, MITTE_Y - 2000).buffer(400)], crs=crs).to_file(
        gpkg, layer="PL_KY_Wasser", driver="GPKG")
    gpd.GeoDataFrame({"Id": [0]}, geometry=[shapely.LineString([(MITTE_X - 6000, MITTE_Y - 6000, 0), (MITTE_X, MITTE_Y, 0)])],
                     crs=crs).to_file(gpkg, layer="PL_KY_KL_Leitbahn", driver="GPKG")
    gpd.GeoDataFrame({"Id": [0, 0], "Richtung": [45, 90]}, geometry=[Point(MITTE_X, MITTE_Y, 0), Point(MITTE_X + 500, MITTE_Y, 0)],
                     crs=crs).to_file(gpkg, layer="PL_KY_KL_Austausch", driver="GPKG")
    gpd.GeoDataFrame({"Id": [1, 2], "gridcode": [2, 2]},  # gridcode ist im echten Layer überall 2
                     geometry=[umriss.difference(umriss.buffer(-1500)), Point(MITTE_X - 4000, MITTE_Y + 3000).buffer(900)],
                     crs=crs).to_file(gpkg, layer="PL_KY_KL_Produktion", driver="GPKG")
    with zipfile.ZipFile(ordner / "Klimaanalyse-Nacht_2026_EPSG25832_GeoPackage.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(gpkg, arcname=gpkg.name)
    gpkg.unlink()
    _abruf("klimaanalyse-nacht-vektor", ["Klimaanalyse-Nacht_2026_EPSG25832_GeoPackage.zip"], "dl-de-zero-2.0", "lanuk")

    # Prüfwerte: Anteile je Gebiet, unabhängig von der Analyse gezählt (Zellmittelpunkt im Gebiet)
    zeilen = []
    zellflaeche = zellgroesse * zellgroesse
    for nummer in range(len(gebiete)):
        wirk = (gebiet == nummer) & wirkraum
        anzahl = wirk.sum()
        zeilen.append({
            "stadtteil": f"Testgebiet {nummer + 1:02d}",
            "wirkraum_ha": anzahl * zellflaeche / 1e4,
            "anteil_ueber_20c_pct": 100 * (wirk & (temperatur_extrem > 20)).sum() / anzahl if anzahl else np.nan,
            "anteil_ueber_20c_pct_typisch": 100 * (wirk & (temperatur_typisch > 20)).sum() / anzahl if anzahl else np.nan,
        })
    erwartet = pd.DataFrame(zeilen)
    erwartet.to_csv(pfade.daten() / "erwartet_hitze.csv", index=False)
    tag = []
    for nummer in range(len(gebiete)):
        im_gebiet = (gebiet == nummer) & innen
        anzahl = im_gebiet.sum()
        tag.append({
            "stadtteil": f"Testgebiet {nummer + 1:02d}",
            "bewertet_ha": anzahl * zellflaeche / 1e4,
            "anteil_ueber_41c_pct": 100 * (im_gebiet & (pet_extrem > 41)).sum() / anzahl if anzahl else np.nan,
            "anteil_ueber_41c_pct_typisch": 100 * (im_gebiet & (pet_typisch > 41)).sum() / anzahl if anzahl else np.nan,
            "pet_mittel_c": float(pet_extrem[im_gebiet].mean()) if anzahl else np.nan,
        })
    pd.DataFrame(tag).to_csv(pfade.daten() / "erwartet_hitze_tag.csv", index=False)
    versiegelung = []
    for nummer in range(len(gebiete)):
        im_gebiet = (gebiet == nummer) & innen
        anzahl = im_gebiet.sum()
        versiegelung.append({
            "stadtteil": f"Testgebiet {nummer + 1:02d}",
            "bewertet_ha": anzahl * zellflaeche / 1e4,
            "anteil_versiegelt_pct": 100 * (im_gebiet & (maske == 1)).sum() / anzahl if anzahl else np.nan,
        })
    pd.DataFrame(versiegelung).to_csv(pfade.daten() / "erwartet_versiegelung.csv", index=False)
    return erwartet


LANDBEDECKUNG = [  # (Layer, Feldwerte, Gruppe laut katalog/zuordnungen/landbedeckung-nrw.yaml)
    ("lb_hochbau", {}, "hochbau"),
    ("lb_tiefbau", {}, "tiefbau"),
    ("lb_krautigevegetation", {"vegetationsmerkmal": "1000"}, "gras"),
    ("lb_krautigevegetation", {"vegetationsmerkmal": "3000"}, "kraut_sonstige"),
    ("lb_holzigevegetation", {"vegetationsmerkmal": "4000", "blattform": "1000"}, "baeume"),
    ("lb_holzigevegetation", {"vegetationsmerkmal": "6000", "blattform": ""}, "gehoelz"),
    ("lb_binnengewaesser", {"fliesseigenschaft": "2000"}, "wasser"),
    ("lb_lockermaterial", {}, "lockermaterial"),
]
GRUEN = {"gras", "kraut_sonstige", "baeume", "gehoelz"}


def _landbedeckung(umriss: Polygon, gebiete: list[Polygon], rng, kante: float = 400.0) -> None:
    """Quadrate mit zufälliger Klasse (innen eher bebaut, außen eher grün), auf den Umriss zugeschnitten."""
    minx, miny, maxx, maxy = umriss.bounds
    zeilen = {layer: [] for layer, _, _ in LANDBEDECKUNG}
    for x in np.arange(minx, maxx, kante):
        for y in np.arange(miny, maxy, kante):
            quadrat = shapely.box(x, y, x + kante, y + kante).intersection(umriss)
            if quadrat.is_empty or quadrat.area < 1:
                continue
            d = Point(x + kante / 2, y + kante / 2).distance(Point(MITTE_X, MITTE_Y)) / 1000
            p_bebaut = np.clip(0.85 - 0.09 * d, 0.1, 0.85)
            gewichte = np.array([p_bebaut * 0.45, p_bebaut * 0.55] + [(1 - p_bebaut) / 4] * 4 + [0.02, 0.01])
            nummer = rng.choice(len(LANDBEDECKUNG), p=gewichte / gewichte.sum())
            layer, felder, _ = LANDBEDECKUNG[nummer]
            zeilen[layer].append({**felder, "geometry": quadrat})
    ordner = pfade.roh("landbedeckung-nrw")
    ordner.mkdir(parents=True)
    gpkg = ordner / "Duesseldorf.gpkg"
    erwartet = []
    for layer, liste in zeilen.items():
        gpd.GeoDataFrame(liste, geometry="geometry", crs="EPSG:25832").to_file(gpkg, layer=layer, driver="GPKG")
    # Prüfwerte unabhängig von der Analyse: Schnittflächen mit shapely
    for nummer, gebiet in enumerate(gebiete):
        flaeche = {g: 0.0 for _, _, g in LANDBEDECKUNG}
        for layer, felder, gruppe in LANDBEDECKUNG:
            for zeile in zeilen[layer]:
                if all(zeile.get(k) == v for k, v in felder.items()):
                    flaeche[gruppe] += zeile["geometry"].intersection(gebiet).area
        gesamt = sum(flaeche.values())
        erwartet.append({"stadtteil": f"Testgebiet {nummer + 1:02d}", "bedeckt_ha": gesamt / 1e4,
                         "anteil_gruen_pct": 100 * sum(flaeche[g] for g in GRUEN) / gesamt if gesamt else np.nan,
                         "anteil_baeume_pct": 100 * flaeche["baeume"] / gesamt if gesamt else np.nan})
    pd.DataFrame(erwartet).to_csv(pfade.daten() / "erwartet_gruenanteil.csv", index=False)
    name = "lb_nrw_05100000_Düsseldorf_EPSG25832_GeoPackage.zip"
    with zipfile.ZipFile(ordner / name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(gpkg, arcname=gpkg.name)
    gpkg.unlink()
    _abruf("landbedeckung-nrw", [name], "dl-de-by-2.0", "geobasis")


LAERM_STUFEN = {"Nacht": range(45, 80, 5), "24h": range(50, 80, 5)}
LAERM_SCHWELLE = {"Nacht": 55, "24h": 65}  # Standard der Analyse laerm


def _laerm_abstand(stufe: int, zeit: str) -> float:
    """Erfunden: Abstand in m, bis zu dem der Pegel mindestens `stufe` dB(A) erreicht."""
    return (80 - stufe) * 25.0 + (100.0 if zeit == "24h" else 0.0)


def _laerm(gebiete: list[Polygon]) -> None:
    """Acht Shapes in ZIPs wie die echte Lärmkarte. Quellen sind erfundene Linien und ein Punkt."""
    from shapely.geometry import LineString

    x, y = MITTE_X, MITTE_Y
    linien = {
        "Strassen": LineString([(x - 6000, y), (x + 6000, y)]).union(LineString([(x, y - 5000), (x, y + 5000)])),
        "DB": LineString([(x - 5000, y - 4000), (x + 5000, y + 4000)]),
        "Ruhrbahn": LineString([(x - 3000, y + 2500), (x + 3000, y + 2500)]),
        "IED_Anlagen": Point(x + 3500, y - 3000),
    }
    stand = {"Strassen": 2011}
    ordner = pfade.roh("laermkarte-essen")
    ordner.mkdir(parents=True)
    namen = []
    for quelle, linie in linien.items():
        for zeit, stufen in LAERM_STUFEN.items():
            zeilen = []
            for stufe in stufen:
                aussen = linie.buffer(_laerm_abstand(stufe, zeit))
                innen = linie.buffer(_laerm_abstand(stufe + 5, zeit)) if stufe + 5 in stufen else None
                band = aussen.difference(innen) if innen is not None else aussen
                if quelle == "Strassen":    # verschachtelt, 3D wie im Original
                    zeilen.append({"DK_ISOTYP": 0, "WERT": float(stufe), "WERTMIN": 0.0, "MODI": "STR",
                                   "geometry": shapely.force_3d(aussen)})
                elif quelle == "DB":        # verschachtelt, Untergrenze als X,01
                    zeilen.append({"ID": 1000 + stufe, "ART": "LNight AllSrcs", "KLASSE": stufe + 0.01,
                                   "geometry": aussen})
                elif quelle == "Ruhrbahn":  # Bänder mit Unter- und Obergrenze
                    zeilen.append({"ISOV1": float(stufe), "ISOV2": float(stufe + 5), "MODI": "Ruhrbahn",
                                   "geometry": band})
                else:                       # Bänder mit einem Wert
                    zeilen.append({"DK_ISOTYP": 0, "WERT": float(stufe), "WERTMIN": 0.0, "MODI": "IED_ISO",
                                   "geometry": band})
            name = f"Laerm_{quelle}_{zeit}_{stand.get(quelle, 2016)}"
            teil = ordner / name
            teil.mkdir()
            gpd.GeoDataFrame(zeilen, geometry="geometry", crs="EPSG:25832").to_crs("EPSG:4647").to_file(
                teil / f"{name}.shp")
            with zipfile.ZipFile(ordner / f"{name}.zip", "w", zipfile.ZIP_DEFLATED) as zf:
                for datei in sorted(teil.iterdir()):
                    zf.write(datei, arcname=datei.name)
            shutil.rmtree(teil)
            namen.append(f"{name}.zip")
    # Prüfwerte unabhängig von der Analyse: Puffer bei der Schwelle, vereinigt über alle Quellen
    erwartet = []
    for nummer, gebiet in enumerate(gebiete):
        zeile = {"stadtteil": f"Testgebiet {nummer + 1:02d}"}
        for zeit, schwelle in LAERM_SCHWELLE.items():
            laut = shapely.union_all([linie.buffer(_laerm_abstand(schwelle, zeit)) for linie in linien.values()])
            zeile[f"anteil_{zeit.lower()}_pct"] = 100 * laut.intersection(gebiet).area / gebiet.area
        erwartet.append(zeile)
    pd.DataFrame(erwartet).to_csv(pfade.daten() / "erwartet_laerm.csv", index=False)
    _abruf("laermkarte-essen", namen, "dl-de-by-2.0", "essen-opendata")


STARKREGEN_TEXT = {1: "0 - <0,05", 2: "0,05 - <0,25", 3: ">= 0,25"}


def _starkregen(umriss: Polygon, gebiete: list[Polygon], rng, kante: float = 300.0) -> None:
    """Quadrate mit Einstauklasse; etwa jedes zehnte fehlt (wie Lücken im Original)."""
    minx, miny, maxx, maxy = umriss.bounds
    zeilen = []
    for x in np.arange(minx, maxx, kante):
        for y in np.arange(miny, maxy, kante):
            quadrat = shapely.box(x, y, x + kante, y + kante).intersection(umriss)
            if quadrat.is_empty or quadrat.area < 1 or rng.random() < 0.1:
                continue
            klasse = int(rng.choice([1, 2, 3], p=[0.80, 0.14, 0.06]))
            zeilen.append({"Id": len(zeilen) + 1, "gridcode": klasse, "Shape_Leng": quadrat.length,
                           "Shape_Area": quadrat.area, "Einstautie": STARKREGEN_TEXT[klasse], "geometry": quadrat})
    erwartet = []
    for nummer, gebiet in enumerate(gebiete):
        flaeche = {k: sum(z["geometry"].intersection(gebiet).area for z in zeilen if z["gridcode"] == k) for k in (1, 2, 3)}
        erwartet.append({"stadtteil": f"Testgebiet {nummer + 1:02d}", "tief_ha": flaeche[3] / 1e4,
                         "anteil_ueber_25cm_pct": 100 * flaeche[3] / gebiet.area,
                         "anteil_ueber_5cm_pct": 100 * (flaeche[2] + flaeche[3]) / gebiet.area})
    pd.DataFrame(erwartet).to_csv(pfade.daten() / "erwartet_starkregen_mit_gewaesser.csv", index=False)
    ordner = pfade.roh("starkregen-essen")
    teil = ordner / "shape"
    teil.mkdir(parents=True)
    gpd.GeoDataFrame(zeilen, geometry="geometry", crs="EPSG:25832").to_crs("EPSG:4647").to_file(
        teil / "Ueberflutung_Kategorien.shp")
    with zipfile.ZipFile(ordner / "Starkregen_0.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for datei in sorted(teil.iterdir()):
            zf.write(datei, arcname=datei.name)
    shutil.rmtree(teil)
    _abruf("starkregen-essen", ["Starkregen_0.zip"], "dl-de-by-2.0", "essen-opendata")


def _erwartet_starkregen(gebiete: list[Polygon]) -> None:
    """Prüfwerte für Starkregen ohne Gewässer (E-017): aus den geschriebenen Testdateien, nur mit shapely."""
    wasser_zip = next(pfade.roh("landbedeckung-nrw").glob("*.zip"))
    wasser = gpd.read_file(f"zip://{wasser_zip}!Duesseldorf.gpkg", layer="lb_binnengewaesser").geometry.union_all()
    flaechen = gpd.read_file(f"zip://{pfade.roh('starkregen-essen') / 'Starkregen_0.zip'}!Ueberflutung_Kategorien.shp")
    flaechen = flaechen.to_crs("EPSG:25832")
    erwartet = []
    for nummer, gebiet in enumerate(gebiete):
        land = gebiet.difference(wasser)
        flaeche = {k: sum(g.intersection(land).area for g in flaechen.geometry[flaechen["gridcode"] == k]) for k in (2, 3)}
        erwartet.append({"stadtteil": f"Testgebiet {nummer + 1:02d}", "tief_ha": flaeche[3] / 1e4,
                         "land_ha": land.area / 1e4, "anteil_ueber_25cm_pct": 100 * flaeche[3] / land.area,
                         "anteil_ueber_5cm_pct": 100 * (flaeche[2] + flaeche[3]) / land.area})
    pd.DataFrame(erwartet).to_csv(pfade.daten() / "erwartet_starkregen.csv", index=False)


def _zensus(umriss: Polygon, rng) -> None:
    """100-m-Zellen in EPSG:3035 über dem Umriss; innen dichter besiedelt, ein Teil der Zellen leer (fehlt)."""
    nach_laea = Transformer.from_crs("EPSG:25832", "EPSG:3035", always_xy=True)
    flaeche = shapely.transform(umriss, lambda x, y: nach_laea.transform(x, y), interleaved=False)
    minx, miny, maxx, maxy = (int(v // 100 * 100) for v in flaeche.bounds)
    mitte = flaeche.centroid
    zeilen = []
    for x in range(minx, int(maxx) + 100, 100):
        for y in range(miny, int(maxy) + 100, 100):
            if not flaeche.contains(Point(x + 50, y + 50)) or rng.random() < 0.3:
                continue
            d = Point(x + 50, y + 50).distance(mitte) / 1000
            zeilen.append((f"CRS3035RES100mN{y}E{x}", x + 50, y + 50, int(rng.integers(1, max(2, int(120 - 15 * d))))))
    tabelle = pd.DataFrame(zeilen, columns=["GITTER_ID_100m", "x_mp_100m", "y_mp_100m", "Einwohner"])
    ordner = pfade.roh("zensus-2022-gitter")
    ordner.mkdir(parents=True)
    name = "Zensus2022_Bevoelkerungszahl.zip"
    with zipfile.ZipFile(ordner / name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Zensus2022_Bevoelkerungszahl_100m-Gitter.csv", tabelle.to_csv(sep=";", index=False))
        zf.writestr("LIESMICH_Testdaten.txt", "Erfundene Einwohnerzahlen im Aufbau des Zensus-Gitters.\n")
    _abruf("zensus-2022-gitter", [name], "dl-de-by-2.0", "zensus-2022")


UBA_INDICES = ["station id", "station code", "station name", "station city", "station synonym",
               "station active from", "station active to", "station longitude", "station latitude", "network id",
               "station setting id", "station type id", "network code", "network name", "station setting name",
               "station setting short name", "station type name", "station street", "station street nr",
               "station zip code"]
UBA_HEADERS = {
    "no2": {"1": "Jahresmittelwert in µg/m³", "2": "Zahl der Stundenmittelwerte über 200 µg/m³*"},
    "pm10": {"1": "Jahresmittelwert in µg/m³", "2": "Zahl der Tageswerte über 50 µg/m3",
             "3": "Zahl der Tageswerte über 50 µg/m3 nach Abzug Streusalz etc. *"},
    "pm25": {"1": "Jahresmittelwert in µg/m³"},
}
UBA_KOMPONENTE = {"no2": "5", "pm10": "1", "pm25": "9"}


def _uba_jahresbilanzen(rng) -> None:
    """Drei erfundene Essener Stationen und eine in einer anderen Stadt; NO₂ sinkt über die Jahre."""
    stationen = {"901": ("DENW901", "Essen Teststraße", "Essen", "Verkehr"),
                 "902": ("DENW902", "Essen-Testpark", "Essen-Testviertel", "Hintergrund"),
                 "903": ("DENW903", "Essen Alte Teststraße", "Essen", "Verkehr"),
                 "904": ("DENW904", "Anderswo", "Bochum", "Verkehr")}
    daten = {}
    for kennung, (code, name, ort, typ) in stationen.items():
        zeile = [kennung, code, name, ort, code[-3:], "2005-01-01", "2015-12-31" if kennung == "903" else None,
                 "7.0", "51.45", "1", "1", "3", "NW", "Nordrhein-Westfalen", "städtisches Gebiet", "städtisch", typ,
                 "Teststraße", "1", "45127"]
        daten[kennung] = zeile
    ordner = pfade.roh("uba-jahresbilanzen")
    ordner.mkdir(parents=True)
    namen = ["stationen.json"]
    (ordner / "stationen.json").write_text(json.dumps({"request": {"lang": "de", "index": "id"}, "indices": UBA_INDICES,
                                                       "data": daten}, ensure_ascii=False), encoding="utf-8")
    erwartet = []
    for jahr in range(2010, 2026):
        for stoff, headers in UBA_HEADERS.items():
            zeilen = []
            for kennung in stationen:
                if kennung == "903" and jahr > 2015:
                    continue
                if stoff == "pm25" and kennung == "901":
                    continue
                basis = {"no2": 55, "pm10": 30, "pm25": 18}[stoff] - (jahr - 2010) * (1.5 if stoff == "no2" else 0.6)
                wert = round(basis - (12 if kennung == "902" else 0) + rng.normal(0, 1))
                zeilen.append([kennung] + [str(wert)] + [str(int(rng.integers(0, 30)))] * (len(headers) - 1))
                if kennung != "904":
                    erwartet.append({"jahr": jahr, "schadstoff": stoff, "code": stationen[kennung][0], "wert": wert})
            name = f"jahr_{jahr}_{stoff}.json"
            antwort = {"request": {"component": UBA_KOMPONENTE[stoff], "year": str(jahr), "lang": "de"},
                       "data": zeilen, "headers": headers,
                       "indices": {"data": ["0: station id - string", "x: Value of headers[x] - string"]}}
            (ordner / name).write_text(json.dumps(antwort, ensure_ascii=False), encoding="utf-8")
            namen.append(name)
    pd.DataFrame(erwartet).to_csv(pfade.daten() / "erwartet_luft.csv", index=False)
    _abruf("uba-jahresbilanzen", namen, "dl-de-by-2.0", "uba")


BETROFFENHEIT_TEXT = {1: "nicht sensitiv", 2: "sensitiv", 3: "hoch sensitiv", 4: "extrem sensitiv"}


def _betroffenheit(umriss: Polygon, gebiete: list[Polygon], rng, kante: float = 250.0) -> None:
    """Quadratische „Baublöcke“ auf etwa der Hälfte der Fläche; ein Teil davon mit Handlungsbedarf (_HP)."""
    minx, miny, maxx, maxy = umriss.bounds
    komplett, hp = [], []
    for x in np.arange(minx, maxx, kante):
        for y in np.arange(miny, maxy, kante):
            block = shapely.box(x + 20, y + 20, x + kante - 20, y + kante - 20).intersection(umriss)
            if block.is_empty or block.area < 1 or rng.random() < 0.5:
                continue
            klasse = int(rng.choice([1, 2, 3, 4], p=[0.75, 0.15, 0.08, 0.02]))
            gemeinde = "Nachbarstadt" if rng.random() < 0.05 else "Essen"
            zeile = {"blck_d_": f"B{len(komplett)}", "block_d": f"{len(komplett)}", "gemeind": gemeinde,
                     "senstvt": float(klasse), "Betroffenheit": BETROFFENHEIT_TEXT[klasse], "geometry": block}
            komplett.append(zeile)
            if rng.random() < 0.45:
                hp.append(dict(zeile))
    erwartet = []

    def summe(zeilen, nur_sensitiv, gebiet):
        return sum(z["geometry"].intersection(gebiet).area for z in zeilen
                   if z["gemeind"] == "Essen" and (z["senstvt"] >= 2 or not nur_sensitiv))

    for nummer, gebiet in enumerate(gebiete):
        bloecke = summe(komplett, False, gebiet)
        erwartet.append({"stadtteil": f"Testgebiet {nummer + 1:02d}", "baubloecke_ha": bloecke / 1e4,
                         "anteil_betroffen_pct": 100 * summe(hp, True, gebiet) / bloecke if bloecke else np.nan,
                         "anteil_sensitiv_pct": 100 * summe(komplett, True, gebiet) / bloecke if bloecke else np.nan})
    pd.DataFrame(erwartet).to_csv(pfade.daten() / "erwartet_betroffenheit.csv", index=False)
    ordner = pfade.roh("klimaanalyse-betroffenheit")
    ordner.mkdir(parents=True)
    gpkg = ordner / "Klimaanalyse-Betroffenheitsanalyse_2026_EPSG25832.gpkg"
    for layer, zeilen in (("PL_KY_BTA_Gesamtbetrachtung_HP", hp), ("PL_KY_BTA_Gesamtbetrachtung_komplett", komplett)):
        gpd.GeoDataFrame(zeilen, geometry="geometry", crs="EPSG:25832").to_file(gpkg, layer=layer, driver="GPKG")
    name = "Klimaanalyse-Betroffenheitsanalyse_2026_EPSG25832_GeoPackage.zip"
    with zipfile.ZipFile(ordner / name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(gpkg, arcname=gpkg.name)
    gpkg.unlink()
    _abruf("klimaanalyse-betroffenheit", [name], "dl-de-zero-2.0", "lanuk")


KLIMATOPE = {  # Code → (Text, Gruppe) wie katalog/zuordnungen/klimaanalyse-klimatope.yaml
    1: ("Gewässer-, Seeklima", "gruen_wasser"), 2: ("Freilandklima", "gruen_wasser"), 3: ("Waldklima", "gruen_wasser"),
    4: ("Klima innerstädtischer Grünflächen", "gruen_wasser"), 5: ("Vorstadtklima", "locker"),
    6: ("Stadtrandklima", "locker"), 7: ("Stadtklima", "dicht"), 8: ("Innenstadtklima", "dicht"),
    9: ("Gewerbe-, Industrieklima (offen)", "locker"), 10: ("Gewerbe-, Industrieklima (dicht)", "dicht"),
    -999: ("Straßenverkehr", "verkehr"), -99: ("Bahnverkehr", "verkehr"),
}


def _klimatope(umriss: Polygon, gebiete: list[Polygon], rng, kante: float = 350.0) -> None:
    """Quadrate mit Klimatop (innen eher dicht, außen eher grün); Feldnamen wie PL_KY_KLIMATOP."""
    minx, miny, maxx, maxy = umriss.bounds
    codes = list(KLIMATOPE)
    zeilen = []
    for x in np.arange(minx, maxx, kante):
        for y in np.arange(miny, maxy, kante):
            quadrat = shapely.box(x, y, x + kante, y + kante).intersection(umriss)
            if quadrat.is_empty or quadrat.area < 1:
                continue
            d = Point(x + kante / 2, y + kante / 2).distance(Point(MITTE_X, MITTE_Y)) / 1000
            dicht = float(np.clip(0.6 - 0.08 * d, 0.05, 0.6))
            gewichte = np.array([0.02, 0.1, 0.1, 0.1, 0.12, 0.12, dicht, dicht / 3, 0.06, dicht / 2, 0.06, 0.02])
            code = codes[rng.choice(len(codes), p=gewichte / gewichte.sum())]
            zeilen.append({"KT_R02_2": float(code), "Shape_Length": quadrat.length, "Shape_Area": quadrat.area,
                           "Klimatoptyp": KLIMATOPE[code][0], "geometry": quadrat})
    erwartet = []
    for nummer, gebiet in enumerate(gebiete):
        je_gruppe = {}
        for z in zeilen:
            gruppe = KLIMATOPE[int(z["KT_R02_2"])][1]
            je_gruppe[gruppe] = je_gruppe.get(gruppe, 0.0) + z["geometry"].intersection(gebiet).area
        gesamt = sum(je_gruppe.values())
        erwartet.append({"stadtteil": f"Testgebiet {nummer + 1:02d}", "bedeckt_ha": gesamt / 1e4,
                         **{f"anteil_{g}_pct": 100 * je_gruppe.get(g, 0.0) / gesamt if gesamt else np.nan
                            for g in ("dicht", "locker", "gruen_wasser", "verkehr")}})
    pd.DataFrame(erwartet).to_csv(pfade.daten() / "erwartet_klimatope.csv", index=False)
    ordner = pfade.roh("klimaanalyse-klimatope")
    ordner.mkdir(parents=True)
    gpkg = ordner / "Klimaanalyse-Klimatopkarte_2026_EPSG25832.gpkg"
    gpd.GeoDataFrame(zeilen, geometry="geometry", crs="EPSG:25832").to_file(gpkg, layer="PL_KY_KLIMATOP", driver="GPKG")
    name = "Klimaanalyse-Klimatopkarte_2026_EPSG25832_GeoPackage.zip"
    with zipfile.ZipFile(ordner / name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(gpkg, arcname=gpkg.name)
    gpkg.unlink()
    _abruf("klimaanalyse-klimatope", [name], "dl-de-zero-2.0", "lanuk")


PLANUNGSHINWEIS_STUFE = {1: "Dringender Handlungsbedarf", 2: "Dringender Handlungsbedarf",
                         3: "Erweiterter Handlungsbedarf", 4: "Erweiterter Handlungsbedarf",
                         5: "Mäßiger Handlungsbedarf", 6: "Kein Handlungsbedarf"}


def _planungshinweise(umriss: Polygon, gebiete: list[Polygon], rng, kante: float = 300.0) -> None:
    """Wirkraum-Flächen mit Handlungspriorität 1–6 (Layer PL_KY_PHK_HP), dazu ein Ausgleichsraum-Layer."""
    minx, miny, maxx, maxy = umriss.bounds
    zeilen, ausgleich = [], []
    for x in np.arange(minx, maxx, kante):
        for y in np.arange(miny, maxy, kante):
            flaeche = shapely.box(x + 15, y + 15, x + kante - 15, y + kante - 15).intersection(umriss)
            if flaeche.is_empty or flaeche.area < 1:
                continue
            if rng.random() < 0.35:  # Grün und Freiflächen: Ausgleichsraum
                ausgleich.append({"Ausgleichsraum": "Hohe Bedeutung", "Planungshinweis": "(erfunden)",
                                  "geometry": flaeche})
                continue
            d = Point(x + kante / 2, y + kante / 2).distance(Point(MITTE_X, MITTE_Y)) / 1000
            p_dringend = float(np.clip(0.55 - 0.07 * d, 0.05, 0.55))
            gewichte = np.array([p_dringend / 6, p_dringend, 0.3, 0.12, 0.2, 0.04])
            hp = int(rng.choice(range(1, 7), p=gewichte / gewichte.sum()))
            gemeinde = "Nachbarstadt" if rng.random() < 0.05 else "Essen"
            zeilen.append({"GN": gemeinde, "Handlungspriorität": f"Handlungspriorität {hp}",
                           "Planungshinweis": f"{PLANUNGSHINWEIS_STUFE[hp]}: Erfundener Hinweistext.",
                           "Shape_Length": flaeche.length, "Shape_Area": flaeche.area,
                           "Einwohnerzahl": float(rng.integers(0, 400)), "geometry": flaeche})
    erwartet = []

    def summe(gebiet, stufe=None):
        return sum(z["geometry"].intersection(gebiet).area for z in zeilen if z["GN"] == "Essen" and
                   (stufe is None or z["Planungshinweis"].startswith(stufe)))

    for nummer, gebiet in enumerate(gebiete):
        wirkraum = summe(gebiet)
        erwartet.append({"stadtteil": f"Testgebiet {nummer + 1:02d}", "wirkraum_ha": wirkraum / 1e4,
                         "anteil_dringend_pct": 100 * summe(gebiet, "Dringender") / wirkraum if wirkraum else np.nan,
                         "anteil_kein_pct": 100 * summe(gebiet, "Kein") / wirkraum if wirkraum else np.nan})
    pd.DataFrame(erwartet).to_csv(pfade.daten() / "erwartet_planungshinweise.csv", index=False)
    ordner = pfade.roh("klimaanalyse-planungshinweise")
    ordner.mkdir(parents=True)
    gpkg = ordner / "Klimaanalyse-Planungshinweiskarte_2026_EPSG25832.gpkg"
    gpd.GeoDataFrame(ausgleich, geometry="geometry", crs="EPSG:25832").to_file(gpkg, layer="PL_KY_PHK_AR", driver="GPKG")
    gpd.GeoDataFrame(zeilen, geometry="geometry", crs="EPSG:25832").to_file(gpkg, layer="PL_KY_PHK_HP", driver="GPKG")
    name = "Klimaanalyse-Planungshinweiskarte_2026_EPSG25832_GeoPackage.zip"
    with zipfile.ZipFile(ordner / name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(gpkg, arcname=gpkg.name)
    gpkg.unlink()
    _abruf("klimaanalyse-planungshinweise", [name], "dl-de-zero-2.0", "lanuk")


def _beschreibung() -> None:
    """Wie das echte Klimaanalyse_meta.zip: nur Dokumente, keine Stildatei."""
    ordner = pfade.roh("klimaanalyse-beschreibung")
    ordner.mkdir(parents=True)
    with zipfile.ZipFile(ordner / "Klimaanalyse_meta.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("LIESMICH_Testdaten.txt",
                    "Erfundene Testdaten. Das echte ZIP enthält PDF-Dokumente (Methodik, Nomenklatur), keine Stildateien.\n")
    _abruf("klimaanalyse-beschreibung", ["Klimaanalyse_meta.zip"], "dl-de-zero-2.0", "lanuk")


def klassenraster_mit_legende(mit_legende: bool = True) -> None:
    """Ersetzt im aktuellen Datenordner das Raster durch ein Klassenraster mit Farbtabelle (eine Datei) und legt
    auf Wunsch eine QGIS-Stildatei als Legende dazu. Für Tests der Legendenerkennung; so liefert das LANUK
    die Klimaanalyse 2026 nicht aus."""
    import rasterio

    ordner = pfade.roh("klimaanalyse-nacht-raster")
    with zipfile.ZipFile(ordner / RASTER_ZIP) as zf:
        lt = zf.read("PL_KY_NACHT_LT_EXT.tif")
        kvsd = zf.read("PL_KY_NACHT_KVSD_EXT.tif")
    with rasterio.MemoryFile(lt) as a, a.open() as r_lt, rasterio.MemoryFile(kvsd) as b, b.open() as r_kv:
        temperatur = r_lt.read(1, masked=True)
        kaltluft = r_kv.read(1, masked=True)
        profil = r_lt.profile
    klasse = np.clip(1 + np.searchsorted(GRENZEN_C, np.ma.filled(temperatur, 0), side="left"), 1, 8)
    stufe = 11 + np.searchsorted([5, 10, 20, 40], np.ma.filled(kaltluft, 0), side="left")
    werte = np.where(~np.ma.getmaskarray(temperatur), klasse, np.where(~np.ma.getmaskarray(kaltluft), stufe, 0))
    profil.update(dtype="uint8", nodata=0, compress="deflate")
    puffer = io.BytesIO()
    with rasterio.MemoryFile() as speicher:
        with speicher.open(**profil) as ds:
            ds.write(werte.astype("uint8"), 1)
            ds.write_colormap(1, {k: (*v, 255) for k, v in FARBEN.items()})
        puffer.write(speicher.read())
    for alt in ordner.iterdir():
        if alt.is_dir():
            shutil.rmtree(alt)
    with zipfile.ZipFile(ordner / RASTER_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Klimaanalyse-Karte-Nacht_2026_EPSG25832.tif", puffer.getvalue())
    if mit_legende:
        _legende_als_qml()


def _legende_als_qml() -> None:
    eintraege = {**WIRKRAUM_LABEL, **AUSGLEICH_LABEL}
    palette = "\n".join(
        f'        <paletteEntry value="{wert}" color="#{FARBEN[wert][0]:02x}{FARBEN[wert][1]:02x}{FARBEN[wert][2]:02x}" '
        f'label="{label.replace("<", "&lt;").replace(">", "&gt;")}" alpha="255"/>'
        for wert, label in eintraege.items()
    )
    qml = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34.0" styleCategories="AllStyleCategories">
  <pipe>
    <rasterrenderer type="paletted" band="1" opacity="1" alphaBand="-1">
      <colorPalette>
{palette}
      </colorPalette>
    </rasterrenderer>
  </pipe>
</qgis>
"""
    ordner = pfade.roh("klimaanalyse-beschreibung")
    for alt in ordner.iterdir():
        if alt.is_dir():
            shutil.rmtree(alt)
    with zipfile.ZipFile(ordner / "Klimaanalyse_meta.zip", "a", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Testdaten_Legende_Klimaanalysekarte_Nacht.qml", qml)


def _dwd(rng) -> None:
    def reihe(von: dt.date, bis: dt.date) -> pd.DataFrame:
        tage = pd.date_range(von, bis, freq="D")
        jahre = (tage.year - 1991) / 33
        saison = np.sin(2 * np.pi * (tage.dayofyear - 110) / 365.25)
        txk = 14.5 + 10.5 * saison + 1.8 * jahre + rng.normal(0, 3.2, len(tage))
        tnk = txk - 8.5 + rng.normal(0, 1.8, len(tage))
        return pd.DataFrame({
            "STATIONS_ID": 1303, "MESS_DATUM": tage.strftime("%Y%m%d"), "QN_3": 10, "FX": -999, "FM": -999, "QN_4": 3,
            "RSK": np.round(np.clip(rng.gamma(0.6, 4.0, len(tage)) - 1.0, 0, None), 1), "RSKF": 6, "SDK": -999,
            "SHK_TAG": 0, "NM": -999, "VPM": -999, "PM": -999, "TMK": np.round((txk + tnk) / 2, 1), "UPM": -999,
            "TXK": np.round(txk, 1), "TNK": np.round(tnk, 1), "TGK": -999, "eor": "eor",
        })

    def schreibe(kennung: str, dateiname: str, df: pd.DataFrame, von: dt.date, bis: dt.date) -> None:
        ordner = pfade.roh(kennung)
        ordner.mkdir(parents=True)
        df.loc[df.sample(frac=0.002, random_state=1).index, ["TXK", "TNK"]] = -999  # einzelne Fehlwerte
        text = df.to_csv(sep=";", index=False)
        geo = ("Stations_id;Stationshoehe;Geogr.Breite;Geogr.Laenge;von_datum;bis_datum;Stationsname\n"
               "1303;150;51.4041;6.9677;19910101;;Teststation (erfunden)\n")
        with zipfile.ZipFile(ordner / dateiname, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"produkt_klima_tag_{von:%Y%m%d}_{bis:%Y%m%d}_01303.txt", text.encode("latin-1"))
            zf.writestr("Metadaten_Geographie_01303.txt", geo.encode("latin-1"))
        _abruf(kennung, [dateiname], "cc-by-4.0", "dwd")

    heute = dt.date.today()
    hist_bis = dt.date(heute.year - 2, 12, 31)
    schreibe("dwd-klima-essen-historisch", f"tageswerte_KL_01303_19910101_{hist_bis:%Y%m%d}_hist.zip",
             reihe(dt.date(1991, 1, 1), hist_bis), dt.date(1991, 1, 1), hist_bis)
    akt_von = dt.date(heute.year - 2, 4, 1)
    akt_bis = heute - dt.timedelta(days=1)
    schreibe("dwd-klima-essen-aktuell", "tageswerte_KL_01303_akt.zip", reihe(akt_von, akt_bis), akt_von, akt_bis)


# Ursprung des echten DWD-Gitters (Kopf der Jahresraster); der Ausschnitt der Testdaten liegt auf demselben Gitter
DWD_X0, DWD_Y0, DWD_ZELLE = 3280414.711633467, 5237500.62890625, 1000.0


def _dwd_raster(umriss: Polygon, rng, von: int = 1951) -> None:
    """Jahresraster heiße Tage, Sommertage, Jahresmittel: im Norden etwas wärmer, über die Jahre wärmer."""
    import gzip

    gk = gpd.GeoSeries([umriss], crs="EPSG:25832").to_crs("EPSG:31467").total_bounds
    s0 = int((gk[0] - 3000 - DWD_X0) // DWD_ZELLE)
    z0 = int((gk[1] - 3000 - DWD_Y0) // DWD_ZELLE)
    spalten = int((gk[2] + 3000 - DWD_X0) // DWD_ZELLE) - s0 + 1
    zeilen = int((gk[3] + 3000 - DWD_Y0) // DWD_ZELLE) - z0 + 1
    nord = np.linspace(1, 0, zeilen)[:, None] * np.ones((1, spalten))  # Zeilen von Nord nach Süd
    bis = dt.date.today().year - 1
    arten = {
        "dwd-raster-heisse-tage": ("grids_germany_annual_hot_days_{}_17.asc.gz", 3.0, 0.12, 2.0),
        "dwd-raster-sommertage": ("grids_germany_annual_summer_days_{}_17.asc.gz", 25.0, 0.3, 4.0),
        "dwd-raster-jahresmittel": ("grids_germany_annual_air_temp_mean_{}17.asc.gz", 92.0, 0.3, 5.0),
    }
    for kennung, (muster, grund, je_jahr, nord_plus) in arten.items():
        ordner = pfade.roh(kennung)
        ordner.mkdir(parents=True)
        namen = []
        for jahr in range(von, bis + 1):
            schwankung = rng.normal(0, grund * 0.3)
            werte = np.clip(np.round(grund + je_jahr * (jahr - von) + nord_plus * nord + schwankung
                                     + rng.normal(0, 0.3, nord.shape)), 0, None).astype(int)
            werte[0, 0] = -999  # einzelner Fehlwert am Rand
            kopf = (f"NCOLS {spalten}\nNROWS {zeilen}\nXLLCORNER {DWD_X0 + s0 * DWD_ZELLE}\n"
                    f"YLLCORNER {DWD_Y0 + z0 * DWD_ZELLE}\nCELLSIZE {DWD_ZELLE:g}\nNODATA_VALUE -999\n")
            text = kopf + "\n".join(" ".join(f"{w:4d}" for w in zeile) for zeile in werte) + "\n"
            name = muster.format(jahr)
            if kennung == "dwd-raster-jahresmittel" and jahr == von:  # wie beim DWD: ZIP mit Endung .asc.gz
                with zipfile.ZipFile(ordner / name, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(f"grids_germany_annual_air_temp_mean_{jahr}17.asc", text)
            else:
                (ordner / name).write_bytes(gzip.compress(text.encode("ascii")))
            namen.append(name)
        _abruf(kennung, namen, "cc-by-4.0", "dwd")


# -------------------------------------------------------------------- Punkte und Zonen (erfunden)

LADESAEULEN_KOPF = (
    "Ladeeinrichtungs-ID;Betreiber;Anzeigename (Karte);Status;Art der Ladeeinrichtung;Anzahl Ladepunkte;"
    "Nennleistung Ladeeinrichtung [kW];Inbetriebnahmedatum;Straße;Hausnummer;Adresszusatz;Postleitzahl;Ort;"
    "Kreis/kreisfreie Stadt;Bundesland;Breitengrad;Längengrad;Standortbezeichnung;Informationen zum Parkraum;"
    "Bezahlsysteme;Öffnungszeiten;Öffnungszeiten: Wochentage;Öffnungszeiten: Tageszeiten"
    + "".join(f";Steckertypen{i};Nennleistung Stecker{i};EVSE-ID{i};Public Key{i}" for i in range(1, 7)))


def _punkte_im_umriss(umriss: Polygon, anzahl: int, rng) -> list[Point]:
    x1, y1, x2, y2 = umriss.bounds
    punkte = []
    while len(punkte) < anzahl:
        p = Point(rng.uniform(x1, x2), rng.uniform(y1, y2))
        if umriss.contains(p):
            punkte.append(p)
    return punkte


def _orte(umriss: Polygon, rng) -> None:
    nach_wgs = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)

    def wgs(punkte):
        xs, ys = nach_wgs.transform([p.x for p in punkte], [p.y for p in punkte])
        return list(xs), list(ys)

    # Kühle Orte: GeoJSON in WGS84, Felder wie im Original
    punkte = _punkte_im_umriss(umriss, 40, rng)
    xs, ys = wgs(punkte)
    arten = ["Spielplatz", "Park", "Friedhof", "Bibliothek", "Hallenbad"]
    gdf = gpd.GeoDataFrame({
        "FID": range(40), "ID": range(40), "ORT": ["Innen" if i % 8 == 0 else "Außen" for i in range(40)],
        "ART": [arten[i % 5] for i in range(40)], "ADRESSE": [f"Teststraße {i + 1}" for i in range(40)],
        "KOSTEN": ["ja" if i % 10 == 0 else "nein" for i in range(40)],
        "BESCHREIBU": ["erfundener kühler Ort"] * 40, "NAME": [f"Testort {i + 1}" for i in range(40)],
        "OEFFNUNGSZ": ["keine"] * 40, "STADTTEIL": ["Testgebiet"] * 40, "STADTBEZIR": ["I"] * 40,
    }, geometry=gpd.points_from_xy(xs, ys), crs="EPSG:4326")
    ordner = pfade.roh("kuehlorte")
    ordner.mkdir(parents=True)
    gdf.to_file(ordner / "Kuehle_Orte.geojson", driver="GeoJSON")
    _abruf("kuehlorte", ["Kuehle_Orte.geojson"], "dl-de-by-2.0", "essen-opendata")

    # Jungbäume: GML in EPSG:25832 (wie der WFS der Stadt)
    punkte = _punkte_im_umriss(umriss, 300, rng)
    gdf = gpd.GeoDataFrame({
        "OBJECTID": range(1, 301), "NUMMER": [float(i) for i in range(1, 301)],
        "STADTBEZIR": [float(i % 9 + 1) for i in range(300)], "STADTTEIL": [float(i % 50 + 1) for i in range(300)],
        "X": [32_000_000 + p.x for p in punkte], "Y": [p.y for p in punkte],
        "PFLANZJAHR": [float(2008 + i % 18) for i in range(300)], "BEWÄSSERU": ["J" if i % 5 else "N" for i in range(300)],
        "KATEGORIE": ["2008-2019" if i % 18 < 12 else str(2008 + i % 18) for i in range(300)],
    }, geometry=punkte, crs="EPSG:25832")
    ordner = pfade.roh("stadtbaeume")
    ordner.mkdir(parents=True)
    gdf.to_file(ordner / "stadtbaeume.gml", driver="GML", layer="Stadtbaeume_Jungbaeume")
    _abruf("stadtbaeume", ["stadtbaeume.gml"], "dl-de-by-2.0", "essen-opendata")

    # Ladesäulenregister: Vorspann, Kopfzeile, ganz Deutschland; ein „Essen“ in Berlin darf nicht mitzählen
    punkte = _punkte_im_umriss(umriss, 25, rng)
    xs, ys = wgs(punkte)
    leer = ";" * 20  # zusammen 47 Felder wie die Kopfzeile
    zeilen = ["Ladesäulenregister Bundesnetzagentur" + ";" * 22, ";" * 22, "Hinweis: " + ";" * 22,
              "Erfundene Testdaten" + ";" * 22, *([";" * 22] * 6), LADESAEULEN_KOPF]
    for i, (x, y) in enumerate(zip(xs, ys, strict=True)):
        zeilen.append(f"{9000 + i};Test-Energie GmbH;Test-Energie;In Betrieb;Normalladeeinrichtung;2;22;01.01.2024;"
                      f"Teststraße;{i + 1};;45127;Essen;Kreisfreie Stadt Essen;Nordrhein-Westfalen;"
                      + f"{y:.6f};{x:.6f}".replace(".", ",")  # Dezimalkomma wie im Original
                      + ";;;RFID-Karte;Keine Angabe;;;AC Typ 2 Steckdose;22;;" + leer)
    zeilen.append("9900;Test GmbH;Test;In Betrieb;Normalladeeinrichtung;1;11;01.01.2021;Grunerstraße;20;;10179;Essen;"
                  "Kreisfreie Stadt Berlin;Berlin;52,519366;13,416644;;;RFID-Karte;Keine Angabe;;;AC Typ 2 Steckdose;11;;"
                  + leer)
    zeilen.append("9901;Test GmbH;Test;In Betrieb;Schnellladeeinrichtung;2;150;01.01.2025;Hauptstraße;1;;44787;Bochum;"
                  "Kreisfreie Stadt Bochum;Nordrhein-Westfalen;51,481;7,219;;;RFID-Karte;Keine Angabe;;;CCS;150;;"
                  + leer)
    ordner = pfade.roh("ladesaeulen")
    ordner.mkdir(parents=True)
    name = "Ladesaeulenregister_BNetzA_Test.csv"
    (ordner / name).write_text("\ufeff" + "\n".join(zeilen) + "\n", encoding="utf-8")
    _abruf("ladesaeulen", [name], "cc-by-4.0", "ladesaeulenregister")

    # StadtLastenRad (GBFS station_information)
    punkte = _punkte_im_umriss(umriss, 6, rng)
    xs, ys = wgs(punkte)
    stationen = [{"station_id": str(50000 + i), "name": f"Teststation {i + 1} StadtLastenRad", "short_name": str(7500 + i),
                  "lat": y, "lon": x, "region_id": "133", "is_virtual_station": False} for i, (x, y) in enumerate(zip(xs, ys, strict=True))]
    ordner = pfade.roh("nextbike-essen")
    ordner.mkdir(parents=True)
    (ordner / "nextbike_essen_stationen.json").write_text(json.dumps(
        {"last_updated": 1791662851, "ttl": 60, "data": {"stations": stationen}, "version": "2.3"}), encoding="utf-8")
    _abruf("nextbike-essen", ["nextbike_essen_stationen.json"], "cc0-1.0", "nextbike")

    # Pegel (Pegelonline): zwei in der Box um Essen, einer weit außerhalb
    pegel = [("TESTPEGEL RUHR", "RUHR", 7.01, 51.40), ("TESTSCHLEUSE OW", "RHEIN-HERNE-KANAL", 7.0, 51.50),
             ("WEIT WEG", "RHEIN", 6.5, 51.9)]
    eintraege = [{"uuid": f"test-{i}", "number": str(1000 + i), "shortname": kurz, "longname": kurz, "km": 1.0,
                  "agency": "TEST", "longitude": lon, "latitude": lat,
                  "water": {"shortname": gewaesser[:3], "longname": gewaesser},
                  "timeseries": [{"shortname": "W", "longname": "WASSERSTAND ROHDATEN", "unit": "cm",
                                  "equidistance": 15, "currentMeasurement": {"timestamp": "2026-10-10T12:00:00+02:00",
                                                                             "value": 200 + i}}]}
                 for i, (kurz, gewaesser, lon, lat) in enumerate(pegel)]
    ordner = pfade.roh("pegel-essen")
    ordner.mkdir(parents=True)
    (ordner / "pegel_essen.json").write_text(json.dumps(eintraege, ensure_ascii=False), encoding="utf-8")
    _abruf("pegel-essen", ["pegel_essen.json"], "dl-de-zero-2.0", "pegel")

    # Umweltzone: drei getrennte Flächen in WGS84, die große mit einem Loch (wie im Original mit Aussparungen)
    mitte = umriss.centroid
    gross = umriss.buffer(-1500).difference(mitte.buffer(800))
    klein = [Point(mitte.x - 300, umriss.bounds[3] - 500).buffer(250), Point(mitte.x + 400, umriss.bounds[3] - 500).buffer(150)]
    flaechen = [klein[0], klein[1], gross]
    gdf = gpd.GeoDataFrame({"FID": [0, 1, 2], "OBJECTID": [1, 2, 3], "ID": [0, 0, 0],
                            "SHAPE_AREA": [f.area for f in flaechen], "SHAPE_LEN": [f.length for f in flaechen]},
                           geometry=flaechen, crs="EPSG:25832").to_crs("EPSG:4326")
    ordner = pfade.roh("umweltzone")
    ordner.mkdir(parents=True)
    gdf.to_file(ordner / "Umweltzone_Essen_0.geojson", driver="GeoJSON")
    _abruf("umweltzone", ["Umweltzone_Essen_0.geojson"], "dl-de-by-2.0", "essen-opendata")


def _haushalte(anzahl_gebiete: int) -> None:
    """Privathaushalte je Stadtteil und Jahr: Semikolon, Windows-1252 (Umlaut im Namen), Spalten wie im Original.

    Gebiet 1 wird von Jahr zu Jahr kinderreicher, die letzte Nummer fehlt (wie eine Lücke in der Quelle)."""
    kopf = ("Stadtbezirk;Stadtteil;Stadtteilname;Jahr;INSGESAMT;HH_EINE_PERSON;HH_EINE_PERSON_25B69;HH_MIT_KINDERN;"
            "HH_MIT_3OM_KINDERN;HH_ALLEINERZIEHEND;BEVOELKERUNG_IN_HH")
    zeilen = [kopf]
    for jahr in range(2007, 2026):
        for nr in range(1, anzahl_gebiete):
            haushalte = 1000 + 100 * nr
            kinder = 100 + 10 * (jahr - 2007) if nr == 1 else 150 + 5 * nr
            eine = 400 + 20 * nr
            zeilen.append(f"{nr % 9 + 1};{nr};Testgebiet {nr:02d} (erfunden, Größe);{jahr};{haushalte};{eine};"
                          f"{eine // 2};{kinder};{kinder // 5};{kinder // 4};{2 * haushalte - 100}")
    ordner = pfade.roh("privathaushalte-stadtteile")
    ordner.mkdir(parents=True)
    name = "Anzahl der Privathaushalte in den Stadtteilen ab 2007_3.csv"
    (ordner / name).write_text("\n".join(zeilen) + "\n", encoding="cp1252")
    _abruf("privathaushalte-stadtteile", [name], "dl-de-by-2.0", "essen-opendata")
