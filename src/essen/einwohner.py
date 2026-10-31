"""Einwohner aus dem Zensus-2022-Gitter (100 m) für Essen: wie viele Menschen wohnen in belasteten Flächen?

Annahme: Die Einwohner einer 100-m-Zelle sind gleichmäßig über die Zelle verteilt. Eine Zelle gehört zu dem
Stadtteil, in dem ihr Mittelpunkt liegt. Liegt ein Teil der Zelle in einer belasteten Fläche, zählt derselbe
Anteil ihrer Einwohner als belastet. Das ist eine Schätzung; Zellen ohne Einwohner fehlen in der Datei.

Die Zellen im Rechteck um Essen werden einmal aus der bundesweiten CSV gelesen und unter
data/processed/_einwohner/ zwischengespeichert.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer

from . import laden, pfade
from .geo import ZIEL_CRS, essen_bbox

DATENSATZ = "zensus-2022-gitter"
GITTER_CRS = "EPSG:3035"
KANTE_M = 100.0
DATEI = "Zensus2022_Bevoelkerungszahl_100m-Gitter.csv"
MIN_EINWOHNER = 200  # darunter kein Anteil je Stadtteil (zu wenige Menschen für einen belastbaren Anteil)
HINWEIS = ("Einwohner: Zensus 2022 (Stichtag 15.05.2022), 100-m-Gitter, Schätzung mit gleichmäßiger Verteilung in "
           "der Zelle; Zellen gehören zu dem Stadtteil, in dem ihr Mittelpunkt liegt.")


def vorhanden() -> bool:
    return laden.vorhanden(DATENSATZ)


def _csv():
    treffer = [p for p in laden.entpackt(DATENSATZ) if p.name == DATEI]
    if not treffer:
        raise FileNotFoundError(f"{DATEI} fehlt im Datensatz {DATENSATZ}. Neu laden: uv run essen laden {DATENSATZ} --neu")
    return treffer[0]


def zellen() -> gpd.GeoDataFrame:
    """100-m-Zellen mit Einwohnern im Rechteck um Essen als Quadrate in EPSG:3035 (Spalten gitter_id, einwohner)."""
    abruf = laden.lese_abruf(DATENSATZ)
    kennung = (next(iter(abruf.sha256.values()), "") if abruf and abruf.sha256 else abruf.zeit if abruf else "")[:16]
    zwischen = pfade.verarbeitet("_einwohner") / f"gitter_essen_{kennung.replace(':', '')}.csv"
    if zwischen.exists():
        tabelle = pd.read_csv(zwischen)
    else:
        x1, y1, x2, y2 = essen_bbox(GITTER_CRS)
        teile = []
        for teil in pd.read_csv(_csv(), sep=";", chunksize=500_000, dtype={"Einwohner": str}):
            teile.append(teil[teil["x_mp_100m"].between(x1 - KANTE_M, x2 + KANTE_M)
                              & teil["y_mp_100m"].between(y1 - KANTE_M, y2 + KANTE_M)])
        tabelle = pd.concat(teile, ignore_index=True)
        werte = pd.to_numeric(tabelle["Einwohner"], errors="coerce")
        if werte.isna().any():  # Sonderzeichen laut Datensatzbeschreibung möglich, in Essen bisher nicht
            raise ValueError(f"{DATEI}: {int(werte.isna().sum())} Zellen ohne Zahl "
                             f"({', '.join(sorted(set(tabelle['Einwohner'][werte.isna()]))[:5])}).")
        tabelle = pd.DataFrame({"gitter_id": tabelle.iloc[:, 0], "x": tabelle["x_mp_100m"], "y": tabelle["y_mp_100m"],
                                "einwohner": werte.astype(int)})
        zwischen.parent.mkdir(parents=True, exist_ok=True)
        for alt in zwischen.parent.glob("gitter_essen_*.csv"):
            alt.unlink()
        tabelle.to_csv(zwischen, index=False)
    halb = KANTE_M / 2
    geometrie = shapely.box(tabelle["x"] - halb, tabelle["y"] - halb, tabelle["x"] + halb, tabelle["y"] + halb)
    return gpd.GeoDataFrame(tabelle[["gitter_id", "einwohner"]], geometry=geometrie, crs=GITTER_CRS)


def zellen_je_gebiet(gebiete: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Zellen mit Mittelpunkt in einem Gebiet, mit gebiet_id, als Polygone in EPSG:25832."""
    z = zellen()
    mitte = gpd.GeoDataFrame(z[["gitter_id"]], geometry=z.geometry.centroid, crs=GITTER_CRS).to_crs(ZIEL_CRS)
    treffer = gpd.sjoin(mitte, gebiete[["gebiet_id", "geometry"]].to_crs(ZIEL_CRS), predicate="within")
    treffer = treffer.drop_duplicates("gitter_id")[["gitter_id", "gebiet_id"]]
    return z.merge(treffer, on="gitter_id").to_crs(ZIEL_CRS)


