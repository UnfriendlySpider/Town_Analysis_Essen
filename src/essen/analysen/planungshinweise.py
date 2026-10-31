"""Handlungsbedarf bei Hitze je Stadtteil.

Grundlage ist die Planungshinweiskarte der Klimaanalyse NRW 2026 (LANUK): Für jede bebaute Fläche (Wirkraum)
eine Handlungspriorität 1 bis 6, abgeleitet aus der nächtlichen Überwärmung im typischen und im extremen
Szenario, zusammengefasst zu vier Stufen (dringend, erweitert, mäßig, kein Handlungsbedarf). Für jeden
Stadtteil: welcher Anteil der bebauten Fläche hat dringenden Handlungsbedarf?

Stufen und Felder stehen in katalog/zuordnungen/klimaanalyse-planungshinweise.yaml.
Methodik: docs/methodik/planungshinweise.md
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .. import einwohner, kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_im_stadtgebiet, vektordatei
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen
from .hitze_nacht import ZuordnungFehlt, lade_zuordnung

DATENSATZ = "klimaanalyse-planungshinweise"
STUFEN_REIHE = ("dringend", "erweitert", "maessig", "kein")

STUFEN = Stufen(
    grenzen=(0, 20, 40, 60, 80),
    farben=FARBSTUFEN["waerme"],
    texte=("unter 20 %", "20 bis 40 %", "40 bis 60 %", "60 bis 80 %", "80 % und mehr"),
    keine_daten_text="zu wenig bebaut, kein Anteil",
)


def _zuordnung() -> dict:
    zuordnung = lade_zuordnung(DATENSATZ)
    noetig = ("layer", "feld", "textfeld", "gemeindefeld", "gemeinde", "klassen", "stufen")
    if not zuordnung or any(not zuordnung.get(k) for k in noetig):
        raise ZuordnungFehlt(f"katalog/zuordnungen/{DATENSATZ}.yaml fehlt oder nennt nicht alle Angaben "
                             f"({', '.join(noetig)}).")
    if set(zuordnung["stufen"]) != set(STUFEN_REIHE):
        raise ZuordnungFehlt(f"{zuordnung['_pfad']}: stufen müssen {', '.join(STUFEN_REIHE)} sein.")
    return zuordnung


def stufe_je_flaeche(flaechen: pd.DataFrame, zuordnung: dict) -> pd.Series:
    """Stufe (dringend …) je Fläche. Unbekannte Priorität oder ein Hinweistext, der nicht zur Stufe passt,
    bricht ab (E-009)."""
    ort = zuordnung["_pfad"]
    feld, textfeld = zuordnung["feld"], zuordnung["textfeld"]
    for spalte in (feld, textfeld):
        if spalte not in flaechen.columns:
            raise ZuordnungFehlt(f"{ort}: Feld {spalte} fehlt (vorhanden: {', '.join(flaechen.columns)}).")
    nach_text = {str(k["text"]).strip(): k["stufe"] for k in zuordnung["klassen"].values()}
    texte = flaechen[feld].astype(str).str.strip()
    offen = sorted(set(texte) - set(nach_text))
    if offen:
        raise ZuordnungFehlt(f"{ort}: In {feld} kommen Werte ohne Beschreibung vor: {', '.join(offen)}.")
    stufe = texte.map(nach_text)
    anfang = stufe.map({s: str(zuordnung["stufen"][s]["anfang"]) for s in STUFEN_REIHE})
    passt = [str(t).strip().startswith(a) for t, a in zip(flaechen[textfeld], anfang, strict=True)]
    if not all(passt):
        falsch = sorted({f"{p} = „{str(t)[:40]}…“" for p, t, ok in zip(texte, flaechen[textfeld], passt, strict=True) if not ok})
        raise ZuordnungFehlt(f"{ort}: {feld} und {textfeld} passen nicht zur Zuordnung: {', '.join(falsch[:5])}.")
    return stufe


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    zuordnung = _zuordnung()
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfad = vektordatei(DATENSATZ)
    melde(f"Planungshinweiskarte: {pfad.name}, Layer {zuordnung['layer']}")
    gemeinde = str(zuordnung["gemeinde"]).replace("'", "''")
    flaechen = lies_im_stadtgebiet(pfad, layer=zuordnung["layer"], where=f"{zuordnung['gemeindefeld']} = '{gemeinde}'",
                                   columns=[zuordnung["feld"], zuordnung["textfeld"]])
    flaechen["stufe"] = stufe_je_flaeche(flaechen, zuordnung)
    flaechen["geometry"] = kennzahlen.gueltig(flaechen.geometry)  # 11 Flächen in Essen sind ungültig
    leer = flaechen.geometry.is_empty
    flaechen = flaechen[~leer]
    melde(f"  {zahl(len(flaechen))} Flächen im Wirkraum. Verschneide mit den Stadtteilen …")
    je_stufe = kennzahlen.flaechen_nach_klasse(gebiete, flaechen[["stufe", "geometry"]], list(STUFEN_REIHE),
                                               spalte="stufe") / 1e4

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    for stufe in STUFEN_REIHE:
        tabelle[f"{stufe}_ha"] = je_stufe[stufe].reindex(tabelle.index).fillna(0.0)
    tabelle["wirkraum_ha"] = tabelle[[f"{s}_ha" for s in STUFEN_REIHE]].sum(axis=1)
    bezug = tabelle["wirkraum_ha"].where(tabelle["wirkraum_ha"] > 0)
    for stufe in STUFEN_REIHE:
        tabelle[f"anteil_{stufe}_pct"] = 100 * tabelle[f"{stufe}_ha"] / bezug
    minimum = float(p["min_wirkraum_ha"])
    tabelle = kennzahlen.mindestbezug(tabelle, "wirkraum_ha", minimum, [f"anteil_{s}_pct" for s in STUFEN_REIHE],
                                      f"unter {minimum:g} ha bebaut, Anteil nicht ausgewiesen")
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha"))})

    einwohner_satz = None
    if einwohner.vorhanden():
        melde("Schätze die Einwohner in Flächen mit dringendem Handlungsbedarf (Zensus-Gitter) …")
        dringend = flaechen[flaechen["stufe"] == "dringend"][["geometry"]].to_crs(ZIEL_CRS)
        tabelle, satz = einwohner.ergaenze(tabelle, einwohner.in_flaeche(gebiete, dringend))
        einwohner_satz = (f"{satz[:-1]} wohnen in Zellen mit Flächen mit dringendem Handlungsbedarf, anteilig nach "
                          f"Fläche. {einwohner.HINWEIS}")
    mit_wert = tabelle.dropna(subset=["anteil_dringend_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_dringend_pct"], mit_wert["wirkraum_ha"])
    text = ("Kein Stadtteil mit genug bebauter Fläche." if stadtweit is None else
            f"Stadtweit haben {zahl(stadtweit, 1)} % der bebauten Fläche dringenden Handlungsbedarf wegen Hitze "
            "(Planungshinweiskarte, Modell).")
    melde(text)
    hinweise = list(stadtteile.hinweise)
    if leer.any():
        hinweise.append(f"{zahl(int(leer.sum()))} ungültige Flächen der Karte haben nach der Reparatur keine Fläche "
                        "mehr und fallen weg.")
    if not zuordnung.get("geprueft", False):
        hinweise.append(f"Die Zuordnung {zuordnung['_pfad']} ist noch nicht als geprüft markiert.")
    hinweise += [
        "Planungshinweiskarte der Klimaanalyse NRW 2026 (LANUK, Modell): Handlungspriorität 1 und 2 heißen "
        "„dringender Handlungsbedarf“, 3 und 4 „erweitert“, 5 „mäßig“, 6 „kein“. Grundlage ist die nächtliche "
        "Überwärmung im typischen und im extremen Szenario.",
        "Bezug ist die bebaute Fläche (Wirkraum) des Stadtteils, nicht die Zahl der Menschen (E-007).",
        "Die Stufen sind Empfehlungen für die Planung, keine Messung und kein Grenzwert.",
    ]
    if einwohner_satz:
        hinweise.append(einwohner_satz)
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise + [f"Stufen aus der Zuordnung {zuordnung['_pfad']}."],
        quellen=[stadtteile.datensatz, DATENSATZ] + ([einwohner.DATENSATZ] if einwohner_satz else []),
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="planungshinweise",
    gewicht="wirkraum_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Handlungsbedarf bei Hitze je Stadtteil",
    frage="Welcher Anteil der bebauten Fläche eines Stadtteils hat laut Planungshinweiskarte dringenden Handlungsbedarf wegen Hitze?",
    themen=("klima",),
    benoetigt=("stadtteile", DATENSATZ),
    optional=(einwohner.DATENSATZ,),
    rechne=rechne,
    kennzahl="anteil_dringend_pct",
    kennzahl_titel="Anteil der bebauten Fläche mit dringendem Handlungsbedarf",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_dringend_pct", "dringend", "prozent", balken=True),
        Spalte("anteil_erweitert_pct", "erweitert", "prozent"),
        Spalte("anteil_maessig_pct", "mäßig", "prozent"),
        Spalte("anteil_kein_pct", "kein", "prozent"),
        Spalte("wirkraum_ha", "bebaut, ha", "zahl", stellen=1),
        Spalte("anteil_einwohner_pct", "Einwohner betroffen", "prozent"),
    ),
    zusammensetzung=(
        Spalte("anteil_dringend_pct", "dringender Handlungsbedarf", "prozent"),
        Spalte("anteil_erweitert_pct", "erweiterter Handlungsbedarf", "prozent"),
        Spalte("anteil_maessig_pct", "mäßiger Handlungsbedarf", "prozent"),
        Spalte("anteil_kein_pct", "kein Handlungsbedarf", "prozent"),
    ),
    parameter=(
        Parameter("min_wirkraum_ha", "Mindestfläche bebaut in Hektar", 5.0,
                  "Stadtteile mit weniger bebauter Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken "
                  "könnte.", typ="zahl", selten=True),
    ),
    methodik="methodik/planungshinweise.md",
    thema_titel="Handlungsbedarf bei Hitze",
    kurz="Wo sollte die Stadt laut Klimaanalyse des Landes am dringendsten etwas gegen Hitze tun?",
    richtung="hoch_schlecht",
    lesehilfe="Gefärbt nach dem Anteil der bebauten Fläche, für die die Planungshinweiskarte des Landes dringenden Handlungsbedarf wegen Hitze sieht: mehr Grün, Schatten, Wasser, weniger versiegelter Boden. Dunkler heißt mehr solche Fläche.",
    grenzen_kurz=(
        "Eine Empfehlung aus einem Modell der Nacht, keine Messung.",
        "Bezug ist die bebaute Fläche, nicht die Zahl der Menschen.",
        "Sagt nicht, was im Stadtteil schon geplant oder umgesetzt ist.",
    ),
)
