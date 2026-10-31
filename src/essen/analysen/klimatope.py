"""Stadtklima nach Klimatopen je Stadtteil.

Grundlage ist die Klimatopkarte der Klimaanalyse NRW 2026 (LANUK): Flächen mit einheitlichem Mikroklima, von
Freiland- und Waldklima bis zu Stadt-, Innenstadt- und Gewerbeklima, abgeleitet aus Nutzung, Überbauung und
Versiegelung. Für jeden Stadtteil: wie verteilt sich die Fläche auf die Klimatope, und welcher Anteil gehört zu
den Klimatopen dichter Bebauung (Stadtklima, Innenstadtklima, dichtes Gewerbeklima)?

Klassen und Gruppen stehen in katalog/zuordnungen/klimaanalyse-klimatope.yaml.
Methodik: docs/methodik/klimatope.md
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .. import kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_im_stadtgebiet, vektordatei
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen
from .hitze_nacht import ZuordnungFehlt, lade_zuordnung
from .starkregen import pruefe_klassen

DATENSATZ = "klimaanalyse-klimatope"
LAYER = "PL_KY_KLIMATOP"
GRUPPEN = {"gruen_wasser": "Grün, Wald und Wasser", "locker": "lockere Bebauung und offenes Gewerbe",
           "dicht": "dichte Bebauung und dichtes Gewerbe", "verkehr": "Straßen und Bahn", "keine": "keine Angabe"}

STUFEN = Stufen(
    grenzen=(0, 10, 20, 30, 40),
    farben=FARBSTUFEN["waerme"],
    texte=("unter 10 %", "10 bis 20 %", "20 bis 30 %", "30 bis 40 %", "40 % und mehr"),
    keine_daten_text="zu wenig Fläche, kein Anteil",
)


def _zuordnung() -> dict:
    zuordnung = lade_zuordnung(DATENSATZ)
    if not zuordnung or not zuordnung.get("feld") or not zuordnung.get("textfeld") or not zuordnung.get("klassen"):
        raise ZuordnungFehlt(f"katalog/zuordnungen/{DATENSATZ}.yaml fehlt oder nennt feld, textfeld und klassen nicht.")
    unbekannt = {k: v.get("gruppe") for k, v in zuordnung["klassen"].items() if v.get("gruppe") not in GRUPPEN}
    if unbekannt:
        raise ZuordnungFehlt(f"{zuordnung['_pfad']}: Klassen ohne bekannte Gruppe: {unbekannt}.")
    return zuordnung


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    zuordnung = _zuordnung()
    feld, textfeld = zuordnung["feld"], zuordnung["textfeld"]
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfad = vektordatei(DATENSATZ)
    melde(f"Klimatopkarte: {pfad.name}, Layer {LAYER}")
    flaechen = lies_im_stadtgebiet(pfad, layer=LAYER, columns=[feld, textfeld])
    # Splitter unter 1 m² tragen nichts bei. Darunter sind in der echten Karte 3 Flächen mit Code 0 und ohne Text
    # (keine Tabelle der Methodik nennt ihn); sie fallen weg. Ein unbekannter Code mit Fläche bricht weiter ab.
    leer = flaechen.geometry.area < 1.0
    flaechen = flaechen[~leer]
    pruefe_klassen(flaechen, zuordnung)  # Zahl und Text müssen zur Zuordnung passen (E-009)
    klassen = {int(k): v for k, v in zuordnung["klassen"].items()}
    flaechen["klasse"] = pd.to_numeric(flaechen[feld]).astype(int)
    melde(f"  {zahl(len(flaechen))} Flächen im Rechteck um Essen. Verschneide mit den Stadtteilen …")
    je_klasse = kennzahlen.flaechen_nach_klasse(gebiete, flaechen[["klasse", "geometry"]], sorted(klassen)) / 1e4

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    je_klasse = je_klasse.reindex(tabelle.index).fillna(0.0)
    tabelle["bedeckt_ha"] = je_klasse.sum(axis=1)
    bezug = tabelle["bedeckt_ha"].where(tabelle["bedeckt_ha"] > 0)
    for gruppe in GRUPPEN:
        codes = [c for c, k in klassen.items() if k["gruppe"] == gruppe]
        tabelle[f"{gruppe}_ha"] = je_klasse[codes].sum(axis=1) if codes else 0.0
        tabelle[f"anteil_{gruppe}_pct"] = 100 * tabelle[f"{gruppe}_ha"] / bezug
    for code in sorted(klassen):
        tabelle[f"klasse_{code}_pct".replace("-", "m")] = 100 * je_klasse[code] / bezug
    minimum = float(p["min_flaeche_ha"])
    anteile = [c for c in tabelle.columns if c.endswith("_pct")]
    tabelle = kennzahlen.mindestbezug(tabelle, "bedeckt_ha", minimum, anteile,
                                      f"unter {minimum:g} ha Fläche, kein Anteil ausgewiesen")
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha"))})

    mit_wert = tabelle.dropna(subset=["anteil_dicht_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_dicht_pct"], mit_wert["bedeckt_ha"])
    gruen = kennzahlen.gewichtetes_mittel(mit_wert["anteil_gruen_wasser_pct"], mit_wert["bedeckt_ha"])
    text = ("Kein Stadtteil mit genug Fläche." if stadtweit is None else
            f"Stadtweit gehören {zahl(stadtweit, 1)} % der Fläche zu Klimatopen dichter Bebauung (Stadt-, Innenstadt- "
            f"und dichtes Gewerbeklima), {zahl(gruen, 1)} % zu Grün-, Wald- und Wasserklimatopen.")
    melde(text)
    hinweise = list(stadtteile.hinweise)
    if leer.any():
        hinweise.append(f"{zahl(int(leer.sum()))} Splitterflächen unter 1 m² in der Karte sind weggelassen.")
    if not zuordnung.get("geprueft", False):
        hinweise.append(f"Die Zuordnung {zuordnung['_pfad']} ist noch nicht als geprüft markiert.")
    hinweise += [
        "Klimatopkarte der Klimaanalyse NRW 2026 (LANUK): abgeleitet aus Flächennutzung, Überbauung und Versiegelung, "
        "keine Messung. Stadtklima heißt über 40 % überbaut, dichtes Gewerbeklima über 70 % versiegelt und über 20 % "
        "überbaut (Methodik der Klimatopkarte).",
        "Dichte Klimatope sagen, wie das Mikroklima gebaut ist; wie warm es tatsächlich wird, zeigen die Themen Hitze "
        "in der Nacht und Hitze am Tag.",
        "Bezug ist die Fläche des Stadtteils, die die Karte abdeckt, nicht die Zahl der Menschen (E-007).",
    ]
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise + [f"Klassen aus der Zuordnung {zuordnung['_pfad']}."],
        quellen=[stadtteile.datensatz, DATENSATZ],
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="klimatope",
    gewicht="bedeckt_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Stadtklima nach Klimatopen je Stadtteil",
    frage="Welcher Anteil der Fläche eines Stadtteils gehört zu Klimatopen dichter Bebauung (Stadt-, Innenstadt- und dichtes Gewerbeklima)?",
    themen=("klima",),
    benoetigt=("stadtteile", DATENSATZ),
    rechne=rechne,
    kennzahl="anteil_dicht_pct",
    kennzahl_titel="Anteil der Fläche mit Klimatopen dichter Bebauung",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_dicht_pct", "dichte Bebauung", "prozent", balken=True),
        Spalte("anteil_locker_pct", "lockere Bebauung", "prozent"),
        Spalte("anteil_gruen_wasser_pct", "Grün, Wald, Wasser", "prozent"),
        Spalte("anteil_verkehr_pct", "Straßen und Bahn", "prozent"),
        Spalte("bedeckt_ha", "Fläche, ha", "zahl", stellen=1),
    ),
    zusammensetzung=(
        Spalte("anteil_dicht_pct", GRUPPEN["dicht"], "prozent"),
        Spalte("anteil_locker_pct", GRUPPEN["locker"], "prozent"),
        Spalte("anteil_verkehr_pct", GRUPPEN["verkehr"], "prozent"),
        Spalte("anteil_gruen_wasser_pct", GRUPPEN["gruen_wasser"], "prozent"),
    ),
    parameter=(
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken könnte.",
                  typ="zahl", selten=True),
    ),
    methodik="methodik/klimatope.md",
    thema_titel="Stadtklima (Klimatope)",
    kurz="Wie viel eines Stadtteils ist so dicht bebaut, dass dort ein typisches Stadt- oder Innenstadtklima herrscht?",
    richtung="neutral",
    lesehilfe="Gefärbt nach dem Anteil der Fläche, die die Klimatopkarte des Landes als Stadt-, Innenstadt- oder dichtes Gewerbeklima einstuft. Darunter steht, wie sich die ganze Fläche auf Grün, lockere und dichte Bebauung und Verkehr verteilt.",
    grenzen_kurz=(
        "Beschreibt, wie dicht gebaut wird, nicht wie warm es tatsächlich ist.",
        "Abgeleitet aus Karten der Nutzung, keine Messung.",
        "Bezug ist die Fläche, nicht die Zahl der Menschen.",
    ),
)
