"""Grünanteil je Stadtteil.

Grundlage ist die Landbedeckung NRW (Geobasis NRW, aus Sentinel-2, Luftbildern und Geobasisdaten,
Stand 2023): Jede Fläche gehört zu genau einer Klasse wie Hochbau, Tiefbau, Gras oder Bäume. Für jeden
Stadtteil: welcher Anteil der Fläche ist mit Vegetation bedeckt, und wie viel davon sind Bäume?

Welche Layer und Codes zu welcher Gruppe gehören, steht in katalog/zuordnungen/landbedeckung-nrw.yaml.
Methodik: docs/methodik/gruenanteil.md
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

DATENSATZ = "landbedeckung-nrw"
GRUPPEN = {
    "baeume": "Bäume",
    "gehoelz": "Gehölz, Büsche und Sträucher",
    "gras": "Gras",
    "kraut_sonstige": "Getreide, Stauden, Röhricht",
    "hochbau": "Hochbau (Gebäude)",
    "tiefbau": "Tiefbau (Straßen, Plätze, Wege)",
    "lockermaterial": "Lockermaterial (Sand, Kies, offener Boden)",
    "wasser": "Wasser",
}

STUFEN = Stufen(
    grenzen=(0, 30, 45, 60, 75),
    farben=FARBSTUFEN["gruen"],
    texte=("unter 30 %", "30 bis 45 %", "45 bis 60 %", "60 bis 75 %", "75 % und mehr"),
    keine_daten_text="zu wenig Fläche, kein Anteil",
)


def _zuordnung() -> dict:
    zuordnung = lade_zuordnung(DATENSATZ)
    if not zuordnung or not zuordnung.get("gruppen"):
        raise ZuordnungFehlt(f"katalog/zuordnungen/{DATENSATZ}.yaml fehlt oder hat keine gruppen "
                             "(welcher Layer und Code zu welcher Gruppe gehört).")
    unbekannt = {g for g in _alle_gruppen(zuordnung) if g not in GRUPPEN}
    if unbekannt:
        raise ZuordnungFehlt(f"{zuordnung['_pfad']}: unbekannte Gruppen {', '.join(sorted(unbekannt))}.")
    return zuordnung


def _alle_gruppen(zuordnung: dict) -> set[str]:
    gruppen = set()
    for regel in zuordnung["gruppen"].values():
        gruppen |= set((regel.get("werte") or {}).values()) if isinstance(regel, dict) else {regel}
    return gruppen


def lies_flaechen(pfad, zuordnung: dict, melde) -> gpd.GeoDataFrame:
    """Alle Flächen im Stadtgebiet mit der Spalte gruppe. Unbekannte Codes führen zum Abbruch (E-009)."""
    vorhanden = {name for name, _ in pyogrio.list_layers(pfad)}
    teile = []
    for layer, regel in zuordnung["gruppen"].items():
        if layer not in vorhanden:
            raise ZuordnungFehlt(f"{zuordnung['_pfad']}: Layer {layer} fehlt in {pfad.name} "
                                 f"(vorhanden: {', '.join(sorted(vorhanden))}).")
        flaechen = lies_im_stadtgebiet(pfad, layer=layer)
        if isinstance(regel, dict):
            codes = flaechen[regel["feld"]].astype(str).str.strip()
            werte = {str(k): v for k, v in regel["werte"].items()}
            offen = sorted(set(codes) - set(werte))
            if offen:
                raise ZuordnungFehlt(f"{zuordnung['_pfad']}: In {layer}.{regel['feld']} kommen Codes ohne Zuordnung "
                                     f"vor: {', '.join(offen)}. Bedeutung in den Stildateien nachsehen und eintragen.")
            flaechen["gruppe"] = codes.map(werte)
        else:
            flaechen["gruppe"] = regel
        melde(f"  {layer}: {zahl(len(flaechen))} Flächen")
        teile.append(flaechen[["gruppe", "geometry"]].to_crs(ZIEL_CRS))
    return gpd.GeoDataFrame(pd.concat(teile, ignore_index=True), geometry="geometry", crs=ZIEL_CRS)


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    zuordnung = _zuordnung()
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfad = vektordatei(DATENSATZ)
    melde(f"Landbedeckung: {pfad.name}")
    flaechen = lies_flaechen(pfad, zuordnung, melde)
    melde("Verschneide mit den Stadtteilen …")
    je_gruppe = kennzahlen.flaechen_nach_klasse(gebiete, flaechen, list(GRUPPEN), spalte="gruppe")

    gruen = [g for g in zuordnung.get("gruen", []) if g in GRUPPEN]
    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    tabelle["bedeckt_ha"] = (je_gruppe.sum(axis=1) / 1e4).reindex(tabelle.index).fillna(0.0)
    tabelle["gruen_ha"] = (je_gruppe[gruen].sum(axis=1) / 1e4).reindex(tabelle.index).fillna(0.0)
    tabelle["baeume_ha"] = (je_gruppe["baeume"] / 1e4).reindex(tabelle.index).fillna(0.0)
    bezug = tabelle["bedeckt_ha"].where(tabelle["bedeckt_ha"] > 0)
    tabelle["anteil_gruen_pct"] = 100 * tabelle["gruen_ha"] / bezug
    tabelle["anteil_baeume_pct"] = 100 * tabelle["baeume_ha"] / bezug
    for gruppe in GRUPPEN:
        tabelle[f"{gruppe}_pct"] = 100 * (je_gruppe[gruppe] / 1e4).reindex(tabelle.index) / bezug
    tabelle["abdeckung_pct"] = 100 * tabelle["bedeckt_ha"] / tabelle["flaeche_ha"]
    minimum = float(p["min_flaeche_ha"])
    spalten = ["anteil_gruen_pct", "anteil_baeume_pct"] + [f"{g}_pct" for g in GRUPPEN]
    tabelle = kennzahlen.mindestbezug(tabelle, "bedeckt_ha", minimum, spalten,
                                      f"unter {minimum:g} ha erfasste Fläche, kein Anteil ausgewiesen")
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha"))})

    hinweise = list(stadtteile.hinweise)
    luecken = tabelle[tabelle["abdeckung_pct"] < 99]
    if len(luecken):
        hinweise.append("Die Landbedeckung deckt nicht die ganze Fläche ab: "
                        + ", ".join(f"{z.stadtteil} {zahl(z.abdeckung_pct)} %" for z in luecken.itertuples()) + ".")
    ueber = tabelle[tabelle["abdeckung_pct"] > 101]
    if len(ueber):
        hinweise.append("Flächen der Landbedeckung überschneiden sich in: " + ", ".join(ueber["stadtteil"]) + ".")
    mit_wert = tabelle.dropna(subset=["anteil_gruen_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_gruen_pct"], mit_wert["bedeckt_ha"])
    baeume = kennzahlen.gewichtetes_mittel(mit_wert["anteil_baeume_pct"], mit_wert["bedeckt_ha"])
    text = ("Kein Stadtteil mit genug Fläche." if stadtweit is None else
            f"Stadtweit sind {zahl(stadtweit)} % der Fläche mit Vegetation bedeckt, {zahl(baeume)} % mit Bäumen.")
    melde(text)
    hinweise += [
        "Grün heißt hier: Vegetation laut Landbedeckung (Gras, Getreide und Stauden, Röhricht, Bäume, Gehölz, "
        "Büsche). Dazu gehören auch Äcker, Gärten und Friedhöfe; öffentlich zugänglich ist nur ein Teil davon.",
        "Die Landbedeckung beruht auf Satellitenbildern (Sentinel-2, 10 m) und Luftbildern; kleine Flächen wie "
        "Vorgärten oder einzelne Straßenbäume sind nur teilweise erfasst.",
        "Pflichtvermerk bei Weitergabe: „Enthält modifizierte Copernicus Sentinel-2 Daten [2023], verarbeitet durch "
        "Geobasis NRW; dl-de/by-2-0“.",
    ]
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise + [f"Gruppen aus der Zuordnung {zuordnung['_pfad']}."],
        quellen=[stadtteile.datensatz, DATENSATZ],
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="gruenanteil",
    gewicht="bedeckt_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Grünanteil je Stadtteil",
    frage="Welcher Anteil der Fläche eines Stadtteils ist mit Vegetation bedeckt, und wie viel davon mit Bäumen?",
    themen=("gruen",),
    benoetigt=("stadtteile", DATENSATZ),
    rechne=rechne,
    kennzahl="anteil_gruen_pct",
    kennzahl_titel="Anteil der Fläche mit Vegetation",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_gruen_pct", "Vegetation", "prozent", balken=True),
        Spalte("anteil_baeume_pct", "Bäume", "prozent"),
        Spalte("gruen_ha", "Vegetation, ha", "zahl", stellen=1),
    ),
    parameter=(
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken könnte.", typ="zahl",
                  selten=True),
    ),
    methodik="methodik/gruenanteil.md",
    thema_titel="Grün",
    kurz="Wie viel der Fläche ist mit Pflanzen bedeckt – Wiesen, Bäume, Büsche oder Felder?",
    richtung="hoch_gut",
    lesehilfe="Gefärbt nach dem Anteil der Fläche mit Pflanzen. Dunkleres Grün heißt mehr Grün. Bäume werden zusätzlich gezählt, weil sie im Sommer besonders kühlen.",
    grenzen_kurz=(
        "Auch Gärten, Felder und Friedhöfe zählen; nicht alles ist öffentlich zugänglich.",
        "Satellitenbilder mit 10 m Auflösung erkennen einzelne Straßenbäume nur teilweise.",
        "Bezug ist die Fläche, nicht die Einwohner.",
    ),
)
