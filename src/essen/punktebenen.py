"""Punkte zum Einblenden auf der Karte: kühle Orte, Jungbäume, Ladesäulen, Leihräder, Pegel.

Jede Ebene liest einen geladenen Datensatz (Felder belegt in den Inspektionsberichten vom 10.10.2026) und gibt
einen GeoDataFrame in WGS84 zurück: nur Punkte im Rechteck um Essen, Spalten mit Namen für Menschen (für den
Tooltip). Feldinhalte werden gezeigt, wie sie geliefert werden, nicht gedeutet (E-009).
"""

from __future__ import annotations

import io
import json
from collections.abc import Callable
from dataclasses import dataclass

import geopandas as gpd
import pandas as pd

from . import laden
from .geo import ESSEN_BBOX_WGS84, WEB_CRS, DatenFehlen, lies_vektor, vektordatei


@dataclass(frozen=True)
class Punktebene:
    id: str
    titel: str
    datensatz: str
    farbe: str
    beschreibung: str
    lies: Callable[[], gpd.GeoDataFrame]


def _im_rechteck(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    west, sued, ost, nord = ESSEN_BBOX_WGS84
    gdf = gdf.to_crs(WEB_CRS)
    return gdf.cx[west:ost, sued:nord].reset_index(drop=True)


def _aus_koordinaten(df: pd.DataFrame, lon: str, lat: str, spalten: dict[str, str]) -> gpd.GeoDataFrame:
    x = pd.to_numeric(df[lon].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    y = pd.to_numeric(df[lat].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    daten = df[list(spalten)].rename(columns=spalten)
    gdf = gpd.GeoDataFrame(daten, geometry=gpd.points_from_xy(x, y), crs=WEB_CRS)
    return gdf[x.notna().to_numpy() & y.notna().to_numpy()]


def _datei(datensatz: str, endung: str):
    treffer = [p for p in laden.dateien(datensatz) if p.suffix.lower() == endung]
    if not treffer:
        raise FileNotFoundError(f"Im Datensatz {datensatz} fehlt eine {endung}-Datei. Neu laden: "
                                f"uv run essen laden {datensatz} --neu")
    return treffer[0]


def _kuehlorte() -> gpd.GeoDataFrame:
    gdf = lies_vektor(vektordatei("kuehlorte"))
    spalten = {"NAME": "Name", "ART": "Art", "ORT": "Ort", "OEFFNUNGSZ": "Öffnungszeiten", "KOSTEN": "Kosten",
               "ADRESSE": "Adresse"}
    return gdf[[c for c in spalten if c in gdf.columns] + ["geometry"]].rename(columns=spalten)


def _jungbaeume() -> gpd.GeoDataFrame:
    gdf = lies_vektor(vektordatei("stadtbaeume"))
    spalten = {"PFLANZJAHR": "Pflanzjahr", "KATEGORIE": "Kategorie"}
    gdf = gdf[[c for c in spalten if c in gdf.columns] + ["geometry"]].rename(columns=spalten)
    if "Pflanzjahr" in gdf.columns:
        gdf["Pflanzjahr"] = pd.to_numeric(gdf["Pflanzjahr"], errors="coerce").astype("Int64")
    return gdf


def _ladesaeulen() -> gpd.GeoDataFrame:
    """Ladesäulenregister: zehn Zeilen Vorspann, dann Kopfzeile ab „Ladeeinrichtungs-ID“; ganz Deutschland.

    Gefiltert wird nach „Kreis/kreisfreie Stadt“, nicht nach „Ort“ (es gibt einen Ort „Essen“ in Berlin)."""
    text = _datei("ladesaeulen", ".csv").read_text(encoding="utf-8-sig", errors="replace")
    zeilen = text.splitlines()
    kopf = next((i for i, z in enumerate(zeilen) if z.startswith("Ladeeinrichtungs-ID")), None)
    if kopf is None:
        raise ValueError("Ladesäulenregister: Kopfzeile „Ladeeinrichtungs-ID“ nicht gefunden; Aufbau geändert?")
    df = pd.read_csv(io.StringIO("\n".join(zeilen[kopf:])), sep=";", dtype=str, low_memory=False)
    df = df[df["Kreis/kreisfreie Stadt"].str.strip() == "Kreisfreie Stadt Essen"].copy()
    df["Adresse"] = (df["Straße"].fillna("") + " " + df["Hausnummer"].fillna("")).str.strip()
    spalten = {"Betreiber": "Betreiber", "Art der Ladeeinrichtung": "Art", "Anzahl Ladepunkte": "Ladepunkte",
               "Nennleistung Ladeeinrichtung [kW]": "Leistung (kW)", "Adresse": "Adresse",
               "Inbetriebnahmedatum": "in Betrieb seit"}
    return _aus_koordinaten(df, "Längengrad", "Breitengrad", spalten)


def _nextbike() -> gpd.GeoDataFrame:
    daten = json.loads(_datei("nextbike-essen", ".json").read_text(encoding="utf-8"))
    stationen = pd.DataFrame(daten.get("data", {}).get("stations", []))
    if stationen.empty:
        return gpd.GeoDataFrame({"Station": []}, geometry=[], crs=WEB_CRS)
    spalten = {"name": "Station"} | ({"capacity": "Stellplätze"} if "capacity" in stationen.columns else {})
    return _aus_koordinaten(stationen, "lon", "lat", spalten)


def _pegel() -> gpd.GeoDataFrame:
    daten = json.loads(_datei("pegel-essen", ".json").read_text(encoding="utf-8"))
    zeilen = []
    for station in daten:
        reihe = next((t for t in station.get("timeseries", []) if t.get("shortname") == "W"), {})
        messung = reihe.get("currentMeasurement") or {}
        zeilen.append({
            "Pegel": station.get("longname") or station.get("shortname"),
            "Gewässer": (station.get("water") or {}).get("longname"),
            "Wasserstand beim Abruf": (f"{messung['value']} {reihe.get('unit', '')}".strip()
                                       if messung.get("value") is not None else None),
            "gemessen": messung.get("timestamp"),
            "lon": station.get("longitude"), "lat": station.get("latitude"),
        })
    df = pd.DataFrame(zeilen)
    if df.empty:
        return gpd.GeoDataFrame({"Pegel": []}, geometry=[], crs=WEB_CRS)
    return _aus_koordinaten(df, "lon", "lat", {c: c for c in ("Pegel", "Gewässer", "Wasserstand beim Abruf",
                                                              "gemessen")})


PUNKTEBENEN: dict[str, Punktebene] = {e.id: e for e in (
    Punktebene("kuehlorte", "Kühle Orte", "kuehlorte", "#2f73a6",
               "Öffentlich zugängliche kühle Orte für heiße Tage: Parks, Spielplätze, Bibliotheken, Bäder.", _kuehlorte),
    Punktebene("jungbaeume", "Jungbäume der Stadt", "stadtbaeume", "#3b8432",
               "Von der Stadt seit 2008 gepflanzte Jungbäume (nicht der ganze Baumbestand).", _jungbaeume),
    Punktebene("ladesaeulen", "Ladesäulen", "ladesaeulen", "#6a51a3",
               "Öffentliche Ladeeinrichtungen für Elektroautos laut Ladesäulenregister.", _ladesaeulen),
    Punktebene("leihraeder", "Lastenrad-Stationen", "nextbike-essen", "#b43e03",
               "Stationen des StadtLastenRads (nextbike).", _nextbike),
    Punktebene("pegel", "Pegel", "pegel-essen", "#1d5582",
               "Wasserstandspegel an Ruhr, Rhein und Rhein-Herne-Kanal in der Umgebung, mit dem Wert beim Laden.",
               _pegel),
)}


def verfuegbar() -> list[Punktebene]:
    """Ebenen, deren Datensatz geladen ist."""
    return [e for e in PUNKTEBENEN.values() if laden.vorhanden(e.datensatz)]


def lade(kennung: str) -> gpd.GeoDataFrame:
    """Punkte einer Ebene im Rechteck um Essen, in WGS84, Spalten für Menschen benannt."""
    ebene = PUNKTEBENEN[kennung]
    if not laden.vorhanden(ebene.datensatz):
        raise DatenFehlen([ebene.datensatz])
    return _im_rechteck(ebene.lies())
