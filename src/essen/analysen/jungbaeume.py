"""Jungbäume der Stadt je Quadratkilometer und Stadtteil.

Grundlage ist der WFS „Stadtbäume Standorte“ der Stadt Essen, Ebene Stadtbaeume_Jungbaeume: Bäume, die die
Stadt seit 2008 gepflanzt hat (Feld PFLANZJAHR). Das ist nicht der ganze Baumbestand; Wald, Parkbäume und
private Bäume fehlen. Gezählt werden die Punkte je Stadtteil, bezogen auf seine Fläche.

Methodik: docs/methodik/jungbaeume.md
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .. import kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_vektor, vektordatei
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen, Zeitwert

DATENSATZ = "stadtbaeume"

STUFEN = Stufen(
    grenzen=(0, 25, 50, 100, 200),
    farben=FARBSTUFEN["gruen"],
    texte=("unter 25 je km²", "25 bis 50", "50 bis 100", "100 bis 200", "200 und mehr"),
    keine_daten_text="zu wenig Fläche, kein Wert",
)


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfad = vektordatei(DATENSATZ)
    baeume = lies_vektor(pfad)
    if "PFLANZJAHR" not in baeume.columns:
        raise ValueError(f"{pfad.name}: Feld PFLANZJAHR fehlt; ist das noch die Ebene der Jungbäume? "
                         "Erst untersuchen: uv run essen inspizieren stadtbaeume")
    ab = int(p["ab_jahr"])
    jahr = pd.to_numeric(baeume["PFLANZJAHR"], errors="coerce")
    baeume = baeume[jahr >= ab].assign(PFLANZJAHR=jahr[jahr >= ab])
    melde(f"{zahl(len(baeume))} Jungbäume mit Pflanzjahr ab {ab}. Zähle je Stadtteil …")
    anzahl = kennzahlen.punkte_je_gebiet(gebiete, baeume)

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"})
    tabelle = tabelle.set_index("gebiet_id")
    tabelle["anzahl_baeume"] = anzahl.reindex(tabelle.index).fillna(0).astype(int)
    tabelle["baeume_je_km2"] = tabelle["anzahl_baeume"] / (tabelle["flaeche_ha"] / 100)
    minimum = float(p["min_flaeche_ha"])
    tabelle = kennzahlen.mindestbezug(tabelle, "flaeche_ha", minimum, ["baeume_je_km2"],
                                      f"unter {minimum:g} ha Fläche, kein Wert ausgewiesen")
    tabelle = tabelle.reset_index().round({"baeume_je_km2": 1, "flaeche_ha": 1})
    gezaehlt = int(tabelle["anzahl_baeume"].sum())
    stadtweit = 100 * gezaehlt / tabelle["flaeche_ha"].sum() if tabelle["flaeche_ha"].sum() else None
    text = ("Keine Fläche." if stadtweit is None else
            f"Stadtweit stehen {zahl(stadtweit)} von der Stadt seit {ab} gepflanzte Jungbäume je km² "
            f"({zahl(gezaehlt)} Bäume).")
    melde(text)
    ausserhalb = len(baeume) - gezaehlt
    hinweise = list(stadtteile.hinweise) + [
        "Nur Jungbäume der Stadt (WFS-Ebene Stadtbaeume_Jungbaeume), nicht der ganze Baumbestand: Wald, Parkbäume, "
        "ältere Straßenbäume und private Bäume fehlen. Für Baumkronen insgesamt siehe das Thema Grün.",
        "Bezug ist die ganze Fläche des Stadtteils, auch Wald und Wasser.",
    ]
    if ausserhalb:
        hinweise.append(f"{zahl(ausserhalb)} Bäume liegen außerhalb der Stadtteilflächen (Rand) und zählen nicht.")
    jahre, abgerufen = jahreswerte(gebiete, baeume, minimum)
    if len(jahre):
        hinweise.append("Verlauf über die Jahre: gezählt sind die Bäume, die beim Abruf noch im Verzeichnis standen. "
                        "Inzwischen gefällte oder abgestorbene Jungbäume fehlen, frühe Jahre sind also eher zu niedrig.")
        if abgerufen:
            hinweise.append(f"Das Jahr des Abrufs ({abgerufen}) und spätere gelten als unvollständig und erscheinen "
                            "nicht im Verlauf.")
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id, tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit, kennzahl_text=text, hinweise=hinweise,
        quellen=[stadtteile.datensatz, DATENSATZ], parameter=dict(p), jahreswerte=jahre,
    )


def jahreswerte(gebiete: gpd.GeoDataFrame, baeume: gpd.GeoDataFrame, min_flaeche_ha: float) -> tuple[pd.DataFrame, int | None]:
    """Je Stadtteil und Pflanzjahr: gepflanzt in dem Jahr und Jungbäume je km² bis einschließlich dieses Jahres.

    Ein Jahr gilt als vollständig, wenn es vor dem Jahr des Abrufs liegt (gepflanzt wird bis in den Winter, und
    die Stadt trägt Bäume nach). Gibt die lange Tabelle und das Jahr des Abrufs (falls bekannt) zurück."""
    abruf = laden.lese_abruf(DATENSATZ)
    abgerufen = int(abruf.zeit[:4]) if abruf and abruf.zeit[:4].isdigit() else None
    jahre = sorted(int(j) for j in baeume["PFLANZJAHR"].dropna().unique())
    if not jahre:
        return pd.DataFrame(columns=["gebiet_id", "stadtteil", "jahr", "gepflanzt", "baeume_je_km2", "vollstaendig"]), abgerufen
    zuordnung = gpd.sjoin(baeume[["PFLANZJAHR", "geometry"]].to_crs(gebiete.crs), gebiete[["gebiet_id", "geometry"]],
                          how="inner", predicate="within")
    je_jahr = zuordnung.groupby(["gebiet_id", "PFLANZJAHR"]).size()
    flaeche = gebiete.set_index("gebiet_id")["flaeche_ha"]
    teile = []
    for gebiet_id, name in zip(gebiete["gebiet_id"], gebiete["name"], strict=True):
        gepflanzt = pd.Series([int(je_jahr.get((gebiet_id, float(j)), 0)) for j in jahre], index=jahre)
        bestand = gepflanzt.cumsum()
        dichte = bestand / (flaeche[gebiet_id] / 100) if flaeche[gebiet_id] >= min_flaeche_ha else float("nan")
        teile.append(pd.DataFrame({"gebiet_id": gebiet_id, "stadtteil": name, "jahr": jahre,
                                   "gepflanzt": gepflanzt.values, "baeume_je_km2": dichte}))
    tabelle = pd.concat(teile, ignore_index=True).round({"baeume_je_km2": 1})
    tabelle["vollstaendig"] = tabelle["jahr"] < abgerufen if abgerufen else True
    return tabelle, abgerufen


ANALYSE = Analyse(
    id="jungbaeume",
    gewicht="flaeche_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Jungbäume der Stadt je Stadtteil",
    frage="Wie viele Bäume hat die Stadt seit 2008 je Quadratkilometer eines Stadtteils gepflanzt?",
    themen=("gruen",),
    benoetigt=("stadtteile", DATENSATZ),
    rechne=rechne,
    kennzahl="baeume_je_km2",
    kennzahl_titel="Jungbäume je km²",
    einheit="je km²",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("baeume_je_km2", "Jungbäume je km²", "zahl", balken=True),
        Spalte("anzahl_baeume", "Jungbäume", "zahl"),
        Spalte("flaeche_ha", "Fläche", "flaeche"),
    ),
    parameter=(
        Parameter("ab_jahr", "Gepflanzt ab", 2008, "Nur Bäume mit diesem oder einem späteren Pflanzjahr zählen.",
                  typ="ganzzahl"),
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert.", typ="zahl", selten=True),
    ),
    methodik="methodik/jungbaeume.md",
    zeitachse=(Zeitwert("baeume_je_km2", "Jungbäume je km², gepflanzt bis zum Jahr", "je km²", STUFEN, stellen=0,
                        jahrzehnte=False,
                        hinweis="Gezählt sind die Bäume, die beim Abruf noch im Verzeichnis standen; inzwischen "
                                "gefällte fehlen. Die Karte zeigt, wo gepflanzt wurde, nicht den Baumbestand."),),
    thema_titel="Neue Bäume",
    kurz="Wo hat die Stadt in den letzten Jahren viele junge Bäume gepflanzt?",
    richtung="hoch_gut",
    lesehilfe="Gefärbt nach der Zahl der Jungbäume, die die Stadt seit 2008 gepflanzt hat, je Quadratkilometer. "
              "Dunkleres Grün heißt mehr neue Bäume auf derselben Fläche.",
    grenzen_kurz=(
        "Nur von der Stadt gepflanzte Jungbäume, nicht alle Bäume: Wald, Parks und private Gärten fehlen.",
        "Ein Stadtteil mit viel altem Baumbestand kann wenige neue Bäume haben und trotzdem sehr grün sein.",
        "Junge Bäume spenden erst nach Jahren viel Schatten.",
    ),
)
