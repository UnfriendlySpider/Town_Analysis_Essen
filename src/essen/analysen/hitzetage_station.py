"""Hitzetage und Tropennächte an der DWD-Station Essen-Bredeney.

Zählt je Jahr Sommertage (Höchstwert ab 25 °C), heiße Tage (ab 30 °C), Tropennächte
(Tiefstwert ab 20 °C), Frost- und Eistage, dazu Jahresmittel und Niederschlag. Vergleicht
die letzten zehn vollständigen Jahre mit dem Bezugszeitraum 1991 bis 2020.

Daten: DWD Climate Data Center, Tageswerte Klima (historisch und aktuell), CC BY 4.0.
Methodik: docs/methodik/hitzetage-station.md
"""

from __future__ import annotations

import datetime as dt
import io
import zipfile

import numpy as np
import pandas as pd

from .. import laden
from ..geo import DatenFehlen
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte

AKTUELL_ID = "dwd-klima-essen-aktuell"
HISTORISCH_ID = "dwd-klima-essen-historisch"
FEHLWERT = -999
VOLLSTAENDIG_AB = 0.95  # Anteil der Tage mit Höchst- und Tiefstwert, ab dem ein Jahr zählt


def lies_tageswerte(zip_pfad) -> tuple[pd.DataFrame, dict]:
    """Liest die Datei produkt_klima_tag_*.txt aus einem DWD-ZIP. Gibt Tageswerte und Stationsangaben zurück."""
    with zipfile.ZipFile(zip_pfad) as zf:
        namen = [n for n in zf.namelist() if n.startswith("produkt_klima_tag") and n.endswith(".txt")]
        if not namen:
            raise ValueError(f"In {zip_pfad.name} fehlt die Datei produkt_klima_tag_*.txt.")
        roh = zf.read(namen[0]).decode("latin-1")
        station = {}
        geo = [n for n in zf.namelist() if n.startswith("Metadaten_Geographie") and n.endswith(".txt")]
        if geo:
            try:
                meta = pd.read_csv(io.StringIO(zf.read(geo[0]).decode("latin-1")), sep=";", skipinitialspace=True)
                meta.columns = [c.strip() for c in meta.columns]
                letzte = meta.iloc[-1]
                station = {
                    "name": str(letzte.get("Stationsname", "")).strip(),
                    "breite": float(letzte.get("Geogr.Breite")), "laenge": float(letzte.get("Geogr.Laenge")),
                    "hoehe_m": float(letzte.get("Stationshoehe")),
                }
            except (ValueError, TypeError, IndexError, KeyError):  # Metadaten sind nett, aber nicht nötig
                station = {}
    df = pd.read_csv(io.StringIO(roh), sep=";", skipinitialspace=True, na_values=[FEHLWERT, str(FEHLWERT)],
                     dtype={"MESS_DATUM": str})
    df.columns = [c.strip() for c in df.columns]
    df["datum"] = pd.to_datetime(df["MESS_DATUM"].str.strip(), format="%Y%m%d")
    for spalte in ("TXK", "TNK", "TMK", "RSK"):
        if spalte in df.columns:
            df[spalte] = pd.to_numeric(df[spalte], errors="coerce").where(lambda s: s > FEHLWERT + 1)
    station["id"] = str(df["STATIONS_ID"].iloc[0]).strip() if "STATIONS_ID" in df.columns and len(df) else ""
    return df[["datum", *[s for s in ("TXK", "TNK", "TMK", "RSK") if s in df.columns]]], station


def tageswerte() -> tuple[pd.DataFrame, dict, list[str]]:
    """Historische und aktuelle Werte zusammen. Bei Überschneidung gilt der geprüfte historische Wert."""
    teile, station, quellen = [], {}, []
    for kennung in (HISTORISCH_ID, AKTUELL_ID):
        if not laden.vorhanden(kennung):
            continue
        for zip_pfad in laden.dateien(kennung, "*.zip"):
            df, meta = lies_tageswerte(zip_pfad)
            df["herkunft"] = kennung
            teile.append(df)
            station = station or meta
        quellen.append(kennung)
    if not teile:
        raise DatenFehlen([HISTORISCH_ID, AKTUELL_ID])
    alle = pd.concat(teile, ignore_index=True)
    alle["vorrang"] = (alle["herkunft"] == HISTORISCH_ID).astype(int)
    alle = alle.sort_values(["datum", "vorrang"]).drop_duplicates("datum", keep="last").drop(columns="vorrang")
    return alle.reset_index(drop=True), station, quellen


