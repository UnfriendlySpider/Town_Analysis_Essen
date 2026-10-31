"""Raumbezug: Stadtteile, Stadtgebiet und Koordinatensysteme.

Flächen werden immer in EPSG:25832 (ETRS89 / UTM 32N) gerechnet, Karten in EPSG:4326.
"""

from __future__ import annotations

import math
import re
import warnings
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
import shapely
from pyproj import Transformer

from . import laden
from .katalog import Katalog
from .text import norm

ZIEL_CRS = "EPSG:25832"
WEB_CRS = "EPSG:4326"
ESSEN_BBOX_WGS84 = (6.87, 51.34, 7.15, 51.54)  # großzügig um das Stadtgebiet
STADTTEILE_ID = "stadtteile"
ANZAHL_STADTTEILE = 50
TECHNISCHE_KENNUNGEN = {"fid", "objectid", "oid", "id", "gid", "ogc_fid", "globalid", "uuid", "shape_id", "fid_"}
VEKTOR_ENDUNGEN = (".gpkg", ".shp", ".geojson", ".fgb", ".gml", ".kml", ".sqlite", ".json")  # Reihenfolge = Vorrang
RASTER_ENDUNGEN = (".tif", ".tiff", ".vrt", ".asc", ".img", ".jp2")


class DatenFehlen(RuntimeError):
    """Benötigte Daten sind noch nicht geladen. `fehlend` nennt die Datensatz-IDs."""

    def __init__(self, fehlend: list[str], nachricht: str | None = None):
        self.fehlend = list(fehlend)
        super().__init__(nachricht or (
            "Diese Daten fehlen noch: " + ", ".join(self.fehlend)
            + ". In der App unter Datenkatalog laden oder: uv run essen laden " + " ".join(self.fehlend)
        ))


def essen_bbox(crs: str = ZIEL_CRS) -> tuple[float, float, float, float]:
    """Rechteck um das Stadtgebiet im gewünschten Koordinatensystem."""
    x1, y1, x2, y2 = ESSEN_BBOX_WGS84
    if crs in (WEB_CRS, "EPSG:4326"):
        return x1, y1, x2, y2
    umrechnung = Transformer.from_crs(WEB_CRS, crs, always_xy=True)
    xs, ys = umrechnung.transform([x1, x1, x2, x2], [y1, y2, y1, y2])
    return min(xs), min(ys), max(xs), max(ys)


@dataclass
class Gebiete:
    """Bezugsflächen einer Auswertung, meist die 50 Stadtteile.

    `gdf` hat die Spalten gebiet_id (Text), name, nummer (oder leer), flaeche_ha und geometry in EPSG:25832.
    """

    gdf: gpd.GeoDataFrame
    name_feld: str
    nummer_feld: str | None
    datensatz: str
    hinweise: list[str]

    @property
    def anzahl(self) -> int:
        return len(self.gdf)


def felder_erkennen(gdf: gpd.GeoDataFrame, vorgabe: dict | None = None) -> tuple[str, str | None, list[str]]:
    """Findet die Spalten für Name und Nummer. Technische Kennungen (FID, OBJECTID …) zählen nicht als Nummer."""
    vorgabe = vorgabe or {}
    hinweise: list[str] = []
    anzahl = len(gdf)
    name_kandidaten, nummer_kandidaten = [], []
    for spalte in gdf.columns:
        if spalte == gdf.geometry.name:
            continue
        werte = gdf[spalte].dropna()
        if anzahl == 0 or werte.nunique() < 0.9 * anzahl:
            continue
        schluessel = norm(spalte)
        technisch = schluessel in TECHNISCHE_KENNUNGEN
        if pd.api.types.is_numeric_dtype(werte):
            if (werte == werte.round()).all() and werte.max() <= 1000 and not technisch:
                bonus = 1 if any(s in schluessel for s in ("nr", "num", "schl", "nummer")) else 0
                nummer_kandidaten.append((bonus, -float(werte.max()), spalte))
        else:
            texte = werte.astype(str).str.strip()
            if texte.str.fullmatch(r"\{?[0-9a-fA-F-]{32,38}\}?").mean() > 0.5:
                continue
            if texte.str.fullmatch(r"\d+").mean() > 0.9:
                if not technisch:
                    bonus = 1 if any(s in schluessel for s in ("nr", "num", "schl", "nummer")) else 0
                    hoechste = pd.to_numeric(texte, errors="coerce").max()
                    if pd.notna(hoechste) and texte.str.fullmatch(r"\d+").all():
                        nummer_kandidaten.append((bonus, -float(hoechste), spalte))
            elif texte.str.contains(r"[A-Za-zÄÖÜäöüß]{3}").mean() > 0.9:
                bonus = 1 if any(s in schluessel for s in ("name", "bez", "stt", "stadtteil")) else 0
                name_kandidaten.append((bonus, texte.str.len().mean(), spalte))
    name = vorgabe.get("name")
    if name and name not in gdf.columns:
        hinweise.append(f"Namensfeld {name} aus dem Katalog fehlt in der Datei, suche selbst.")
        name = None
    if not name:
        if not name_kandidaten:
            raise ValueError("Keine Namensspalte gefunden. Spalten: " + ", ".join(map(str, gdf.columns)))
        name = sorted(name_kandidaten, reverse=True)[0][2]
    nummer = vorgabe.get("nummer")
    if nummer and nummer not in gdf.columns:
        hinweise.append(f"Nummernfeld {nummer} aus dem Katalog fehlt in der Datei.")
        nummer = None
    if not nummer and nummer_kandidaten:
        nummer = sorted(nummer_kandidaten, reverse=True)[0][2]
        hinweise.append(f"Stadtteilnummer aus Feld {nummer} geraten. Bitte prüfen und im Katalog unter felder.nummer eintragen.")
    return name, nummer, hinweise


