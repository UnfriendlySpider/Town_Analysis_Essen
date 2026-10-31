"""Karte über die Jahre: Stadtteile je Jahrzehnt oder Jahr gefärbt, zum Abspielen und Nebeneinanderstellen.

Bereitet alles für die Anzeige vor (Flächen als SVG-Pfade, Farbe und Wert je Zeitschritt, Legende), damit der
Browser nur noch umfärbt: kein Neuladen je Bild, keine Bibliothek, keine Kartenkacheln. Grundlage sind
Ergebnis.jahreswerte und die Zeitachse der Analyse (Analyse.zeitachse, E-016).
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import pandas as pd
import shapely

from .analysen.basis import Ergebnis, Zeitwert
from .geo import ZIEL_CRS
from .text import zahl

BREITE = 1000.0       # Breite der Zeichenfläche (SVG-Einheiten); die Höhe folgt dem Seitenverhältnis
TOLERANZ_M = 30.0     # Vereinfachung der Grenzen: auf einer Bildschirmkarte nicht zu sehen


@dataclass
class Schritt:
    titel: str                  # „1990er“, „2020–2025“ oder „2003“
    von: int
    bis: int
    jahre: int                  # Anzahl Jahre mit Werten (vollständige Jahre)
    werte: dict[str, float]     # gebiet_id → Wert


def jahrzehnt_mittel(jahreswerte: pd.DataFrame, feld: str) -> list[Schritt]:
    """Mittel je Gebiet und Jahrzehnt über die vollständigen Jahre. Ein angebrochenes Jahrzehnt heißt „2020–2025“.

    Einzelne Jahre schwanken stark; Jahrzehnte zeigen den Verlauf ruhiger. Jahrzehnte mit weniger als drei
    Jahren fallen weg (zu wenig für ein Mittel)."""
    daten = _voll(jahreswerte, feld)
    daten = daten.assign(jahrzehnt=daten["jahr"] // 10 * 10)
    schritte = []
    for jahrzehnt, teil in daten.groupby("jahrzehnt"):
        von, bis, anzahl = int(teil["jahr"].min()), int(teil["jahr"].max()), int(teil["jahr"].nunique())
        if anzahl < 3:
            continue
        titel = f"{jahrzehnt}er" if anzahl == 10 else f"{von}–{bis}"
        werte = teil.groupby("gebiet_id")[feld].mean()
        schritte.append(Schritt(titel, von, bis, anzahl, {str(g): float(w) for g, w in werte.items()}))
    return schritte


def einzeljahre(jahreswerte: pd.DataFrame, feld: str) -> list[Schritt]:
    """Ein Schritt je vollständigem Jahr."""
    daten = _voll(jahreswerte, feld)
    return [Schritt(str(int(jahr)), int(jahr), int(jahr), 1,
                    {str(g): float(w) for g, w in zip(teil["gebiet_id"], teil[feld], strict=True)})
            for jahr, teil in daten.groupby("jahr")]


def _voll(jahreswerte: pd.DataFrame, feld: str) -> pd.DataFrame:
    if feld not in jahreswerte.columns:
        raise ValueError(f"Die Jahreswerte haben keine Spalte {feld}.")
    voll = jahreswerte["vollstaendig"].astype(bool) if "vollstaendig" in jahreswerte.columns else True
    return jahreswerte[voll].dropna(subset=[feld]).assign(gebiet_id=lambda d: d["gebiet_id"].astype(str))


def svg_pfade(gebiete: gpd.GeoDataFrame, breite: float = BREITE) -> tuple[list[dict], float]:
    """Flächen als SVG-Pfade in einer Zeichenfläche `breite` × Höhe (EPSG:25832 ist eben, Norden oben).

    Gibt [{gebiet_id, name, d}] und die Höhe zurück. `gebiete` braucht gebiet_id, stadtteil oder name."""
    daten = gebiete.to_crs(ZIEL_CRS)
    daten = daten[daten.geometry.notna() & ~daten.geometry.is_empty]
    x1, y1, x2, y2 = daten.total_bounds
    massstab = breite / (x2 - x1)
    hoehe = round((y2 - y1) * massstab, 1)
    namen = daten["stadtteil"] if "stadtteil" in daten.columns else daten.get("name", daten["gebiet_id"])
    pfade = []
    for gebiet_id, name, form in zip(daten["gebiet_id"].astype(str), namen.astype(str), daten.geometry, strict=True):
        form = shapely.force_2d(form).simplify(TOLERANZ_M, preserve_topology=True)
        teile = []
        for flaeche in getattr(form, "geoms", [form]):
            if not isinstance(flaeche, shapely.Polygon):
                continue
            for ring in (flaeche.exterior, *flaeche.interiors):
                punkte = [f"{(x - x1) * massstab:.1f},{(y2 - y) * massstab:.1f}" for x, y in ring.coords[:-1]]
                teile.append("M" + "L".join(punkte) + "Z")
        if teile:
            pfade.append({"gebiet_id": gebiet_id, "name": name, "d": "".join(teile)})
    return pfade, hoehe


def daten(ergebnis: Ergebnis, zeitwert: Zeitwert, jahrzehnte: bool = True) -> dict:
    """Alles für die Anzeige: Pfade, Schritte (Titel, Farbe und Wert als Text je Gebiet), Legende, Hinweis.

    Gebiete ohne Fläche (z. B. „Essen gesamt“) bleiben in den Werten, erscheinen aber nicht auf der Karte."""
    if ergebnis.geometrie is None or ergebnis.jahreswerte is None:
        raise ValueError(f"Für {ergebnis.analyse_id} gibt es keine Jahreswerte je Stadtteil. Erst rechnen: "
                         f"uv run essen analyse {ergebnis.analyse_id}")
    pfade, hoehe = svg_pfade(ergebnis.geometrie)
    stufen = zeitwert.stufen
    schritte = (jahrzehnt_mittel if jahrzehnte else einzeljahre)(ergebnis.jahreswerte, zeitwert.feld)
    if not schritte:
        raise ValueError(f"Keine vollständigen Jahre für {zeitwert.titel}.")
    ids = [p["gebiet_id"] for p in pfade]
    einheit = f" {zeitwert.einheit}" if zeitwert.einheit else ""
    return {
        "breite": BREITE, "hoehe": hoehe, "pfade": pfade,
        "titel": zeitwert.titel, "einheit": zeitwert.einheit,
        "schritte": [{
            "titel": s.titel,
            "untertitel": (f"Mittel aus {s.jahre} Jahren ({s.von}–{s.bis})" if s.jahre > 1 else ""),
            "farben": [stufen.farbe(s.werte.get(g)) for g in ids],
            "texte": [("kein Wert" if s.werte.get(g) is None else f"{zahl(s.werte[g], zeitwert.stellen)}{einheit}")
                      for g in ids],
        } for s in schritte],
        "legende": [{"farbe": f, "text": t} for f, t in zip(stufen.farben, stufen.texte, strict=True)],
        "hinweis": zeitwert.hinweis,
    }


def verfuegbar(analyse, ergebnis: Ergebnis | None) -> list[Zeitwert]:
    """Die Zeitwerte einer Analyse, für die das gespeicherte Ergebnis Jahreswerte und Flächen hat."""
    if ergebnis is None or ergebnis.jahreswerte is None or ergebnis.geometrie is None:
        return []
    return [z for z in analyse.zeitachse if z.feld in ergebnis.jahreswerte.columns
            and ergebnis.jahreswerte[z.feld].notna().any()]


def datenstand(katalog, analyse) -> str:
    """Stand der Fachdaten einer Analyse aus dem Katalog (ohne die Stadtteilgrenzen), z. B. „2024“."""
    from .geo import STADTTEILE_ID

    staende = []
    for kennung in analyse.benoetigt:
        if kennung == STADTTEILE_ID or kennung not in katalog.datensaetze:
            continue
        stand = katalog.datensaetze[kennung].stand
        if stand and any(z.isdigit() for z in str(stand)) and stand not in staende:  # nicht „laut Datensatz“
            staende.append(str(stand))
    return "; ".join(staende)
