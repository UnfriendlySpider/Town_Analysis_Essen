"""Kennzahlen je Stadtbezirk (E-018): aus den gespeicherten Ergebnissen der Stadtteile, ohne neu zu rechnen.

Ein Bezirkswert entsteht wie der stadtweite Wert einer Analyse: als Mittel der Stadtteile, gewichtet mit derselben
Bezugsgröße (`Analyse.gewicht`, z. B. die bebaute Fläche bei der Hitze in der Nacht). Bei Anteilen ist das gleich
„Summe der belasteten Fläche durch Summe der Bezugsfläche“, nicht das Mittel der Prozente.

Welcher Stadtteil zu welchem Bezirk gehört, steht in der Stadtteildatei (Feld laut Katalog `felder.bezirk`).
Die Bezirke heißen „Stadtbezirk I“ bis „IX“; Namen der Bezirke liegen in keiner der Quellen vor.
"""

from __future__ import annotations

import warnings

import pandas as pd
import pyogrio

from . import analysen, kennzahlen, laden
from .analysen.basis import Ergebnis
from .geo import STADTTEILE_ID, vektordatei

ROEMISCH = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
_GEMERKT: dict[tuple, dict[str, int]] = {}


def name(bezirk: int) -> str:
    return f"Stadtbezirk {ROEMISCH[bezirk - 1]}" if 1 <= bezirk <= len(ROEMISCH) else f"Stadtbezirk {bezirk}"


def zuordnung(katalog) -> dict[str, int]:
    """gebiet_id des Stadtteils → Bezirksnummer. Leer, wenn die Stadtteile fehlen oder der Katalog kein Feld nennt.

    gebiet_id ist die Stadtteilnummer als Text, wie in geo.lade_stadtteile."""
    ds = katalog.datensatz(STADTTEILE_ID)
    felder = ds.felder or {}
    if not laden.vorhanden(ds) or not felder.get("bezirk") or not felder.get("nummer"):
        return {}
    pfad = vektordatei(ds.id)
    stempel = (str(pfad), pfad.stat().st_mtime, felder["nummer"], felder["bezirk"])
    if stempel not in _GEMERKT:
        vorhanden = set(pyogrio.read_info(pfad)["fields"])
        if not {felder["nummer"], felder["bezirk"]} <= vorhanden:
            return {}
        with warnings.catch_warnings():  # wie geo.lies_vektor: GDAL-Hinweise zu überzähligen Koordinaten
            warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")
            daten = pyogrio.read_dataframe(pfad, read_geometry=False, columns=[felder["nummer"], felder["bezirk"]])
        nummer = pd.to_numeric(daten[felder["nummer"]], errors="coerce")
        bezirk = pd.to_numeric(daten[felder["bezirk"]], errors="coerce")
        gueltig = nummer.notna() & bezirk.notna()
        _GEMERKT[stempel] = dict(zip(nummer[gueltig].astype(int).astype(str), bezirk[gueltig].astype(int), strict=True))
    return _GEMERKT[stempel]


def gewicht_spalte(analyse, tabelle: pd.DataFrame) -> str | None:
    """Die Gewichtsspalte der Analyse; fehlt sie (z. B. ohne Gewässerabzug), die Fläche des Stadtteils."""
    if not analyse.gewicht:
        return None
    for spalte in (analyse.gewicht, "flaeche_ha"):
        if spalte in tabelle.columns:
            return spalte
    return None


def je_bezirk(katalog, analyse_id: str, ergebnis: Ergebnis | None = None) -> pd.DataFrame:
    """Eine Zeile je Bezirk: bezirk, name, wert, gewicht (Summe der Bezugsgröße), stadtteile (mit Wert).

    Leer, wenn die Analyse keine Bezirkswerte hat (z. B. Mehrfachbelastung, Stationen) oder Daten fehlen."""
    analyse = analysen.hole(analyse_id)
    ergebnis = ergebnis or Ergebnis.ansehen(analyse_id)
    leer = pd.DataFrame(columns=["bezirk", "name", "wert", "gewicht", "stadtteile"])
    if ergebnis is None or analyse.raumbezug != "stadtteil" or "gebiet_id" not in ergebnis.tabelle.columns:
        return leer
    tabelle = ergebnis.tabelle
    spalte = gewicht_spalte(analyse, tabelle)
    bezirke = zuordnung(katalog)
    if spalte is None or not bezirke or analyse.kennzahl not in tabelle.columns:
        return leer
    daten = tabelle.assign(bezirk=tabelle["gebiet_id"].astype(str).map(bezirke)).dropna(subset=["bezirk"])
    zeilen = []
    for bezirk, teil in daten.groupby("bezirk"):
        werte, gewichte = teil[analyse.kennzahl], teil[spalte]
        zeilen.append({"bezirk": int(bezirk), "name": name(int(bezirk)),
                       "wert": kennzahlen.gewichtetes_mittel(werte, gewichte),
                       "gewicht": float(gewichte[werte.notna()].sum()), "stadtteile": int(werte.notna().sum())})
    return pd.DataFrame(zeilen, columns=leer.columns).sort_values("bezirk").reset_index(drop=True) if zeilen else leer


def bezirk_von(katalog, gebiet_id: str) -> int | None:
    return zuordnung(katalog).get(str(gebiet_id))
