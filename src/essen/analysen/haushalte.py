"""Privathaushalte je Stadtteil: Anteil der Haushalte mit Kindern und der Einpersonenhaushalte, seit 2007.

Grundlage ist die Tabelle „Anzahl der Privathaushalte in den Stadtteilen ab 2007“ des Amts für Statistik
(Stichtag 31.12., aus den Meldedaten gebildet). Eine Zeile je Stadtteil und Jahr; zugeordnet über die
Stadtteilnummer (Spalte Stadtteil = STADTT der Stadtteilgrenzen). Gerechnet wird nur mit Spalten, deren
Bedeutung der Name eindeutig sagt (E-016); Hauptkennzahl ist der Stand des letzten Jahres.

Methodik: docs/methodik/haushalte.md
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .. import laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile
from ..text import prozent, zahl
from .basis import Analyse, Ergebnis, Kontext, Spalte, Stufen, Zeitwert

DATENSATZ = "privathaushalte-stadtteile"
# Spalten der Datei → eigene Namen. Weitere Spalten (HH_EINE_PERSON_25B69, HH_MIT_3OM_KINDERN, HH_ALLEINERZIEHEND)
# sind nicht beschrieben und bleiben ungenutzt.
FELDER = {"Stadtteil": "stadtteil_nr", "Jahr": "jahr", "INSGESAMT": "haushalte", "HH_EINE_PERSON": "einpersonen",
          "HH_MIT_KINDERN": "mit_kindern", "BEVOELKERUNG_IN_HH": "personen"}

STUFEN = Stufen(
    grenzen=(0, 15, 18, 21, 24),
    farben=FARBSTUFEN["neutral"],
    texte=("unter 15 %", "15 bis 18 %", "18 bis 21 %", "21 bis 24 %", "24 % und mehr"),
)
STUFEN_EINPERSONEN = Stufen(
    grenzen=(0, 40, 45, 50, 55),
    farben=FARBSTUFEN["neutral"],
    texte=("unter 40 %", "40 bis 45 %", "45 bis 50 %", "50 bis 55 %", "55 % und mehr"),
)


def lies(pfad) -> pd.DataFrame:
    """Liest die CSV (Semikolon, Windows-Zeichensatz) und prüft die nötigen Spalten."""
    try:
        roh = pd.read_csv(pfad, sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        roh = pd.read_csv(pfad, sep=";", encoding="cp1252")
    fehlend = [f for f in FELDER if f not in roh.columns]
    if fehlend:
        raise ValueError(f"{pfad.name}: Spalten {', '.join(fehlend)} fehlen; hat sich der Aufbau geändert? "
                         "Erst untersuchen: uv run essen inspizieren privathaushalte-stadtteile")
    daten = roh[list(FELDER)].rename(columns=FELDER)
    for spalte in daten.columns:
        daten[spalte] = pd.to_numeric(daten[spalte], errors="coerce")
    if daten.isna().any().any():
        raise ValueError(f"{pfad.name}: Werte, die keine Zahlen sind. Erst untersuchen: "
                         "uv run essen inspizieren privathaushalte-stadtteile")
    return daten.astype(int)


def anteile(daten: pd.DataFrame) -> pd.DataFrame:
    return daten.assign(
        anteil_kinder_pct=100 * daten["mit_kindern"] / daten["haushalte"],
        anteil_einpersonen_pct=100 * daten["einpersonen"] / daten["haushalte"],
        personen_je_haushalt=daten["personen"] / daten["haushalte"],
    )


def rechne(kontext: Kontext) -> Ergebnis:
    melde = kontext.melde
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfade = laden.dateien(DATENSATZ, "*.csv")
    if not pfade:
        raise DatenFehlen([DATENSATZ])
    daten = anteile(lies(pfade[0]))
    letztes = int(daten["jahr"].max())
    erstes = int(daten["jahr"].min())
    melde(f"{len(daten)} Zeilen, {erstes} bis {letztes}. Ordne die Stadtteile über ihre Nummer zu …")

    nummern = gebiete[["gebiet_id", "name", "nummer"]].dropna(subset=["nummer"])
    nummern = nummern.assign(nummer=nummern["nummer"].astype(int))
    jahre = daten.merge(nummern, left_on="stadtteil_nr", right_on="nummer", how="inner")
    unbekannt = sorted(set(daten["stadtteil_nr"]) - set(nummern["nummer"]))
    ohne_daten = sorted(set(nummern["name"]) - set(jahre["name"]))
    hinweise = list(stadtteile.hinweise)
    if unbekannt:
        hinweise.append(f"Stadtteilnummern ohne Fläche in den Grenzen: {', '.join(map(str, unbekannt))}.")
    if ohne_daten:
        hinweise.append(f"Ohne Haushaltszahlen: {', '.join(ohne_daten)}.")
    if not len(jahre):
        raise ValueError("Keine Stadtteilnummer der Tabelle passt zu den Stadtteilgrenzen (Feld STADTT).")

    jahre = jahre.rename(columns={"name": "stadtteil"}).assign(vollstaendig=True)
    jahre = jahre[["gebiet_id", "stadtteil", "jahr", "haushalte", "personen", "mit_kindern", "einpersonen",
                   "anteil_kinder_pct", "anteil_einpersonen_pct", "personen_je_haushalt", "vollstaendig"]]
    jahre = jahre.sort_values(["gebiet_id", "jahr"]).round(
        {"anteil_kinder_pct": 1, "anteil_einpersonen_pct": 1, "personen_je_haushalt": 2}).reset_index(drop=True)

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"})
    stand = jahre[jahre["jahr"] == letztes].set_index("gebiet_id")
    frueh = jahre[jahre["jahr"] == erstes].set_index("gebiet_id")
    tabelle = tabelle.set_index("gebiet_id")
    for spalte in ("haushalte", "personen", "anteil_kinder_pct", "anteil_einpersonen_pct", "personen_je_haushalt"):
        tabelle[spalte] = stand[spalte]
    tabelle["anteil_kinder_aenderung"] = (stand["anteil_kinder_pct"] - frueh["anteil_kinder_pct"]).round(1)
    tabelle = tabelle.reset_index()

    summe = daten[daten["jahr"] == letztes][["haushalte", "mit_kindern", "einpersonen", "personen"]].sum()
    stadt = 100 * summe["mit_kindern"] / summe["haushalte"]
    text = (f"Ende {letztes} lebten in Essen {zahl(summe['personen'])} Menschen in {zahl(summe['haushalte'])} "
            f"Privathaushalten; in {prozent(stadt)} der Haushalte leben Kinder, "
            f"{prozent(100 * summe['einpersonen'] / summe['haushalte'])} sind Einpersonenhaushalte.")
    melde(text)
    hinweise += [
        "Haushalte bildet die Stadt aus den Meldedaten (gleiche Adresse, Familienbeziehungen, Namen); es sind "
        "Schätzungen, keine Befragung. Menschen in Heimen und Einrichtungen zählen nicht.",
        "Stichtag ist jeweils der 31.12. des Jahres.",
        "Die Spalte „mit Kindern“ ist im Portal nicht näher beschrieben (bis zu welchem Alter Kinder zählen).",
    ]
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id, tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=float(stadt), kennzahl_text=text, hinweise=hinweise,
        quellen=[stadtteile.datensatz, DATENSATZ], parameter={}, jahreswerte=jahre,
    )


ANALYSE = Analyse(
    id="haushalte",
    gewicht="haushalte",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Privathaushalte je Stadtteil",
    frage="In welchen Stadtteilen leben viele Familien mit Kindern, wo viele Menschen allein, und wie hat sich das "
          "seit 2007 verändert?",
    themen=("bevoelkerung",),
    benoetigt=("stadtteile", DATENSATZ),
    rechne=rechne,
    kennzahl="anteil_kinder_pct",
    kennzahl_titel="Haushalte mit Kindern",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_kinder_pct", "Haushalte mit Kindern", "prozent", stellen=1, balken=True),
        Spalte("anteil_einpersonen_pct", "Einpersonenhaushalte", "prozent", stellen=1),
        Spalte("personen_je_haushalt", "Personen je Haushalt", "zahl", stellen=2),
        Spalte("haushalte", "Haushalte", "zahl"),
        Spalte("anteil_kinder_aenderung", "Änderung seit 2007 (Prozentpunkte)", "zahl", stellen=1),
    ),
    methodik="methodik/haushalte.md",
    zeitachse=(
        Zeitwert("anteil_kinder_pct", "Anteil der Haushalte mit Kindern", "%", STUFEN, stellen=1),
        Zeitwert("anteil_einpersonen_pct", "Anteil der Einpersonenhaushalte", "%", STUFEN_EINPERSONEN, stellen=1),
    ),
    thema_titel="Haushalte",
    kurz="Wo wohnen viele Familien mit Kindern, wo leben viele Menschen allein?",
    richtung="neutral",
    lesehilfe="Jeder Stadtteil ist nach dem Anteil der Haushalte gefärbt, in denen Kinder leben (Stand Ende des "
              "letzten Jahres). Dunkleres Blau heißt mehr Familien mit Kindern. Das ist weder gut noch schlecht, "
              "hilft aber zu sehen, wo Hitze, Lärm oder fehlendes Grün besonders viele Kinder treffen.",
    grenzen_kurz=(
        "Haushalte sind aus den Meldedaten geschätzt, nicht gezählt.",
        "Ein Anteil sagt nichts über die Zahl: Ein großer Stadtteil mit kleinem Anteil kann mehr Familien haben.",
        "Wie alt „Kinder“ höchstens sind, nennt die Quelle nicht.",
    ),
)
