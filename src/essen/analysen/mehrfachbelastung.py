"""Mehrfachbelastung je Stadtteil (E-008).

Zählt, in wie vielen Themen ein Stadtteil im obersten Fünftel der Essener Stadtteile liegt. Themen und
Regel sind in docs/entscheidungen.md (E-008) festgelegt: Hitze in der Nacht, Lärm, Starkregen; keine
Gewichtung. Die Einzelergebnisse kommen aus den gespeicherten Analysen mit Standard-Einstellungen; fehlen
sie oder passen sie nicht mehr, werden sie neu gerechnet.

Methodik: docs/methodik/mehrfachbelastung.md
"""

from __future__ import annotations

import math

import geopandas as gpd
import pandas as pd

from .. import analysen as registry, einwohner
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, lade_stadtteile
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Spalte, Stufen, veraltet

THEMEN = {  # Analyse → Kurzname; Reihenfolge wie in E-008
    "hitze-nacht": "Hitze in der Nacht",
    "laerm": "Lärm",
    "starkregen": "Starkregen",
}
ANTEIL_OBEN = 0.2  # oberstes Fünftel

STUFEN = Stufen(
    grenzen=(0, 1, 2, 3),
    farben=FARBSTUFEN["waerme"][:4],
    texte=("in keinem Thema", "in einem Thema", "in zwei Themen", "in drei Themen"),
    keine_daten_text="keine Angabe",
)


def spalte(analyse_id: str) -> str:
    return analyse_id.replace("-", "_")


def oberstes_fuenftel(werte: pd.Series, anteil: float = ANTEIL_OBEN) -> pd.Series:
    """True für die Werte im obersten Anteil (Gleichstand an der Grenze zählt mit), NaN bleibt NaN."""
    gueltig = werte.dropna()
    if gueltig.empty:
        return pd.Series(pd.NA, index=werte.index, dtype="boolean")
    anzahl = max(1, math.ceil(anteil * len(gueltig)))
    grenze = gueltig.sort_values(ascending=False).iloc[anzahl - 1]
    return (werte >= grenze).astype("boolean").where(werte.notna(), pd.NA)


def einzelergebnis(kontext: Kontext, analyse_id: str) -> Ergebnis:
    """Gespeichertes Ergebnis mit Standard-Einstellungen, sonst neu gerechnet und gespeichert."""
    analyse = registry.hole(analyse_id)
    ergebnis = Ergebnis.laden(analyse_id)
    if ergebnis is None or veraltet(analyse, ergebnis, {}):
        kontext.melde(f"Rechne {analyse.titel} mit Standard-Einstellungen …")
        ergebnis = registry.ausfuehren(kontext.katalog, analyse_id, melde=lambda m: kontext.melde(f"  {m}"))
    else:
        kontext.melde(f"{analyse.titel}: gespeichertes Ergebnis vom {ergebnis.erstellt[:10]}")
    return ergebnis


