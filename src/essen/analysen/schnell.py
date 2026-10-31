"""Schnellanalyse: einen beliebigen geladenen Vektordatensatz auf die Stadtteile verteilen.

Punkte werden gezählt (je Stadtteil und je km²), Flächen als Anteil der Stadtteilfläche,
Linien als Länge je km². Gut für einen ersten Blick auf neue Daten, bevor es eine eigene
Analyse gibt.
"""

from __future__ import annotations

from collections.abc import Callable

import geopandas as gpd
import pyogrio

from .. import kennzahlen
from ..geo import ZIEL_CRS, lade_stadtteile, lies_im_stadtgebiet, vektordatei
from ..katalog import Katalog
from ..text import zahl
from .basis import Ergebnis, Spalte, Stufen


def layer_liste(kennung: str) -> list[tuple[str, str]]:
    return [(name, str(typ)) for name, typ in pyogrio.list_layers(vektordatei(kennung)) if typ]


def verteile(katalog: Katalog, kennung: str, layer: str | None = None,
             melde: Callable[[str], None] = print) -> Ergebnis:
    stadtteile = lade_stadtteile(katalog)
    pfad = vektordatei(kennung)
    vorhanden = [name for name, _ in layer_liste(kennung)]
    if not vorhanden:
        raise ValueError(f"In {pfad.name} gibt es keinen Layer mit Geometrie.")
    if layer and layer not in vorhanden:
        raise ValueError(f"Layer {layer} gibt es nicht. Vorhanden: {', '.join(vorhanden)}")
    layer = layer or vorhanden[0]
    daten = lies_im_stadtgebiet(pfad, layer=layer)
    if daten.empty:
        raise ValueError(f"Im Layer {layer} liegen keine Objekte im Stadtgebiet.")
    arten = daten.geom_type.str.replace("Multi", "")
    typ = arten.mode().iloc[0]
    hinweise = list()
    if (arten != typ).any():
        hinweise.append(f"{zahl(int((arten != typ).sum()))} Objekte anderer Geometrieart übergangen, gezählt wird {typ}.")
        daten = daten[arten == typ]
    melde(f"{zahl(len(daten))} Objekte ({typ}) aus {pfad.name}, Layer {layer}")
    gebiete = stadtteile.gdf
    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"})
    km2 = tabelle["flaeche_ha"] / 100
    if typ == "Point":
        anzahl = kennzahlen.punkte_je_gebiet(gebiete, daten)
        tabelle["anzahl"] = tabelle["gebiet_id"].map(anzahl).fillna(0).astype(int)
        tabelle["je_km2"] = (tabelle["anzahl"] / km2).round(2)
        kennzahl, text = "je_km2", f"{zahl(tabelle['anzahl'].sum())} Objekte in {zahl((tabelle['anzahl'] > 0).sum())} Stadtteilen"
    elif typ == "Polygon":
        bedeckt = kennzahlen.flaechenanteil_je_gebiet(gebiete, daten)
        tabelle["bedeckt_ha"] = tabelle["gebiet_id"].map(bedeckt["bedeckt_ha"]).round(1)
        tabelle["anteil_pct"] = tabelle["gebiet_id"].map(bedeckt["anteil_pct"]).round(1)
        gesamt = 100 * tabelle["bedeckt_ha"].sum() / tabelle["flaeche_ha"].sum()
        kennzahl, text = "anteil_pct", f"Die Flächen bedecken {zahl(gesamt, 1)} % des Stadtgebiets"
    elif typ == "LineString":
        laenge = kennzahlen.laenge_je_gebiet(gebiete, daten)
        tabelle["laenge_km"] = (tabelle["gebiet_id"].map(laenge) / 1000).round(2)
        tabelle["km_je_km2"] = (tabelle["laenge_km"] / km2).round(2)
        kennzahl, text = "km_je_km2", f"{zahl(tabelle['laenge_km'].sum(), 1)} km Linien im Stadtgebiet"
    else:
        raise ValueError(f"Geometrieart {typ} wird noch nicht unterstützt.")
    tabelle["flaeche_ha"] = tabelle["flaeche_ha"].round(1)
    melde(text)
    geometrie = gpd.GeoDataFrame(gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id"),
                                 geometry="geometry", crs=ZIEL_CRS)
    return Ergebnis(
        analyse_id=f"schnell-{kennung}",
        tabelle=tabelle,
        geometrie=geometrie,
        kennzahl_text=text,
        quellen=[stadtteile.datensatz, kennung],
        parameter={"datensatz": kennung, "layer": layer, "kennzahl": kennzahl, "geometrie": typ},
        hinweise=stadtteile.hinweise + hinweise,
    )


KENNZAHL_TITEL = {"je_km2": "Anzahl je km²", "anteil_pct": "bedeckter Anteil in %", "km_je_km2": "km je km²"}
SPALTEN_TITEL = {"stadtteil": "Stadtteil", "stadtteil_nr": "Nr.", "flaeche_ha": "Fläche (ha)", "anzahl": "Anzahl",
                 "je_km2": "je km²", "bedeckt_ha": "bedeckt (ha)", "anteil_pct": "Anteil (%)",
                 "laenge_km": "Länge (km)", "km_je_km2": "km je km²"}


def stufen_fuer(ergebnis: Ergebnis) -> Stufen:
    """Farbstufen nach Quintilen der Kennzahl; die Farben gleichmäßig über die neutrale Folge verteilt."""
    import numpy as np

    from ..farben import FARBSTUFEN

    werte = ergebnis.tabelle[ergebnis.parameter["kennzahl"]].dropna()
    grenzen = tuple(float(x) for x in np.unique(np.quantile(werte, [0, 0.2, 0.4, 0.6, 0.8]))) if len(werte) else (0.0,)
    folge = FARBSTUFEN["neutral"]
    farben = tuple(folge[round(i)] for i in np.linspace(0, len(folge) - 1, len(grenzen)))
    return Stufen(grenzen=grenzen, farben=farben, texte=tuple(f"ab {zahl(g, 1)}" for g in grenzen))


def spalten_fuer(ergebnis: Ergebnis) -> tuple[Spalte, ...]:
    """Spalten für Karte und Tooltip: Stadtteil und die Kennzahl."""
    kennzahl = ergebnis.parameter["kennzahl"]
    return (Spalte("stadtteil", "Stadtteil", "text"), Spalte(kennzahl, KENNZAHL_TITEL[kennzahl], "zahl", stellen=1))
