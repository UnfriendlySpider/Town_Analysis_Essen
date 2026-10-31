"""Kühle Orte in der Nähe: welcher Anteil eines Stadtteils liegt höchstens 300 m Luftlinie von einem kühlen Ort?

Grundlage ist der Datensatz „Kühle Orte“ der Stadt Essen: öffentlich zugängliche Orte, an denen man sich an
heißen Tagen abkühlen kann (Parks, Spielplätze mit Schatten, Bibliotheken, Bäder). Um jeden Ort wird ein Kreis
gelegt; gezählt wird die Fläche des Stadtteils in diesen Kreisen. Optional: Einwohner in diesen Kreisen (E-013).

Methodik: docs/methodik/kuehlorte.md
"""

from __future__ import annotations

import geopandas as gpd

from .. import einwohner, kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_vektor, vektordatei
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen

DATENSATZ = "kuehlorte"

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
    orte = lies_vektor(vektordatei(DATENSATZ)).to_crs(ZIEL_CRS)
    abstand = float(p["abstand_m"])
    if p["orte"] == "draussen" and "ORT" in orte.columns:
        orte = orte[orte["ORT"].astype(str).str.strip().str.lower() == "außen"]
    melde(f"{zahl(len(orte))} kühle Orte, Umkreis {zahl(abstand)} m Luftlinie …")
    kreise = gpd.GeoDataFrame(geometry=[orte.buffer(abstand).union_all()], crs=ZIEL_CRS)
    bedeckt = kennzahlen.flaechenanteil_je_gebiet(gebiete, kreise)
    anzahl = kennzahlen.punkte_je_gebiet(gebiete, orte)

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"})
    tabelle = tabelle.set_index("gebiet_id")
    tabelle["anzahl_orte"] = anzahl.reindex(tabelle.index).fillna(0).astype(int)
    tabelle["nah_ha"] = bedeckt["bedeckt_ha"].reindex(tabelle.index).fillna(0.0)
    tabelle["anteil_nah_pct"] = 100 * tabelle["nah_ha"] / tabelle["flaeche_ha"].where(tabelle["flaeche_ha"] > 0)
    minimum = float(p["min_flaeche_ha"])
    tabelle = kennzahlen.mindestbezug(tabelle, "flaeche_ha", minimum, ["anteil_nah_pct"],
                                      f"unter {minimum:g} ha Fläche, kein Anteil ausgewiesen")
    tabelle = tabelle.reset_index().round({"anteil_nah_pct": 1, "nah_ha": 1, "flaeche_ha": 1})

    einwohner_satz = None
    if einwohner.vorhanden():
        melde("Schätze die Einwohner im Umkreis der kühlen Orte (Zensus-Gitter) …")
        tabelle, satz = einwohner.ergaenze(tabelle, einwohner.in_flaeche(gebiete, kreise.geometry.iloc[0]))
        einwohner_satz = (f"{satz[:-1]} wohnen höchstens {zahl(abstand)} m Luftlinie von einem kühlen Ort entfernt, "
                          f"anteilig nach Fläche. {einwohner.HINWEIS}")
    mit_wert = tabelle.dropna(subset=["anteil_nah_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_nah_pct"], mit_wert["flaeche_ha"])
    text = ("Kein Stadtteil mit genug Fläche." if stadtweit is None else
            f"Stadtweit liegen {zahl(stadtweit, 1)} % der Fläche höchstens {zahl(abstand)} m Luftlinie von einem "
            f"kühlen Ort entfernt ({zahl(len(orte))} Orte).")
    melde(text)
    hinweise = list(stadtteile.hinweise) + [
        "Luftlinie, nicht Fußweg: Straßen, Bahnlinien und Zäune können den Weg deutlich verlängern.",
        "Gezählt wird, ob ein Ort in der Nähe liegt, nicht wie groß, wie schattig oder wann er geöffnet ist "
        "(Felder ART, OEFFNUNGSZ und KOSTEN in den Originaldaten).",
        "Bezug ist die ganze Fläche des Stadtteils, auch Wald und Felder, in denen kaum jemand wohnt (E-007).",
    ]
    if p["orte"] == "draussen":
        hinweise.append("Nur Orte im Freien (Feld ORT = „Außen“).")
    if einwohner_satz:
        hinweise.append(einwohner_satz)
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id, tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit, kennzahl_text=text, hinweise=hinweise,
        quellen=[stadtteile.datensatz, DATENSATZ], parameter=dict(p),
    )


ANALYSE = Analyse(
    id="kuehlorte",
    gewicht="flaeche_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Kühle Orte in der Nähe je Stadtteil",
    frage="Welcher Anteil der Fläche eines Stadtteils liegt höchstens 300 m Luftlinie von einem kühlen Ort entfernt?",
    themen=("klima",),
    benoetigt=("stadtteile", DATENSATZ),
    optional=(einwohner.DATENSATZ,),
    rechne=rechne,
    kennzahl="anteil_nah_pct",
    kennzahl_titel="Anteil der Fläche mit kühlem Ort in der Nähe",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_nah_pct", "Fläche in der Nähe", "prozent", balken=True),
        Spalte("anzahl_orte", "kühle Orte im Stadtteil", "zahl"),
        Spalte("anteil_einwohner_pct", "Einwohner in der Nähe", "prozent"),
    ),
    parameter=(
        Parameter("abstand_m", "Umkreis in Metern (Luftlinie)", 300.0,
                  "300 m sind etwa 5 Minuten zu Fuß, wenn der Weg gerade ist.", typ="zahl"),
        Parameter("orte", "Welche Orte", "alle", "Mit „nur im Freien“ zählen Bibliotheken, Bäder und andere "
                  "Innenräume nicht.", optionen=("alle", "draussen"), typ="wahl",
                  beschriftungen={"alle": "alle Orte", "draussen": "nur im Freien"}),
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert.", typ="zahl", selten=True),
    ),
    methodik="methodik/kuehlorte.md",
    thema_titel="Kühle Orte",
    kurz="Wie weit ist es an heißen Tagen bis zum nächsten kühlen Ort wie einem Park oder einer Bibliothek?",
    richtung="hoch_gut",
    lesehilfe="Gefärbt nach dem Anteil der Fläche, von dem aus ein kühler Ort höchstens 300 m Luftlinie entfernt "
              "ist. Dunkleres Blau heißt: Von mehr Stellen des Stadtteils aus ist ein kühler Ort nah.",
    grenzen_kurz=(
        "Luftlinie, nicht Fußweg: Der echte Weg ist oft länger.",
        "Jeder kühle Ort zählt gleich, ob kleiner Spielplatz oder großer Park.",
        "Die Fläche schließt Wald und Felder ein, wo kaum jemand wohnt.",
    ),
)
