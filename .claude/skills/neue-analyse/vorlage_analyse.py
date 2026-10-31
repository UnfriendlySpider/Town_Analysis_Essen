"""VORLAGE: Anteil einer Fläche je Stadtteil (z. B. Grünflächen, versiegelte Fläche).

Kopieren nach src/essen/analysen/<thema>.py, alle Stellen mit ANPASSEN ändern und in
src/essen/analysen/__init__.py in ALLE eintragen. Methodik: docs/methodik/<id>.md
"""

from __future__ import annotations

import geopandas as gpd

from .. import kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_im_stadtgebiet, vektordatei
from ..text import mehrzahl, zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen

DATENSATZ = "osm-gruenflaechen"  # ANPASSEN: Datensatz-ID aus katalog/datensaetze.yaml

# ANPASSEN: Grenzen zum Thema wählen, Farben aus essen/farben.py (geprüft, Skill karte-gestalten).
STUFEN = Stufen(
    grenzen=(0, 10, 20, 30, 40),
    farben=FARBSTUFEN["gruen"],
    texte=("unter 10 %", "10 bis 20 %", "20 bis 30 %", "30 bis 40 %", "40 % und mehr"),
)


def rechne(kontext: Kontext) -> Ergebnis:
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    stadtteile = lade_stadtteile(kontext.katalog)
    pfad = vektordatei(DATENSATZ)
    flaechen = lies_im_stadtgebiet(pfad, layer=kontext.parameter["layer"] or None)
    kontext.melde(f"{mehrzahl(len(flaechen), 'Fläche', 'Flächen')} gelesen")

    anteil = kennzahlen.flaechenanteil_je_gebiet(stadtteile.gdf, flaechen)
    tabelle = stadtteile.gdf.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"})
    tabelle["bedeckt_ha"] = tabelle["gebiet_id"].map(anteil["bedeckt_ha"]).round(1)
    tabelle["anteil_pct"] = tabelle["gebiet_id"].map(anteil["anteil_pct"]).round(1)
    tabelle["flaeche_ha"] = tabelle["flaeche_ha"].round(1)

    stadtweit = kennzahlen.gewichtetes_mittel(tabelle["anteil_pct"], tabelle["flaeche_ha"])
    text = f"Stadtweit sind {zahl(stadtweit, 1)} % der Fläche bedeckt."  # ANPASSEN
    geometrie = gpd.GeoDataFrame(stadtteile.gdf[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id"),
                                 geometry="geometry", crs=ZIEL_CRS)
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=geometrie,
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=stadtteile.hinweise + ["ANPASSEN: Grenzen der Methode nennen."],
        quellen=[stadtteile.datensatz, DATENSATZ],
        parameter=dict(kontext.parameter),
    )


ANALYSE = Analyse(
    id="mein-thema",                                  # ANPASSEN
    titel="Anteil … je Stadtteil",                    # ANPASSEN
    frage="Welcher Anteil der Fläche ist …?",         # ANPASSEN
    themen=("gruen",),                                # ANPASSEN
    benoetigt=("stadtteile", DATENSATZ),
    rechne=rechne,
    kennzahl="anteil_pct",
    kennzahl_titel="Anteil der Fläche",               # ANPASSEN
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_pct", "Anteil", "prozent", stellen=1, balken=True),
        Spalte("bedeckt_ha", "bedeckt, ha", "zahl", stellen=1),
    ),
    parameter=(Parameter("layer", "Layer", "", "leer = erster Layer"),),
    methodik="methodik/mein-thema.md",                # ANPASSEN
)
