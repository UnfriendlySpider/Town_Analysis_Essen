"""Zeitreihen aus gespeicherten Analysen: Reihen, Trend, Vergleichswerte.

Stationsanalysen haben je Jahr eine Zeile. Die Rasteranalyse hitzetage-raster hat dazu Jahreswerte je
Stadtteil (Ergebnis.jahreswerte); daraus werden Reihen für einzelne Stadtteile.
Liest nur gespeicherte Ergebnisse, rechnet nichts neu. Grundlage für die App-Seite „Zeitreihen“.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import analysen
from .analysen.basis import Ergebnis

# Reihen je Analyse: Spalte → Beschriftung. Bei luft-station kommen die Stationen (Spalten wert_*) dazu.
REIHEN = {
    "hitzetage-station": {"sommertage": "Sommertage (ab 25 °C)", "heisse_tage": "Heiße Tage (ab 30 °C)",
                          "tropennaechte": "Tropennächte (Tiefstwert ab 20 °C)", "jahresmittel_c": "Jahresmittel °C"},
    "luft-station": {"hoechstes_jahresmittel_ug_m3": "höchstes Jahresmittel", "mittel_stationen_ug_m3": "Mittel der Stationen"},
    "hitzetage-raster": {"heisse_tage": "Heiße Tage (ab 30 °C)", "sommertage": "Sommertage (ab 25 °C)",
                         "jahresmittel_c": "Jahresmittel °C"},
}
JE_STADTTEIL = ("hitzetage-raster",)  # Analysen mit Jahreswerten je Stadtteil
STATION_NAME = "Messstation Bredeney"
ART = {"heisse_tage": "heiße Tage", "sommertage": "Sommertage", "jahresmittel_c": "°C"}  # für Sätze
# Lesehilfe für das Liniendiagramm, wo die der Analyse eine Karte beschreibt
LESEHILFE = {
    "hitzetage-raster": "Jede Linie ist ein Stadtteil (oder ganz Essen), jeder Punkt ein Jahr. Einzelne Jahre "
                        "schwanken stark; aussagekräftig ist der Verlauf über Jahrzehnte. Die Werte stammen aus einem "
                        "Raster des Wetterdienstes; Stadtteile nebeneinander unterscheiden sich darin nur wenig.",
}
BEZUG = (1961, 1990)  # üblicher Vergleichszeitraum des Wetterdienstes

# Ereignisse, die eine Reihe unterbrechen (senkrechte Marke im Diagramm). Beleg: docs/methodik/hitzetage-station.md
MARKEN = {
    "hitzetage-station": {1965: "Station verlegt (1965)"},
}


@dataclass
class Zeitreihe:
    analyse_id: str
    titel: str
    einheit: str
    daten: pd.DataFrame                      # jahr, reihe, wert, vollstaendig
    vergleich: dict[str, float] = field(default_factory=dict)   # Beschriftung → Wert (waagerechte Linien)
    parameter: dict = field(default_factory=dict)
    marken: dict[int, str] = field(default_factory=dict)          # Jahr → Ereignis (senkrechte Linien)


def _stationsname(analyse_id: str) -> dict[str, str]:
    """Spalte wert_<Code> → „Name (Code)“, soweit die Stationsliste geladen ist."""
    if analyse_id != "luft-station":
        return {}
    try:
        from .analysen.luft_station import stationen_in_essen
        return {f"wert_{z.code}": f"{z.name} ({z.code})" for z in stationen_in_essen().itertuples()}
    except Exception:  # noqa: BLE001 - ohne Stationsliste bleibt der Code als Name
        return {}


def _beschriftungen(analyse_id: str, spalten) -> dict[str, str]:
    namen = _stationsname(analyse_id)
    return {**{k: v for k, v in REIHEN[analyse_id].items() if k in spalten},
            **{c: namen.get(c, c.removeprefix("wert_")) for c in spalten if c.startswith("wert_")}}


def verfuegbare() -> list[str]:
    return [a for a in REIHEN if Ergebnis.ansehen(a) is not None]


def zeitreihe(analyse_id: str, reihen: list[str] | None = None, ergebnis: Ergebnis | None = None) -> Zeitreihe:
    """Lange Tabelle der gewählten Reihen (Standard: alle) aus dem gespeicherten oder übergebenen Ergebnis."""
    ergebnis = ergebnis or Ergebnis.laden(analyse_id)
    if ergebnis is None:
        raise ValueError(f"Kein gespeichertes Ergebnis für {analyse_id}. Erst rechnen: uv run essen analyse {analyse_id}")
    tabelle = ergebnis.tabelle
    moeglich = _beschriftungen(analyse_id, tabelle.columns)
    gewaehlt = [r for r in (reihen or list(moeglich)) if r in tabelle.columns]
    voll = tabelle["vollstaendig"].astype(bool) if "vollstaendig" in tabelle.columns else pd.Series(True, index=tabelle.index)
    lang = tabelle.assign(vollstaendig=voll).melt(id_vars=["jahr", "vollstaendig"], value_vars=gewaehlt,
                                                  var_name="spalte", value_name="wert").dropna(subset=["wert"])
    lang["reihe"] = lang["spalte"].map(moeglich)
    analyse = analysen.hole(analyse_id)
    vergleich = {}
    if analyse_id == "luft-station":
        from .analysen.luft_station import GRENZWERTE
        g = GRENZWERTE[ergebnis.parameter.get("schadstoff", "no2")]
        vergleich = {f"Grenzwert {g['eu']}": g["eu"], f"Grenzwert ab 2030: {g['eu_2030']}": g["eu_2030"],
                     f"WHO-Richtwert {g['who']}": g["who"]}
    return Zeitreihe(analyse_id, analyse.titel, analyse.einheit, lang[["jahr", "reihe", "spalte", "wert", "vollstaendig"]],
                     vergleich, dict(ergebnis.parameter), dict(MARKEN.get(analyse_id, {})))


def moegliche_reihen(analyse_id: str, ergebnis: Ergebnis | None = None) -> dict[str, str]:
    ergebnis = ergebnis or Ergebnis.laden(analyse_id)
    return _beschriftungen(analyse_id, ergebnis.tabelle.columns if ergebnis is not None else [])


def trend(daten: pd.DataFrame, von: int | None = None, bis: int | None = None) -> pd.DataFrame:
    """Linearer Trend je Reihe über vollständige Jahre: Änderung je 10 Jahre, Anzahl Jahre, Zeitraum."""
    zeilen = []
    for reihe, teil in daten[daten["vollstaendig"]].groupby("reihe"):
        if von is not None:
            teil = teil[teil["jahr"] >= von]
        if bis is not None:
            teil = teil[teil["jahr"] <= bis]
        if len(teil) < 5:
            continue
        steigung = np.polyfit(teil["jahr"].astype(float), teil["wert"].astype(float), 1)[0]
        zeilen.append({"reihe": reihe, "je_10_jahre": 10 * steigung, "jahre": len(teil),
                       "von": int(teil["jahr"].min()), "bis": int(teil["jahr"].max())})
    return pd.DataFrame(zeilen, columns=["reihe", "je_10_jahre", "jahre", "von", "bis"])


def trendlinien(daten: pd.DataFrame) -> pd.DataFrame:
    """Je Reihe zwei Punkte (erstes und letztes vollständiges Jahr) auf der Trendgeraden, zum Einzeichnen.

    Gleiche Regel wie trend(): nur vollständige Jahre, mindestens 5."""
    zeilen = []
    for reihe, teil in daten[daten["vollstaendig"]].groupby("reihe"):
        if len(teil) < 5:
            continue
        steigung, achse = np.polyfit(teil["jahr"].astype(float), teil["wert"].astype(float), 1)
        for jahr in (int(teil["jahr"].min()), int(teil["jahr"].max())):
            zeilen.append({"reihe": reihe, "jahr": jahr, "wert": steigung * jahr + achse})
    return pd.DataFrame(zeilen, columns=["reihe", "jahr", "wert"])


def zeitraum_mittel(daten: pd.DataFrame, von: int, bis: int, mindestens: int = 20) -> pd.DataFrame:
    """Mittel je Reihe über vollständige Jahre von–bis, nur wenn mindestens so viele Jahre vorliegen.

    Für Vergleiche wie „1961–1990 gegenüber den letzten zehn Jahren“."""
    teil = daten[daten["vollstaendig"] & (daten["jahr"] >= von) & (daten["jahr"] <= bis)]
    gruppen = teil.groupby("reihe")["wert"].agg(["mean", "count"]).reset_index()
    gruppen = gruppen[gruppen["count"] >= mindestens]
    return gruppen.rename(columns={"mean": "mittel", "count": "jahre"})[["reihe", "mittel", "jahre"]]


# -------------------------------------------------------------------- je Stadtteil

def erstes_jahr(analyse_id: str, spalte: str | None = None) -> int | None:
    """Erstes Jahr mit Werten im gespeicherten Ergebnis (Jahreswerte je Stadtteil oder Tabelle je Jahr)."""
    ergebnis = Ergebnis.ansehen(analyse_id)
    if ergebnis is None:
        return None
    daten = ergebnis.jahreswerte if ergebnis.jahreswerte is not None else ergebnis.tabelle
    if "jahr" not in daten.columns:
        return None
    if spalte and spalte in daten.columns:
        daten = daten[daten[spalte].notna()]
    return int(daten["jahr"].min()) if len(daten) else None


def stellen(analyse_id: str, einheit: str) -> int:
    """Nachkommastellen für Diagramm und Trend: Temperaturen aus dem Raster ändern sich in Hundertsteln."""
    return 2 if analyse_id in JE_STADTTEIL and einheit == "°C" else 1


def einheit_von(spalte: str) -> str:
    return "°C" if spalte.endswith("_c") else "Tage"


def stadtteile(analyse_id: str = "hitzetage-raster", ergebnis: Ergebnis | None = None) -> dict[str, str]:
    """Wählbare Gebiete mit Jahreswerten: gebiet_id → Name, „Essen gesamt“ zuerst, dann nach Namen."""
    ergebnis = ergebnis or Ergebnis.laden(analyse_id)
    if ergebnis is None or ergebnis.jahreswerte is None:
        return {}
    paare = ergebnis.jahreswerte[["gebiet_id", "stadtteil"]].drop_duplicates()
    from .analysen.hitzetage_raster import ESSEN_ID
    essen = paare[paare["gebiet_id"] == ESSEN_ID]
    rest = paare[paare["gebiet_id"] != ESSEN_ID].sort_values("stadtteil")
    return dict(zip(pd.concat([essen, rest])["gebiet_id"], pd.concat([essen, rest])["stadtteil"], strict=True))


def stadtteil_reihe(spalte: str, gebiete: list[str], station: bool = False, analyse_id: str = "hitzetage-raster",
                    ergebnis: Ergebnis | None = None) -> Zeitreihe:
    """Eine Kennzahl (z. B. heisse_tage) für mehrere Gebiete; jede Reihe heißt wie ihr Gebiet.

    Mit `station` kommt die Messreihe von hitzetage-station dazu, soweit sie gespeichert ist."""
    ergebnis = ergebnis or Ergebnis.laden(analyse_id)
    if ergebnis is None or ergebnis.jahreswerte is None:
        raise ValueError(f"Keine Jahreswerte für {analyse_id}. Erst rechnen: uv run essen analyse {analyse_id}")
    jahre = ergebnis.jahreswerte
    if spalte not in jahre.columns:
        raise ValueError(f"Die Reihe {spalte} fehlt. Vorhanden: {', '.join(c for c in REIHEN[analyse_id] if c in jahre.columns)}")
    namen = stadtteile(analyse_id, ergebnis)
    teil = jahre[jahre["gebiet_id"].isin(gebiete)].dropna(subset=[spalte])
    daten = pd.DataFrame({"jahr": teil["jahr"], "reihe": teil["gebiet_id"].map(namen), "spalte": spalte,
                          "wert": teil[spalte], "vollstaendig": teil["vollstaendig"].astype(bool)})
    reihenfolge = [namen[g] for g in gebiete if g in namen]
    marken = {}
    if station:
        messung = Ergebnis.laden("hitzetage-station")
        if messung is not None and spalte in messung.tabelle.columns:
            m = messung.tabelle.dropna(subset=[spalte])
            daten = pd.concat([daten, pd.DataFrame({
                "jahr": m["jahr"], "reihe": STATION_NAME, "spalte": spalte, "wert": m[spalte],
                "vollstaendig": m["vollstaendig"].astype(bool)})], ignore_index=True)
            reihenfolge.append(STATION_NAME)
            marken = dict(MARKEN["hitzetage-station"])
    daten["reihe"] = pd.Categorical(daten["reihe"], categories=reihenfolge)
    daten = daten.sort_values(["reihe", "jahr"]).reset_index(drop=True)
    daten["reihe"] = daten["reihe"].astype(str)
    analyse = analysen.hole(analyse_id)
    return Zeitreihe(analyse_id, f"{REIHEN[analyse_id][spalte]} – {analyse.titel}", einheit_von(spalte), daten,
                     {}, dict(ergebnis.parameter), marken)


def frueher_heute(daten: pd.DataFrame, von: int = BEZUG[0], bis: int = BEZUG[1],
                  jahre: int = 10) -> tuple[pd.DataFrame, int | None]:
    """Mittel je Reihe im Vergleichszeitraum und in den letzten `jahre` vollständigen Jahren.

    Gibt die Tabelle (reihe, mittel_frueher, mittel_heute, differenz) und das letzte Jahr zurück."""
    voll = daten[daten["vollstaendig"]]
    if voll.empty:
        return pd.DataFrame(columns=["reihe", "mittel_frueher", "mittel_heute", "differenz"]), None
    letzte = int(voll["jahr"].max())
    frueher = zeitraum_mittel(daten, von, bis)
    heute = zeitraum_mittel(daten, letzte - jahre + 1, letzte, mindestens=max(1, jahre - 2))
    tabelle = frueher.merge(heute, on="reihe", suffixes=("_frueher", "_heute"))
    tabelle["differenz"] = tabelle["mittel_heute"] - tabelle["mittel_frueher"]
    reihenfolge = {r: i for i, r in enumerate(dict.fromkeys(daten["reihe"]))}  # wie gewählt, nicht alphabetisch
    tabelle = tabelle.sort_values("reihe", key=lambda s: s.map(reihenfolge)).reset_index(drop=True)
    return tabelle[["reihe", "mittel_frueher", "mittel_heute", "differenz"]], letzte