def in_flaeche(gebiete: gpd.GeoDataFrame, belastet) -> pd.DataFrame:
    """Je Gebiet: einwohner und einwohner_belastet (Anteil der Zellfläche in den belasteten Flächen).

    `belastet` ist eine Geometrie in EPSG:25832 oder ein GeoDataFrame mit überschneidungsfreien Flächen."""
    z = zellen_je_gebiet(gebiete)
    if belastet is None or (not isinstance(belastet, gpd.GeoDataFrame) and shapely.is_empty(belastet)):
        anteil = np.zeros(len(z))
    elif isinstance(belastet, gpd.GeoDataFrame):
        teile = belastet[["geometry"]].to_crs(ZIEL_CRS)
        schnitt = gpd.overlay(z[["gitter_id", "geometry"]], teile, how="intersection", keep_geom_type=True)
        flaeche = schnitt.area.groupby(schnitt["gitter_id"]).sum()
        anteil = (flaeche.reindex(z["gitter_id"]).fillna(0.0).to_numpy() / z.area.to_numpy()).clip(max=1.0)
    else:
        shapely.prepare(belastet)
        anteil = shapely.area(shapely.intersection(z.geometry.values, belastet)) / shapely.area(z.geometry.values)
    return _summen(gebiete, z.assign(anteil=anteil))


def in_rastermaske(gebiete: gpd.GeoDataFrame, maske: np.ndarray, transform, crs) -> pd.DataFrame:
    """Wie in_flaeche, aber belastet ist eine Rastermaske (True je Rasterzelle). Anteil je 100-m-Zelle = Anteil
    der Rasterzellen, deren Mittelpunkt in der Zelle liegt und die belastet sind."""
    z = zellen_je_gebiet(gebiete)
    zeilen, spalten = np.nonzero(np.ones_like(maske, dtype=bool))
    xs, ys = transform @ (spalten + 0.5, zeilen + 0.5)
    gx, gy = Transformer.from_crs(crs, GITTER_CRS, always_xy=True).transform(xs, ys)
    schluessel = pd.Series(np.floor(np.asarray(gx) / KANTE_M).astype(np.int64) * 10_000_000
                           + np.floor(np.asarray(gy) / KANTE_M).astype(np.int64))
    zaehlung = pd.DataFrame({"k": schluessel, "b": maske.ravel().astype(int)}).groupby("k")["b"].agg(["sum", "count"])
    mitte = z.to_crs(GITTER_CRS).geometry.centroid
    k = np.floor(mitte.x / KANTE_M).astype(np.int64) * 10_000_000 + np.floor(mitte.y / KANTE_M).astype(np.int64)
    treffer = zaehlung.reindex(k.to_numpy())
    anteil = (treffer["sum"] / treffer["count"]).fillna(0.0).to_numpy()
    return _summen(gebiete, z.assign(anteil=anteil))


def _summen(gebiete: gpd.GeoDataFrame, z: pd.DataFrame) -> pd.DataFrame:
    z = z.assign(belastet=z["einwohner"] * z["anteil"])
    summe = z.groupby("gebiet_id")[["einwohner", "belastet"]].sum()
    ergebnis = summe.reindex(gebiete["gebiet_id"]).fillna(0.0).rename(columns={"belastet": "einwohner_belastet"})
    ergebnis["anteil_einwohner_pct"] = (100 * ergebnis["einwohner_belastet"] / ergebnis["einwohner"]).where(
        ergebnis["einwohner"] >= MIN_EINWOHNER)
    ergebnis["einwohner"] = ergebnis["einwohner"].round().astype(int)
    ergebnis["einwohner_belastet"] = ergebnis["einwohner_belastet"].round().astype(int)
    return ergebnis


def ergaenze(tabelle: pd.DataFrame, je_gebiet: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Hängt einwohner, einwohner_belastet und anteil_einwohner_pct an eine Ergebnistabelle (mit gebiet_id) und
    gibt einen Satz für die Stadt zurück."""
    je_gebiet = je_gebiet.reset_index()
    je_gebiet["gebiet_id"] = je_gebiet["gebiet_id"].astype(str)
    tabelle = tabelle.assign(gebiet_id=tabelle["gebiet_id"].astype(str)).merge(je_gebiet, on="gebiet_id", how="left")
    tabelle["anteil_einwohner_pct"] = tabelle["anteil_einwohner_pct"].round(1)
    gesamt, belastet = int(tabelle["einwohner"].sum()), int(tabelle["einwohner_belastet"].sum())
    from .text import zahl
    anteil = 100 * belastet / gesamt if gesamt else float("nan")
    return tabelle, f"Geschätzt {zahl(round(belastet, -2))} von {zahl(gesamt)} Einwohnern ({zahl(anteil, 1)} %)."