def ist_geojson(pfad: Path) -> bool:
    """.geojson gilt immer als GeoJSON; bei .json wird im Anfang der Datei nach dem GeoJSON-Typ gesucht."""
    if Path(pfad).suffix.lower() == ".geojson":
        return True
    try:
        with open(pfad, encoding="utf-8", errors="replace") as datei:
            anfang = datei.read(65536)
    except OSError:
        return False
    return re.search(r'"type"\s*:\s*"Feature(Collection)?"', anfang) is not None


def _ist_vektor(pfad: Path) -> bool:
    endung = pfad.suffix.lower()
    if endung in (".json", ".geojson"):
        return ist_geojson(pfad)
    return endung in VEKTOR_ENDUNGEN


def hat_vektordaten(datensatz_id: str) -> bool:
    """Schneller Blick ohne Entpacken: liegt eine Vektordatei im Datensatz oder in einem seiner ZIPs?"""
    import zipfile

    if not laden.vorhanden(datensatz_id):
        return False
    for pfad in laden.dateien(datensatz_id):
        if pfad.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(pfad) as zf:
                    if any(Path(n).suffix.lower() in VEKTOR_ENDUNGEN[:-1] for n in zf.namelist()):
                        return True
            except zipfile.BadZipFile:
                continue
        elif _ist_vektor(pfad):
            return True
    return False


def gdb_ordner(dateien: list[Path]) -> list[Path]:
    """File-Geodatabases: Ordner mit der Endung .gdb, in denen die Dateien liegen (GDAL liest den Ordner)."""
    return sorted({eltern for p in dateien for eltern in Path(p).parents if eltern.suffix.lower() == ".gdb"})


def vektordatei(datensatz_id: str) -> Path:
    """Die Vektordatei eines geladenen Datensatzes (entpackt ZIPs bei Bedarf); auch ein .gdb-Ordner."""
    if not laden.vorhanden(datensatz_id):
        raise DatenFehlen([datensatz_id])
    dateien = laden.entpackt(datensatz_id)
    kandidaten = [p for p in dateien if _ist_vektor(p) and not gdb_ordner([p])]
    if not kandidaten and gdb_ordner(dateien):
        return gdb_ordner(dateien)[0]
    if not kandidaten:
        raise FileNotFoundError(f"Im Datensatz {datensatz_id} liegt keine Vektordatei ({', '.join(VEKTOR_ENDUNGEN)}).")
    return sorted(kandidaten, key=lambda p: (VEKTOR_ENDUNGEN.index(p.suffix.lower()), len(str(p))))[0]


def lies_vektor(pfad: Path, **kwargs) -> gpd.GeoDataFrame:
    """Liest eine Vektordatei, setzt fehlende Koordinatensysteme und vereinheitlicht die Geometriespalte."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*Measured \\(M\\) geometry types.*")
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")
        gdf = pyogrio.read_dataframe(pfad, **kwargs)
    if gdf.geometry.name != "geometry":
        gdf = gdf.rename_geometry("geometry")
    if gdf.geometry.has_z.any():  # Höhenwerte (oft nur 0) braucht keine Auswertung; gespeicherte Flächen werden kleiner
        gdf["geometry"] = gdf.geometry.force_2d()
    if gdf.crs is None:
        gdf = gdf.set_crs(WEB_CRS if Path(pfad).suffix.lower() in (".geojson", ".json") else ZIEL_CRS)
    return gdf


def lies_im_stadtgebiet(pfad: Path, layer: str | None = None, **kwargs) -> gpd.GeoDataFrame:
    """Liest nur Objekte im Rechteck um Essen, egal in welchem Koordinatensystem der Layer vorliegt."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        info = pyogrio.read_info(pfad, layer=layer)
    bbox = essen_bbox(info["crs"]) if info.get("crs") else None
    return lies_vektor(pfad, layer=layer, bbox=bbox, **kwargs)


