"""Umweltzone je Stadtteil: welcher Anteil der Fläche liegt in der Umweltzone?

Grundlage ist die Grenze der Umweltzone der Stadt Essen (GeoJSON, drei getrennte Flächen; die große hat
Aussparungen als Löcher). Die Flächen tragen keine Merkmale außer Kennungen und Flächenmaßen; gezählt wird
nur, ob ein Ort innerhalb liegt.

Methodik: docs/methodik/umweltzone.md
"""

from __future__ import annotations

import geopandas as gpd

from .. import kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_vektor, vektordatei
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen

DATENSATZ = "umweltzone"

STUFEN = Stufen(
    grenzen=(0, 20, 40, 60, 80),
    farben=FARBSTUFEN["neutral"],
    texte=("unter 20 %", "20 bis 40 %", "40 bis 60 %", "60 bis 80 %", "80 % und mehr"),
    keine_daten_text="zu wenig Fläche, kein Anteil",
)


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    zone = lies_vektor(vektordatei(DATENSATZ)).to_crs(ZIEL_CRS)
    zone = zone[zone.geometry.notna() & ~zone.geometry.is_empty]
    melde(f"Umweltzone: {zahl(len(zone))} Flächen, zusammen {zahl(zone.area.sum() / 1e6, 1)} km². Verschneide …")
    bedeckt = kennzahlen.flaechenanteil_je_gebiet(gebiete, zone)

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"})
    tabelle = tabelle.set_index("gebiet_id")
    tabelle["zone_ha"] = bedeckt["bedeckt_ha"].reindex(tabelle.index).fillna(0.0)
    tabelle["anteil_zone_pct"] = 100 * tabelle["zone_ha"] / tabelle["flaeche_ha"].where(tabelle["flaeche_ha"] > 0)
    minimum = float(p["min_flaeche_ha"])
    tabelle = kennzahlen.mindestbezug(tabelle, "flaeche_ha", minimum, ["anteil_zone_pct"],
                                      f"unter {minimum:g} ha Fläche, kein Anteil ausgewiesen")
    tabelle = tabelle.reset_index().round({"anteil_zone_pct": 1, "zone_ha": 1, "flaeche_ha": 1})
    mit_wert = tabelle.dropna(subset=["anteil_zone_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_zone_pct"], mit_wert["flaeche_ha"])
    ganz = int((mit_wert["anteil_zone_pct"] >= 99.5).sum())
    text = ("Kein Stadtteil mit genug Fläche." if stadtweit is None else
            f"Stadtweit liegen {zahl(stadtweit, 1)} % der Fläche in der Umweltzone; {zahl(ganz)} Stadtteile liegen "
            "ganz darin.")
    melde(text)
    hinweise = list(stadtteile.hinweise) + [
        "Die Umweltzone ist eine Regel für Fahrzeuge, keine Messung: Sie sagt nichts darüber, wie gut die Luft ist.",
        "Aussparungen (etwa Autobahnen) sind in den Originaldaten Löcher in der Fläche und zählen nicht zur Zone.",
        "Stand laut Katalog; ob die Zone heute noch gilt, steht beim Anbieter.",
    ]
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id, tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit, kennzahl_text=text, hinweise=hinweise,
        quellen=[stadtteile.datensatz, DATENSATZ], parameter=dict(p),
    )


ANALYSE = Analyse(
    id="umweltzone",
    gewicht="flaeche_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Umweltzone je Stadtteil",
    frage="Welcher Anteil der Fläche eines Stadtteils liegt in der Umweltzone?",
    themen=("luft",),
    benoetigt=("stadtteile", DATENSATZ),
    rechne=rechne,
    kennzahl="anteil_zone_pct",
    kennzahl_titel="Anteil der Fläche in der Umweltzone",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_zone_pct", "in der Umweltzone", "prozent", balken=True),
        Spalte("zone_ha", "in der Zone, ha", "zahl", stellen=1),
        Spalte("flaeche_ha", "Fläche", "flaeche"),
    ),
    parameter=(
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert.", typ="zahl", selten=True),
    ),
    methodik="methodik/umweltzone.md",
    thema_titel="Umweltzone",
    kurz="Welche Teile der Stadt liegen in der Umweltzone, in der nur Autos mit grüner Plakette fahren dürfen?",
    richtung="neutral",
    lesehilfe="Gefärbt nach dem Anteil der Fläche, der in der Umweltzone liegt. Dunkler heißt: mehr vom Stadtteil "
              "liegt in der Zone. Das ist weder gut noch schlecht, sondern eine Regel für den Verkehr.",
    grenzen_kurz=(
        "Eine Regel für Fahrzeuge, keine Messung der Luft.",
        "Ausgenommene Straßen wie Autobahnen zählen nicht zur Zone.",
        "Ob die Zone heute noch so gilt, steht beim Anbieter.",
    ),
)
