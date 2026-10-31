"""Allgemeine Kennzahlen je Gebiet: Flächen nach Klassen (Vektor und Raster), Zählungen, Anteile.

Alle Funktionen erwarten Gebiete mit der Spalte gebiet_id (siehe geo.Gebiete) und rechnen
Flächen in EPSG:25832. Sie wissen nichts über ein bestimmtes Thema; die Analysen in
essen/analysen/ bauen darauf auf.
"""

from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .geo import ZIEL_CRS
from .text import zahl


def _gebiete_utm(gebiete: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if "gebiet_id" not in gebiete.columns:
        raise ValueError("Gebiete brauchen die Spalte gebiet_id.")
    return gebiete[["gebiet_id", "geometry"]].to_crs(ZIEL_CRS)


def gueltig(geometrien: gpd.GeoSeries) -> gpd.GeoSeries:
    """make_valid wie bisher; nur Geometrien, an denen GEOS dabei scheitert („mixed-dimension“), werden mit dem
    Verfahren „structure“ repariert (vorgekommen bei 11 Flächen der Planungshinweiskarte in Essen). Was dabei zu
    Linien oder Punkten zusammenfällt, wird leer: Es hat keine Fläche und würde das Verschneiden stören."""
    try:
        repariert = geometrien.make_valid()
    except shapely.errors.GEOSException:
        werte = []
        for g in geometrien:
            try:
                werte.append(shapely.make_valid(g))
            except shapely.errors.GEOSException:
                werte.append(shapely.make_valid(g, method="structure", keep_collapsed=False))
        repariert = gpd.GeoSeries(werte, index=geometrien.index, crs=geometrien.crs)
    andere = ~repariert.geom_type.isin(["Polygon", "MultiPolygon"]) & repariert.notna()
    if andere.any():
        def nur_flaechen(g):
            teile = [t for t in shapely.get_parts(g) if t.geom_type in ("Polygon", "MultiPolygon")]
            return shapely.union_all(teile) if teile else shapely.Polygon()
        repariert = repariert.copy()
        repariert[andere] = [nur_flaechen(g) for g in repariert[andere]]
    return repariert


def flaechen_nach_klasse(gebiete: gpd.GeoDataFrame, flaechen: gpd.GeoDataFrame, klassen: list,
                         spalte: str = "klasse") -> pd.DataFrame:
    """Fläche in m² je Gebiet und Klasse aus Vektorflächen. Zeilen: gebiet_id, Spalten: klassen.

    Flächen, die ganz in einem Gebiet liegen, zählen direkt; nur die übrigen werden verschnitten. Das spart bei
    vielen kleinen Flächen (etwa 548.000 in der Starkregenkarte) fast die ganze Rechenzeit.
    """
    teile = flaechen[[spalte, "geometry"]].to_crs(ZIEL_CRS).reset_index(drop=True)
    teile["geometry"] = gueltig(teile.geometry)
    utm = _gebiete_utm(gebiete).reset_index(drop=True)
    innen, gebiet = utm.sindex.query(teile.geometry, predicate="within")
    direkt = pd.DataFrame({"gebiet_id": utm["gebiet_id"].to_numpy()[gebiet], spalte: teile[spalte].to_numpy()[innen],
                           "m2": teile.geometry.iloc[innen].area.to_numpy()})
    rest = teile.drop(index=np.unique(innen))
    schnitt = gpd.overlay(rest, utm, how="intersection", keep_geom_type=True) if len(rest) else rest.iloc[:0]
    zusammen = pd.concat([direkt, pd.DataFrame({"gebiet_id": schnitt.get("gebiet_id", pd.Series(dtype=object)),
                                                spalte: schnitt[spalte], "m2": schnitt.area})], ignore_index=True)
    if zusammen.empty:
        return pd.DataFrame(0.0, index=gebiete["gebiet_id"], columns=klassen)
    tabelle = zusammen.pivot_table(index="gebiet_id", columns=spalte, values="m2", aggfunc="sum", fill_value=0.0)
    return tabelle.reindex(index=gebiete["gebiet_id"], columns=klassen, fill_value=0.0).fillna(0.0)


def schnitt_mit(flaechen: gpd.GeoDataFrame, maske) -> gpd.GeoDataFrame:
    """Die Teile der Flächen, die in der Maske liegen (eine Geometrie in ZIEL_CRS), mit allen übrigen Spalten.

    Nur Flächen, die die Maske berühren, werden verschnitten; das hält es bei vielen kleinen Flächen schnell."""
    teile = flaechen.to_crs(ZIEL_CRS).reset_index(drop=True)
    if maske is None or maske.is_empty or teile.empty:
        return teile.iloc[:0]
    kandidaten = teile.iloc[np.unique(teile.sindex.query(maske, predicate="intersects"))].copy()
    kandidaten["geometry"] = kandidaten.geometry.make_valid().intersection(maske)
    return kandidaten[~kandidaten.geometry.is_empty & (kandidaten.geometry.area > 0)]


def ohne(flaechen: gpd.GeoDataFrame, maske) -> gpd.GeoDataFrame:
    """Die Flächen ohne die Teile, die in der Maske liegen (Gegenstück zu schnitt_mit)."""
    teile = flaechen.to_crs(ZIEL_CRS).reset_index(drop=True)
    if maske is None or maske.is_empty or teile.empty:
        return teile
    beruehrt = np.unique(teile.sindex.query(maske, predicate="intersects"))
    teile["geometry"] = teile.geometry.make_valid()
    teile.loc[beruehrt, "geometry"] = teile.geometry.iloc[beruehrt].difference(maske).to_numpy()
    return teile[~teile.geometry.is_empty]


def flaechen_nach_klasse_raster(gebiete: gpd.GeoDataFrame, klassen_raster: np.ndarray, transform, crs,
                                klassen: list[int]) -> pd.DataFrame:
    """Fläche in m² je Gebiet und Klasse aus einem Klassenraster (0 = keine Klasse).

    Jede Zelle zählt zu dem Gebiet, in dem ihr Mittelpunkt liegt.
    """
    from rasterio.features import rasterize

    if klassen_raster.ndim != 2:
        raise ValueError("Erwartet ein zweidimensionales Klassenraster.")
    utm = gebiete[["gebiet_id", "geometry"]].to_crs(crs)
    index = rasterize(
        ((geometrie, nummer + 1) for nummer, geometrie in enumerate(utm.geometry)),
        out_shape=klassen_raster.shape, transform=transform, fill=0, dtype="int32", all_touched=False,
    )
    werte = np.asarray(klassen_raster).astype(np.int64)
    gueltig = (index > 0) & (werte > 0)
    hoechste = int(max(klassen + [int(werte.max()) if werte.size else 0]))
    codes = index[gueltig].astype(np.int64) * (hoechste + 1) + werte[gueltig]
    zaehlung = np.bincount(codes, minlength=(len(utm) + 1) * (hoechste + 1)).reshape(len(utm) + 1, hoechste + 1)
    zellflaeche = abs(transform.a * transform.e)
    tabelle = pd.DataFrame(zaehlung[1:, :] * zellflaeche, index=utm["gebiet_id"].to_numpy())
    tabelle.index.name = "gebiet_id"
    return tabelle.reindex(columns=klassen, fill_value=0.0)


def flaechen_nach_wert_rasterdatei(gebiete: gpd.GeoDataFrame, pfad, werte: list[int], band: int = 1,
                                   zeilen_je_streifen: int = 1024, melde=None) -> pd.DataFrame:
    """Fläche in m² je Gebiet und Rasterwert aus einer Ganzzahl-Rasterdatei, streifenweise gelesen.

    Für sehr große Raster (z. B. Versiegelung mit 0,5 m). Jede Zelle zählt zu dem Gebiet, in dem ihr
    Mittelpunkt liegt; Fehlwerte und Werte außerhalb von `werte` zählen nicht.
    """
    import rasterio
    from rasterio.windows import Window, from_bounds

    with rasterio.open(pfad) as r:
        utm = gebiete[["gebiet_id", "geometry"]].to_crs(r.crs)
        x1, y1, x2, y2 = utm.total_bounds
        roh = from_bounds(x1 - 100, y1 - 100, x2 + 100, y2 + 100, transform=r.transform)
        spalte0, zeile0 = max(0, math.floor(roh.col_off)), max(0, math.floor(roh.row_off))
        spalte1 = min(r.width, math.ceil(roh.col_off + roh.width))
        zeile1 = min(r.height, math.ceil(roh.row_off + roh.height))
        fenster = Window(spalte0, zeile0, spalte1 - spalte0, zeile1 - zeile0)
        summen = pd.DataFrame(0.0, index=utm["gebiet_id"].to_numpy(), columns=werte)
        summen.index.name = "gebiet_id"
        ende = fenster.row_off + fenster.height
        for start in range(int(fenster.row_off), int(ende), zeilen_je_streifen):
            streifen = Window(fenster.col_off, start, fenster.width, min(zeilen_je_streifen, ende - start))
            daten = r.read(band, window=streifen, masked=True)
            klassen = np.where(np.isin(daten.filled(0), werte) & ~np.ma.getmaskarray(daten),
                               daten.filled(0).astype(np.int64) + 1, 0)  # +1, damit der Wert 0 zählt
            teil = flaechen_nach_klasse_raster(gebiete, klassen, r.window_transform(streifen), r.crs,
                                               [w + 1 for w in werte])
            summen += teil.to_numpy()
            if melde:
                melde(f"  Zeilen bis {zahl(start + streifen.height - fenster.row_off)} von {zahl(fenster.height)}")
    return summen


def mittel_je_gebiet_rasterdatei(gebiete: gpd.GeoDataFrame, pfad, gueltig: tuple[float, float], band: int = 1
                                 ) -> pd.DataFrame:
    """Mittel eines stetigen Rasters je Gebiet (z. B. Versiegelungsgrad in %) und die Fläche mit gültigen Werten.

    Jede Zelle zählt zu dem Gebiet, in dem ihr Mittelpunkt liegt; alle Zellen sind gleich groß, das Mittel ist also
    flächengewichtet. Fehlwerte und Werte außerhalb von `gueltig` (einschließlich der Grenzen) zählen nicht.
    Gibt je gebiet_id die Spalten mittel und gueltig_ha zurück (Fläche in der Projektion des Rasters)."""
    import rasterio
    from rasterio.features import rasterize
    from rasterio.windows import Window, from_bounds

    with rasterio.open(pfad) as r:
        eigen = gebiete[["gebiet_id", "geometry"]].to_crs(r.crs).reset_index(drop=True)
        x1, y1, x2, y2 = eigen.total_bounds
        roh = from_bounds(x1, y1, x2, y2, transform=r.transform)
        spalte0, zeile0 = max(0, math.floor(roh.col_off)), max(0, math.floor(roh.row_off))
        spalte1 = min(r.width, math.ceil(roh.col_off + roh.width))
        zeile1 = min(r.height, math.ceil(roh.row_off + roh.height))
        fenster = Window(spalte0, zeile0, spalte1 - spalte0, zeile1 - zeile0)
        daten = r.read(band, window=fenster, masked=True).astype("float64")
        transform = r.window_transform(fenster)
        zelle_ha = abs(r.transform.a * r.transform.e) / 1e4
    nummern = rasterize(((g, i + 1) for i, g in enumerate(eigen.geometry)), out_shape=daten.shape,
                        transform=transform, fill=0, dtype="int32")  # Zellmitte im Gebiet (all_touched=False)
    werte = daten.filled(np.nan)
    ok = (nummern > 0) & np.isfinite(werte) & (werte >= gueltig[0]) & (werte <= gueltig[1])
    anzahl = np.bincount(nummern[ok], minlength=len(eigen) + 1)[1:]
    summe = np.bincount(nummern[ok], weights=werte[ok], minlength=len(eigen) + 1)[1:]
    with np.errstate(invalid="ignore", divide="ignore"):
        mittel = np.where(anzahl > 0, summe / anzahl, np.nan)
    return pd.DataFrame({"mittel": mittel, "gueltig_ha": anzahl * zelle_ha},
                        index=pd.Index(eigen["gebiet_id"], name="gebiet_id"))


def anteile(flaechen: pd.DataFrame) -> pd.DataFrame:
    """Anteile in Prozent der Zeilensumme. Zeilen ohne Fläche werden leer."""
    summe = flaechen.sum(axis=1)
    return flaechen.div(summe.where(summe > 0), axis=0) * 100


def mindestbezug(tabelle: pd.DataFrame, bezug_spalte: str, minimum: float, spalten: list[str],
                 hinweis: str) -> pd.DataFrame:
    """Setzt Kennzahlen leer, wenn die Bezugsfläche zu klein ist, und schreibt einen Hinweis."""
    tabelle = tabelle.copy()
    zu_klein = tabelle[bezug_spalte] < minimum
    tabelle.loc[zu_klein, spalten] = np.nan
    if "hinweis" not in tabelle.columns:
        tabelle["hinweis"] = ""
    tabelle.loc[zu_klein, "hinweis"] = hinweis
    return tabelle


def punkte_je_gebiet(gebiete: gpd.GeoDataFrame, punkte: gpd.GeoDataFrame) -> pd.Series:
    """Anzahl der Punkte je Gebiet."""
    treffer = gpd.sjoin(punkte[["geometry"]].to_crs(ZIEL_CRS), _gebiete_utm(gebiete), predicate="within", how="inner")
    return treffer.groupby("gebiet_id").size().reindex(gebiete["gebiet_id"], fill_value=0).rename("anzahl")


def flaechenanteil_je_gebiet(gebiete: gpd.GeoDataFrame, flaechen: gpd.GeoDataFrame) -> pd.DataFrame:
    """Wie viel der Gebietsfläche von den Flächen bedeckt ist (Überlappungen zählen einmal)."""
    gebiete_utm = _gebiete_utm(gebiete)
    vereinigt = gpd.GeoDataFrame(geometry=[flaechen.to_crs(ZIEL_CRS).geometry.make_valid().union_all()], crs=ZIEL_CRS)
    schnitt = gpd.overlay(gebiete_utm, vereinigt, how="intersection", keep_geom_type=True)
    bedeckt = schnitt.assign(m2=schnitt.area).groupby("gebiet_id")["m2"].sum()
    gesamt = gebiete_utm.set_index("gebiet_id").area
    tabelle = pd.DataFrame({"flaeche_ha": gesamt / 1e4, "bedeckt_ha": bedeckt.reindex(gesamt.index, fill_value=0.0) / 1e4})
    tabelle["anteil_pct"] = 100 * tabelle["bedeckt_ha"] / tabelle["flaeche_ha"]
    return tabelle


def laenge_je_gebiet(gebiete: gpd.GeoDataFrame, linien: gpd.GeoDataFrame) -> pd.Series:
    """Länge der Linien je Gebiet in Metern."""
    schnitt = gpd.overlay(linien[["geometry"]].to_crs(ZIEL_CRS), _gebiete_utm(gebiete), how="intersection",
                          keep_geom_type=True)
    return schnitt.assign(m=schnitt.length).groupby("gebiet_id")["m"].sum().reindex(gebiete["gebiet_id"], fill_value=0.0)


def gewichtetes_mittel(werte: pd.Series, gewichte: pd.Series) -> float | None:
    """Mittelwert über Gebiete, gewichtet z. B. mit der Bezugsfläche. Leere Werte zählen nicht."""
    gueltig = werte.notna() & gewichte.notna() & (gewichte > 0)
    if not gueltig.any():
        return None
    return float((werte[gueltig] * gewichte[gueltig]).sum() / gewichte[gueltig].sum())
