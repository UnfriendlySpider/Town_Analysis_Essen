"""Hitzebetroffenheit je Stadtteil.

Grundlage ist die Betroffenheitsanalyse der Klimaanalyse NRW 2026 (LANUK): Baublöcke im Siedlungsbereich, in
denen viele Hochaltrige oder Kleinkinder wohnen oder die Mieten niedrig sind (je Gemeinde in Dezile eingeteilt),
überlagert mit dem dringenden Handlungsbedarf wegen Hitze aus der Planungshinweiskarte. Für jeden Stadtteil:
welcher Anteil der Baublockfläche ist sensitiv und zugleich hitzebelastet?

Layer und Klassen stehen in katalog/zuordnungen/klimaanalyse-betroffenheit.yaml.
Methodik: docs/methodik/betroffenheit.md
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pyogrio

from .. import kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_im_stadtgebiet, vektordatei
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen
from .hitze_nacht import ZuordnungFehlt, lade_zuordnung
from .starkregen import pruefe_klassen

DATENSATZ = "klimaanalyse-betroffenheit"

STUFEN = Stufen(
    grenzen=(0, 5, 10, 15, 20),
    farben=FARBSTUFEN["waerme"],
    texte=("unter 5 %", "5 bis 10 %", "10 bis 15 %", "15 bis 20 %", "20 % und mehr"),
    keine_daten_text="zu wenig Baublockfläche, kein Anteil",
)


def _zuordnung() -> dict:
    zuordnung = lade_zuordnung(DATENSATZ)
    noetig = ("layer_wirkraum", "layer_handlungsbedarf", "feld", "klassen", "ab_klasse", "gemeinde")
    if not zuordnung or any(not zuordnung.get(k) for k in noetig):
        raise ZuordnungFehlt(f"katalog/zuordnungen/{DATENSATZ}.yaml fehlt oder nennt nicht alle Angaben "
                             f"({', '.join(noetig)}).")
    return zuordnung


def _lies(pfad, layer: str, zuordnung: dict) -> gpd.GeoDataFrame:
    vorhanden = {name for name, _ in pyogrio.list_layers(pfad)}
    if layer not in vorhanden:
        raise ZuordnungFehlt(f"{zuordnung['_pfad']}: Layer {layer} fehlt (vorhanden: {', '.join(sorted(vorhanden))}).")
    gemeinde = str(zuordnung["gemeinde"]).replace("'", "''")
    flaechen = lies_im_stadtgebiet(pfad, layer=layer, where=f"gemeind = '{gemeinde}'")
    pruefe_klassen(flaechen, zuordnung)
    flaechen["klasse"] = pd.to_numeric(flaechen[zuordnung["feld"]]).astype(int)
    flaechen["sensitiv"] = flaechen["klasse"] >= int(zuordnung["ab_klasse"])
    return flaechen.to_crs(ZIEL_CRS)


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    zuordnung = _zuordnung()
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfad = vektordatei(DATENSATZ)
    melde(f"Betroffenheitsanalyse: {pfad.name}")
    wirkraum = _lies(pfad, zuordnung["layer_wirkraum"], zuordnung)
    bedarf = _lies(pfad, zuordnung["layer_handlungsbedarf"], zuordnung)
    melde(f"  {zahl(len(wirkraum))} Baublöcke im Wirkraum, {zahl(len(bedarf))} mit dringendem Handlungsbedarf")
    teile = pd.concat([
        wirkraum.assign(gruppe="wirkraum")[["gruppe", "geometry"]],
        wirkraum[wirkraum["sensitiv"]].assign(gruppe="sensitiv")[["gruppe", "geometry"]],
        bedarf.assign(gruppe="bedarf")[["gruppe", "geometry"]],
        bedarf[bedarf["sensitiv"]].assign(gruppe="betroffen")[["gruppe", "geometry"]],
    ], ignore_index=True)
    melde("Verschneide mit den Stadtteilen …")
    gruppen = ["wirkraum", "sensitiv", "bedarf", "betroffen"]
    flaechen = kennzahlen.flaechen_nach_klasse(gebiete, gpd.GeoDataFrame(teile, geometry="geometry", crs=ZIEL_CRS),
                                               gruppen, spalte="gruppe") / 1e4

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    for gruppe, spalte in zip(gruppen, ("baubloecke_ha", "sensitiv_ha", "handlungsbedarf_ha", "betroffen_ha"), strict=True):
        tabelle[spalte] = flaechen[gruppe].reindex(tabelle.index).fillna(0.0)
    bezug = tabelle["baubloecke_ha"].where(tabelle["baubloecke_ha"] > 0)
    tabelle["anteil_betroffen_pct"] = 100 * tabelle["betroffen_ha"] / bezug
    tabelle["anteil_sensitiv_pct"] = 100 * tabelle["sensitiv_ha"] / bezug
    tabelle["anteil_handlungsbedarf_pct"] = 100 * tabelle["handlungsbedarf_ha"] / bezug
    minimum = float(p["min_flaeche_ha"])
    tabelle = kennzahlen.mindestbezug(tabelle, "baubloecke_ha", minimum,
                                      ["anteil_betroffen_pct", "anteil_sensitiv_pct", "anteil_handlungsbedarf_pct"],
                                      f"unter {minimum:g} ha Baublockfläche, kein Anteil ausgewiesen")
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha"))})

    mit_wert = tabelle.dropna(subset=["anteil_betroffen_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_betroffen_pct"], mit_wert["baubloecke_ha"])
    text = ("Kein Stadtteil mit genug Baublockfläche." if stadtweit is None else
            f"Stadtweit sind {zahl(stadtweit, 1)} % der Baublockfläche sensitiv und zugleich hitzebelastet "
            "(dringender Handlungsbedarf).")
    melde(text)
    hinweise = list(stadtteile.hinweise)
    if not zuordnung.get("geprueft", False):
        hinweise.append(f"Die Zuordnung {zuordnung['_pfad']} ist noch nicht als geprüft markiert.")
    hinweise += [
        "Sensitiv heißt laut LANUK: viele Hochaltrige (ab 80) oder Kleinkinder (unter 6) je Fläche oder niedrige "
        "Nettokaltmiete, jeweils im obersten Bereich innerhalb Essens (Dezile je Gemeinde, Zensus 2022). Das ist ein "
        "Vergleich innerhalb Essens.",
        "Hitzebelastet heißt: Handlungspriorität 1 oder 2 der Planungshinweiskarte der Klimaanalyse NRW 2026 (Modell).",
        "Bezug ist die Fläche der Baublöcke im Siedlungsbereich, nicht die Zahl der Menschen. Die Nettokaltmiete ist "
        "nur ein Ersatz für Armutsgefährdung.",
    ]
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise + [f"Layer und Klassen aus der Zuordnung {zuordnung['_pfad']}."],
        quellen=[stadtteile.datensatz, DATENSATZ],
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="betroffenheit",
    gewicht="baubloecke_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Hitzebetroffenheit je Stadtteil",
    frage="Welcher Anteil der Wohnblöcke eines Stadtteils ist für Hitze empfindlich und zugleich stark hitzebelastet?",
    themen=("klima", "bevoelkerung"),
    benoetigt=("stadtteile", DATENSATZ),
    rechne=rechne,
    kennzahl="anteil_betroffen_pct",
    kennzahl_titel="Anteil der Baublockfläche, sensitiv und hitzebelastet",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_betroffen_pct", "sensitiv und hitzebelastet", "prozent", balken=True),
        Spalte("anteil_sensitiv_pct", "sensitiv", "prozent"),
        Spalte("anteil_handlungsbedarf_pct", "hitzebelastet", "prozent"),
        Spalte("baubloecke_ha", "Baublöcke, ha", "zahl", stellen=1),
    ),
    parameter=(
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken könnte.", typ="zahl",
                  selten=True),
    ),
    methodik="methodik/betroffenheit.md",
    thema_titel="Hitze und empfindliche Menschen",
    kurz="Wo wohnen viele hitzeempfindliche Menschen – Hochbetagte, kleine Kinder, Menschen mit wenig Geld – in Wohnblöcken, die stark unter Hitze leiden?",
    richtung="hoch_schlecht",
    lesehilfe="Gefärbt nach dem Anteil der Wohnblockfläche, die zugleich empfindlich und stark hitzebelastet ist. Empfindlich heißt: viele Menschen ab 80 oder unter 6 Jahren oder niedrige Mieten, jeweils im Vergleich innerhalb Essens.",
    grenzen_kurz=(
        "Ein Vergleich innerhalb Essens, kein fester Maßstab.",
        "Niedrige Miete ist nur ein grober Ersatz für Armut.",
        "Bezug ist die Fläche der Wohnblöcke, nicht die Zahl der Menschen.",
    ),
)
