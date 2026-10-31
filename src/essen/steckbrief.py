"""Kennzahlen aller gespeicherten Analysen je Stadtteil: Steckbrief eines Stadtteils und Vergleich zweier Themen.

Liest nur gespeicherte Ergebnisse (data/processed/<id>/), rechnet nichts neu. Grundlage für die App-Seiten
„Stadtteil“ und „Themen vergleichen“.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import analysen
from .analysen.basis import Ergebnis


@dataclass(frozen=True)
class Kennzahl:
    analyse_id: str
    titel: str          # Titel der Analyse
    kennzahl: str       # Spalte
    kennzahl_titel: str
    einheit: str
    erstellt: str
    kennzahl_text: str
    testdaten: bool


def verfuegbare() -> list[Kennzahl]:
    """Alle Analysen mit Stadtteilbezug, für die ein gespeichertes Ergebnis mit der Kennzahlspalte vorliegt."""
    gefunden = []
    for analyse in analysen.ALLE.values():
        if analyse.raumbezug != "stadtteil" or not analyse.kennzahl:
            continue
        ergebnis = Ergebnis.ansehen(analyse.id)
        if ergebnis is None or analyse.kennzahl not in ergebnis.tabelle.columns or "gebiet_id" not in ergebnis.tabelle:
            continue
        gefunden.append(Kennzahl(analyse.id, analyse.titel, analyse.kennzahl, analyse.kennzahl_titel, analyse.einheit,
                                 ergebnis.erstellt, ergebnis.kennzahl_text, ergebnis.testdaten))
    return gefunden


def tabelle() -> pd.DataFrame:
    """Breite Tabelle: eine Zeile je Stadtteil (gebiet_id, stadtteil), eine Spalte je Analyse (Wert der Kennzahl)."""
    breit = None
    for k in verfuegbare():
        t = Ergebnis.ansehen(k.analyse_id).tabelle
        teil = t[["gebiet_id", "stadtteil", k.kennzahl]].rename(columns={k.kennzahl: k.analyse_id})
        teil["gebiet_id"] = teil["gebiet_id"].astype(str)
        breit = teil if breit is None else breit.merge(teil.drop(columns="stadtteil"), on="gebiet_id", how="outer")
    if breit is None:
        return pd.DataFrame(columns=["gebiet_id", "stadtteil"])
    return breit.sort_values("stadtteil").reset_index(drop=True)


def stadtteil(gebiet_id: str, katalog=None) -> pd.DataFrame:
    """Steckbrief: je Analyse Wert, Rang (1 = höchster Wert), Anzahl Stadtteile mit Wert und Mittel der Stadtteile.

    Mit `katalog` auch der Wert des Stadtbezirks (`bezirk`, `wert_bezirk`, E-018), soweit die Analyse ihn kennt."""
    from . import bezirke

    breit = tabelle()
    bezirk = bezirke.bezirk_von(katalog, gebiet_id) if katalog is not None else None
    zeilen = []
    for k in verfuegbare():
        spalte = breit[k.analyse_id]
        wert = spalte[breit["gebiet_id"] == str(gebiet_id)]
        wert = float(wert.iloc[0]) if len(wert) and pd.notna(wert.iloc[0]) else np.nan
        zeile = breit["gebiet_id"] == str(gebiet_id)
        rang_mitte = float(spalte.rank(ascending=False, method="average")[zeile].iloc[0]) if not np.isnan(wert) else None
        rang = int(spalte.rank(ascending=False, method="min")[zeile].iloc[0]) \
            if not np.isnan(wert) else None
        zeilen.append({"analyse_id": k.analyse_id, "thema": k.titel, "kennzahl": k.kennzahl_titel, "wert": wert,
                       "einheit": k.einheit, "rang": rang, "rang_mitte": rang_mitte, "von": int(spalte.notna().sum()),
                       "mittel_stadtteile": float(spalte.mean()) if spalte.notna().any() else np.nan,
                       "erstellt": k.erstellt[:10], "bezirk": bezirk,
                       "wert_bezirk": _bezirkswert(katalog, k.analyse_id, bezirk)})
    return pd.DataFrame(zeilen)


def _bezirkswert(katalog, analyse_id: str, bezirk: int | None) -> float:
    from . import bezirke

    if bezirk is None:
        return np.nan
    werte = bezirke.je_bezirk(katalog, analyse_id)
    treffer = werte[werte["bezirk"] == bezirk]["wert"]
    return float(treffer.iloc[0]) if len(treffer) and pd.notna(treffer.iloc[0]) else np.nan


def vergleich(analyse_a: str, analyse_b: str) -> tuple[pd.DataFrame, float | None]:
    """Werte zweier Kennzahlen je Stadtteil und ihre Korrelation (Pearson) über die Stadtteile mit beiden Werten."""
    breit = tabelle()
    for kennung in (analyse_a, analyse_b):
        if kennung not in breit.columns:
            raise ValueError(f"Für {kennung} gibt es kein gespeichertes Ergebnis je Stadtteil. Erst rechnen: "
                             f"uv run essen analyse {kennung}")
    paar = breit[["gebiet_id", "stadtteil", analyse_a, analyse_b]].dropna()
    r = float(paar[analyse_a].corr(paar[analyse_b])) if len(paar) >= 3 else None
    return paar.reset_index(drop=True), r


def korrelationen() -> pd.DataFrame:
    """Korrelationsmatrix aller verfügbaren Kennzahlen über die Stadtteile (paarweise vollständige Werte)."""
    breit = tabelle()
    werte = breit.drop(columns=["gebiet_id", "stadtteil"])
    return werte.corr() if werte.shape[1] else pd.DataFrame()


# Themen der Mehrfachbelastung (E-008): Spalte „…_oben“ → Titel für Menschen
MEHRFACH_THEMEN = {"hitze_nacht_oben": "Hitze in der Nacht", "laerm_oben": "Lärm", "starkregen_oben": "Starkregen"}


def _zeile(analyse_id: str, gebiet_id: str) -> pd.Series | None:
    ergebnis = Ergebnis.ansehen(analyse_id)
    if ergebnis is None or "gebiet_id" not in ergebnis.tabelle.columns:
        return None
    treffer = ergebnis.tabelle[ergebnis.tabelle["gebiet_id"].astype(str) == str(gebiet_id)]
    return treffer.iloc[0] if len(treffer) else None


def zeile(analyse_id: str, gebiet_id: str) -> pd.Series | None:
    """Die Zeile eines Stadtteils im gespeicherten Ergebnis einer Analyse (alle Spalten)."""
    return _zeile(analyse_id, gebiet_id)


def einwohner_belastet(analyse_id: str, gebiet_id: str) -> dict | None:
    """Geschätzte Einwohner in den belasteten Flächen eines Stadtteils (E-013), falls das Ergebnis sie enthält.

    Gibt einwohner, belastet und anteil_pct zurück; None ohne Einwohnerspalten oder ohne belastbaren Anteil."""
    zeile = _zeile(analyse_id, gebiet_id)
    if zeile is None or "einwohner_belastet" not in zeile.index or pd.isna(zeile.get("anteil_einwohner_pct")):
        return None
    return {"einwohner": int(zeile["einwohner"]), "belastet": int(zeile["einwohner_belastet"]),
            "anteil_pct": float(zeile["anteil_einwohner_pct"])}


def mehrfach_themen(gebiet_id: str) -> list[tuple[str, bool]]:
    """Für die Mehrfachbelastung: je Thema (Titel, liegt der Stadtteil im obersten Fünftel?)."""
    zeile = _zeile("mehrfachbelastung", gebiet_id)
    if zeile is None:
        return []
    return [(titel, bool(zeile[spalte])) for spalte, titel in MEHRFACH_THEMEN.items() if spalte in zeile.index]


def flaeche_ha(gebiet_id: str) -> float | None:
    """Fläche eines Stadtteils in Hektar aus dem ersten gespeicherten Ergebnis, das sie enthält."""
    for k in verfuegbare():
        zeile = _zeile(k.analyse_id, gebiet_id)
        if zeile is not None and "flaeche_ha" in zeile.index and pd.notna(zeile["flaeche_ha"]):
            return float(zeile["flaeche_ha"])
    return None