def jahreswerte(tage: pd.DataFrame, heute: dt.date | None = None) -> pd.DataFrame:
    """Eine Zeile je Jahr mit Kenntagen nach den Definitionen des DWD."""
    heute = heute or dt.date.today()
    txk, tnk = tage["TXK"], tage["TNK"]
    merkmale = pd.DataFrame({
        "jahr": tage["datum"].dt.year,
        "tage_mit_werten": txk.notna() & tnk.notna(),
        "sommertage": txk >= 25,
        "heisse_tage": txk >= 30,
        "tropennaechte": tnk >= 20,
        "frosttage": tnk < 0,
        "eistage": txk < 0,
    })
    gruppen = tage.assign(jahr=merkmale["jahr"]).groupby("jahr")
    tabelle = merkmale.groupby("jahr").sum().astype(int)
    tabelle["hoechstwert_c"] = gruppen["TXK"].max()
    tabelle["tiefstwert_c"] = gruppen["TNK"].min()
    tabelle["jahresmittel_c"] = gruppen["TMK"].mean() if "TMK" in tage.columns else np.nan
    tabelle["niederschlag_mm"] = gruppen["RSK"].sum(min_count=300) if "RSK" in tage.columns else np.nan
    tage_im_jahr = pd.Series([366 if pd.Timestamp(j, 12, 31).is_leap_year else 365 for j in tabelle.index],
                             index=tabelle.index)
    tabelle["vollstaendig"] = (tabelle["tage_mit_werten"] / tage_im_jahr >= VOLLSTAENDIG_AB) & (tabelle.index < heute.year)
    return tabelle.reset_index().round({"hoechstwert_c": 1, "tiefstwert_c": 1, "jahresmittel_c": 2, "niederschlag_mm": 0})


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    tage, station, quellen = tageswerte()
    kontext.melde(f"Tageswerte: {zahl(len(tage))} Tage von {tage['datum'].min():%d.%m.%Y} bis {tage['datum'].max():%d.%m.%Y}")
    tabelle = jahreswerte(tage)
    voll = tabelle[tabelle["vollstaendig"]]
    von, bis = int(p["bezug_von"]), int(p["bezug_bis"])
    bezug = voll[(voll["jahr"] >= von) & (voll["jahr"] <= bis)]
    letzte = voll.tail(10)
    hinweise = []
    if len(bezug) < 0.8 * (bis - von + 1):
        hinweise.append(f"Im Bezugszeitraum {von} bis {bis} sind nur {len(bezug)} Jahre vollständig.")
    if "historisch" not in " ".join(quellen):
        hinweise.append("Nur aktuelle Werte geladen. Für lange Reihen dwd-klima-essen-historisch laden.")
    mittel_bezug = float(bezug["heisse_tage"].mean()) if len(bezug) else None
    mittel_letzte = float(letzte["heisse_tage"].mean()) if len(letzte) else None
    if mittel_letzte is None:
        text = "Noch kein vollständiges Jahr in den Daten."
    elif mittel_bezug is None:
        text = f"Heiße Tage pro Jahr, Mittel der letzten {len(letzte)} vollständigen Jahre: {zahl(mittel_letzte, 1)}."
    else:
        text = (f"Heiße Tage pro Jahr: {von} bis {bis} im Mittel {zahl(mittel_bezug, 1)}, "
                f"{int(letzte['jahr'].min())} bis {int(letzte['jahr'].max())} im Mittel {zahl(mittel_letzte, 1)}.")
    offen = tabelle[~tabelle["vollstaendig"]]
    if len(offen):
        hinweise.append("Nicht in Mittelwerten und Rangfolgen, weil unvollständig: "
                        + ", ".join(f"{int(z.jahr)} ({int(z.tage_mit_werten)} Tage)" for z in offen.itertuples())
                        + ". Werte des laufenden Jahres sind vorläufig (DWD „recent“, nicht abschließend geprüft).")
    if station.get("name"):
        hinweise.append(f"Station {station['name']} (ID {station.get('id', '?')}), {zahl(station.get('hoehe_m'))} m.")
    kontext.melde(text)
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        kennzahl_stadt=mittel_letzte,
        kennzahl_text=text,
        hinweise=hinweise,
        quellen=quellen,
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="hitzetage-station",
    titel="Hitzetage und Tropennächte an der Station Essen-Bredeney",
    frage="Wie oft wird es in Essen heiß, und hat das zugenommen?",
    themen=("klima",),
    benoetigt=(AKTUELL_ID,),
    optional=(HISTORISCH_ID,),
    rechne=rechne,
    raumbezug="station",
    kennzahl="heisse_tage",
    kennzahl_titel="Heiße Tage (Höchstwert ab 30 °C)",
    einheit="Tage",
    spalten=(
        Spalte("jahr", "Jahr", "text"),
        Spalte("sommertage", "Sommertage", "zahl"),
        Spalte("heisse_tage", "heiße Tage", "zahl", balken=True),
        Spalte("tropennaechte", "Tropennächte", "zahl"),
        Spalte("jahresmittel_c", "Jahresmittel °C", "zahl", stellen=1),
    ),
    parameter=(
        Parameter("bezug_von", "Vergleichszeitraum von", 1991,
                  "Mit diesem Zeitraum werden die letzten zehn Jahre verglichen. 1991 bis 2020 ist der übliche "
                  "Vergleichszeitraum in der Klimaforschung.", typ="ganzzahl", selten=True),
        Parameter("bezug_bis", "Vergleichszeitraum bis", 2020, "Ende des Vergleichszeitraums.", typ="ganzzahl",
                  selten=True),
    ),
    methodik="methodik/hitzetage-station.md",
    thema_titel="Heiße Tage seit 1935",
    kurz="Wie oft wurde es an der Wetterstation Essen-Bredeney heiß, und hat das über die Jahrzehnte zugenommen?",
    richtung="hoch_schlecht",
    lesehilfe="Jeder Punkt auf der Linie ist ein Jahr und zeigt, wie viele Tage es an der Station gab, zum Beispiel heiße Tage mit mindestens 30 °C. Einzelne Jahre schwanken stark; aussagekräftig ist der Verlauf über Jahrzehnte. Unvollständige Jahre, etwa das laufende, zählen nicht zu den Mittelwerten.",
    grenzen_kurz=(
        "Eine einzige Station im Süden der Stadt; in der Innenstadt ist es oft wärmer.",
        "Die Station wurde 1965 verlegt; frühe und späte Jahre sind nur bedingt vergleichbar.",
        "Werte des laufenden Jahres sind vorläufig.",
    ),
)