def rechne(kontext: Kontext) -> Ergebnis:
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"})
    tabelle["gebiet_id"] = tabelle["gebiet_id"].astype(str)
    hinweise = list(stadtteile.hinweise)
    quellen = [stadtteile.datensatz]
    grenzen = []
    for analyse_id, name in THEMEN.items():
        analyse = registry.hole(analyse_id)
        ergebnis = einzelergebnis(kontext, analyse_id)
        werte = ergebnis.tabelle[["gebiet_id", analyse.kennzahl]].copy()
        werte["gebiet_id"] = werte["gebiet_id"].astype(str)
        werte = werte.rename(columns={analyse.kennzahl: f"{spalte(analyse_id)}_wert"})
        tabelle = tabelle.merge(werte, on="gebiet_id", how="left")
        oben = oberstes_fuenftel(tabelle[f"{spalte(analyse_id)}_wert"])
        tabelle[f"{spalte(analyse_id)}_oben"] = oben
        grenze = tabelle.loc[oben.fillna(False).astype(bool), f"{spalte(analyse_id)}_wert"].min()
        grenzen.append(f"{name}: ab {zahl(grenze, 1)} {analyse.einheit} ({analyse.kennzahl_titel}), "
                       f"{int(oben.fillna(False).sum())} Stadtteile")
        fehlen = int(oben.isna().sum())
        if fehlen:
            hinweise.append(f"{name}: {fehlen} Stadtteile ohne Wert, dort zählt das Thema nicht.")
        quellen += [q for q in ergebnis.quellen if q not in quellen]
    oben_spalten = [f"{spalte(a)}_oben" for a in THEMEN]
    oben = tabelle[oben_spalten].fillna(False).astype(bool)
    tabelle["anzahl_belastungen"] = oben.sum(axis=1)
    tabelle["themen_oben"] = oben.apply(lambda z: ", ".join(THEMEN[a] for a, wert in zip(THEMEN, z, strict=True) if wert), axis=1)
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_wert", "_ha"))})

    mindestens_zwei = int((tabelle["anzahl_belastungen"] >= 2).sum())
    alle = int((tabelle["anzahl_belastungen"] == len(THEMEN)).sum())
    text = (f"{mindestens_zwei} von {len(tabelle)} Stadtteilen liegen in mindestens zwei von {len(THEMEN)} Themen im "
            f"obersten Fünftel, {alle} in allen.")
    kontext.melde(text)
    if einwohner.vorhanden():
        kontext.melde("Einwohner je Stadtteil (Zensus-Gitter) …")
        je_gebiet = einwohner.in_flaeche(gebiete, None)["einwohner"].rename("einwohner").reset_index()
        je_gebiet["gebiet_id"] = je_gebiet["gebiet_id"].astype(str)
        tabelle = tabelle.merge(je_gebiet, on="gebiet_id", how="left")
        gesamt = int(tabelle["einwohner"].sum())
        betroffen = int(tabelle.loc[tabelle["anzahl_belastungen"] >= 2, "einwohner"].sum())
        hinweise.append(f"In den {mindestens_zwei} Stadtteilen mit mindestens zwei Themen wohnen geschätzt "
                        f"{zahl(round(betroffen, -2))} von {zahl(gesamt)} Einwohnern ({zahl(100 * betroffen / gesamt, 1)} %). "
                        "Das heißt nicht, dass alle diese Menschen selbst belastet sind (E-013). " + einwohner.HINWEIS)
    hinweise += [
        "Oberstes Fünftel heißt: unter den 20 % der Essener Stadtteile mit den höchsten Werten. Das ist ein Vergleich "
        "innerhalb Essens, kein Grenzwert. Grenzen: " + "; ".join(grenzen) + ".",
        "Themen nach E-008: Hitze in der Nacht, Lärm, Starkregen, ohne Gewichtung. Hitze am Tag, Versiegelung und "
        "Grünanteil zählen nicht, weil sie mit der Hitze in der Nacht eng zusammenhängen (Korrelation 0,8 bis 0,9).",
        "Alle Themen beziehen sich auf Fläche, nicht auf Einwohner (E-007). Grenzen und Alter der Einzeldaten "
        "stehen in den Methodik-Seiten der Analysen.",
    ]
    geometrie = gebiete[["gebiet_id", "geometry"]].assign(gebiet_id=lambda g: g["gebiet_id"].astype(str)).merge(
        tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=float(mindestens_zwei),
        kennzahl_text=text,
        hinweise=hinweise,
        quellen=quellen,
        parameter=dict(kontext.parameter),
    )


ANALYSE = Analyse(
    id="mehrfachbelastung",
    titel="Mehrfachbelastung je Stadtteil",
    frage="In wie vielen Themen (Hitze in der Nacht, Lärm, Starkregen) liegt ein Stadtteil im obersten Fünftel Essens?",
    themen=("klima", "laerm", "wasser"),
    benoetigt=("stadtteile", "klimaanalyse-nacht-raster", "laermkarte-essen", "starkregen-essen"),
    optional=("landbedeckung-nrw", einwohner.DATENSATZ),  # Landbedeckung: Gewässer beim Starkregen (E-017)
    rechne=rechne,
    kennzahl="anzahl_belastungen",
    kennzahl_titel="Zahl der Themen im obersten Fünftel",
    einheit="Themen",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anzahl_belastungen", "Themen im obersten Fünftel", "zahl"),
        Spalte("themen_oben", "welche", "text"),
        Spalte("hitze_nacht_wert", "Hitze Nacht (%)", "zahl", stellen=1),
        Spalte("laerm_wert", "Lärm (%)", "zahl", stellen=1),
        Spalte("starkregen_wert", "Starkregen (%)", "zahl", stellen=1),
        Spalte("einwohner", "Einwohner (geschätzt)", "zahl"),
    ),
    parameter=(),
    methodik="methodik/mehrfachbelastung.md",
    thema_titel="Mehrfachbelastung",
    kurz="In wie vielen der Themen Hitze in der Nacht, Lärm und Starkregen gehört ein Stadtteil zu den am stärksten belasteten in Essen?",
    richtung="hoch_schlecht",
    lesehilfe="Für jedes der drei Themen werden die zehn von 50 Stadtteilen mit den höchsten Werten markiert. Die Farbe zeigt, in wie vielen Themen ein Stadtteil dazugehört: von keinem (hell) bis allen dreien (dunkel).",
    grenzen_kurz=(
        "Ein Vergleich innerhalb Essens, kein Grenzwert: Zehn Stadtteile sind immer „oben“.",
        "Alle Themen zählen gleich viel.",
        "Luft fehlt, weil es dafür keine Werte je Stadtteil gibt.",
    ),
)