def lade_stadtteile(katalog: Katalog) -> Gebiete:
    ds = katalog.datensatz(STADTTEILE_ID)
    gdf = lies_vektor(vektordatei(ds.id))
    name_feld, nummer_feld, hinweise = felder_erkennen(gdf, ds.felder)
    if len(gdf) != ANZAHL_STADTTEILE:
        hinweise.append(f"Die Datei hat {len(gdf)} Flächen, Essen hat {ANZAHL_STADTTEILE} Stadtteile.")
    gdf = gdf.to_crs(ZIEL_CRS)
    gdf["geometry"] = gdf.geometry.make_valid()
    ergebnis = gpd.GeoDataFrame(
        {
            "name": gdf[name_feld].astype(str).str.strip(),
            "nummer": pd.to_numeric(gdf[nummer_feld], errors="coerce").astype("Int64") if nummer_feld else pd.NA,
        },
        geometry=gdf.geometry,
        crs=ZIEL_CRS,
    )
    ergebnis["gebiet_id"] = (
        ergebnis["nummer"].astype(str) if nummer_feld else ergebnis["name"].map(_kennung)
    )
    if ergebnis["gebiet_id"].duplicated().any():
        ergebnis["gebiet_id"] = ergebnis["gebiet_id"] + "-" + ergebnis.groupby("gebiet_id").cumcount().astype(str)
        hinweise.append("Doppelte Namen oder Nummern in den Stadtteilgrenzen, Kennungen ergänzt.")
    ergebnis["flaeche_ha"] = ergebnis.area / 1e4
    ergebnis = ergebnis[["gebiet_id", "name", "nummer", "flaeche_ha", "geometry"]]
    ergebnis = ergebnis.sort_values(["nummer", "name"] if nummer_feld else ["name"]).reset_index(drop=True)
    return Gebiete(gdf=ergebnis, name_feld=name_feld, nummer_feld=nummer_feld, datensatz=ds.id, hinweise=hinweise)


def _kennung(name: str) -> str:
    return "".join(z if z.isalnum() else "-" for z in norm(name)).strip("-")


def fuer_karte(gdf: gpd.GeoDataFrame, toleranz_m: float = 3.0) -> gpd.GeoDataFrame:
    """Vereinfacht Flächen leicht und rechnet sie für Webkarten nach WGS84 um.

    Koordinaten werden auf 5 Nachkommastellen gerundet (rund 1 m): halb so viele Daten für den Browser."""
    vereinfacht = gdf.to_crs(ZIEL_CRS).copy()
    vereinfacht["geometry"] = vereinfacht.geometry.simplify(toleranz_m, preserve_topology=True)
    vereinfacht = vereinfacht.to_crs(WEB_CRS)
    vereinfacht["geometry"] = shapely.set_precision(vereinfacht.geometry.values, 1e-5)
    return vereinfacht


def lies_raster_fenster(pfad, gebiete: gpd.GeoDataFrame):
    """Liest den Ausschnitt eines Rasters um die Gebiete (100 m Rand), mit Skalierung.

    Gibt Daten (maskiert, Bänder × Zeilen × Spalten), Transformation, CRS, Farbtabelle und Datentypen zurück."""
    import rasterio
    from rasterio.windows import Window, from_bounds, transform as fenster_transform

    with rasterio.open(pfad) as r:
        crs = r.crs.to_string() if r.crs else ZIEL_CRS
        x1, y1, x2, y2 = gebiete.to_crs(crs).total_bounds
        roh = from_bounds(x1 - 100, y1 - 100, x2 + 100, y2 + 100, r.transform)
        spalte0, zeile0 = max(0, math.floor(roh.col_off)), max(0, math.floor(roh.row_off))
        spalte1 = min(r.width, math.ceil(roh.col_off + roh.width))
        zeile1 = min(r.height, math.ceil(roh.row_off + roh.height))
        if spalte1 <= spalte0 or zeile1 <= zeile0:
            raise ValueError("Das Raster deckt das Stadtgebiet nicht ab.")
        fenster = Window(spalte0, zeile0, spalte1 - spalte0, zeile1 - zeile0)
        daten = r.read(window=fenster, masked=True)
        skalen = [(r.scales[i] if r.scales else 1.0, r.offsets[i] if r.offsets else 0.0) for i in range(r.count)]
        if any(sv != (1.0, 0.0) for sv in skalen):  # z. B. Temperaturen als Ganzzahl mit Faktor 0,1
            daten = daten.astype("float32")
            for i, (skala, versatz) in enumerate(skalen):
                daten[i] = daten[i] * skala + versatz
        try:
            farbtabelle = r.colormap(1)
        except ValueError:
            farbtabelle = {}
        return daten, fenster_transform(fenster, r.transform), crs, farbtabelle, r.dtypes
