"""Heiße Tage, Sommertage und Jahresmittel je Stadtteil aus den Jahresrastern des DWD.

Der Deutsche Wetterdienst rechnet aus seinen Stationen für jedes Jahr ein 1-km-Gitter für Deutschland.
Für jeden Stadtteil wird der flächengewichtete Mittelwert der Zellen gebildet, die ihn berühren. So
entsteht eine Reihe je Stadtteil und eine für ganz Essen. Verglichen werden der Bezugszeitraum
(Standard 1961 bis 1990) und die letzten zehn Jahre.

Modellwerte: Die Raster sind aus Stationen interpoliert; städtische Wärmeinsel und Kaltluftabfluss sind
laut DWD nicht abgebildet. Benachbarte Stadtteile unterscheiden sich daher wenig.

Daten: DWD Climate Data Center, Jahresraster (grids_germany/annual), CC BY 4.0.
Methodik: docs/methodik/hitzetage-raster.md
"""

from __future__ import annotations

import gzip
import io
import re
import zipfile
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .. import laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen, Zeitwert

HEISSE_ID = "dwd-raster-heisse-tage"
SOMMER_ID = "dwd-raster-sommertage"
MITTEL_ID = "dwd-raster-jahresmittel"

# Belegt in den Datensatzbeschreibungen des DWD (BESCHREIBUNG_gridsgermany_annual_*_de.pdf, Stand 18.12.2018):
# Gauß-Krüger 3. Streifen (EPSG:31467), Fehlwert -999, Jahresmittel in 1/10 °C, Kenntage als Anzahl.
RASTER_CRS = "EPSG:31467"
FEHLWERT = -999
KENNWERTE = {  # Spalte → (Datensatz, Beschriftung, Faktor)
    "heisse_tage": (HEISSE_ID, "Heiße Tage (ab 30 °C)", 1.0),
    "sommertage": (SOMMER_ID, "Sommertage (ab 25 °C)", 1.0),
    "jahresmittel_c": (MITTEL_ID, "Jahresmittel °C", 0.1),
}
# Stufen für die Karte über die Jahre (essen.zeitkarte): reichen von den 1950ern bis heute, gleich für alle Jahre
ZEITACHSE = (
    Zeitwert("heisse_tage", "Heiße Tage pro Jahr (ab 30 °C)", "Tage", Stufen(
        grenzen=(0, 4, 6, 8, 10), farben=FARBSTUFEN["waerme"],
        texte=("unter 4", "4 bis 6", "6 bis 8", "8 bis 10", "10 und mehr"))),
    Zeitwert("sommertage", "Sommertage pro Jahr (ab 25 °C)", "Tage", Stufen(
        grenzen=(0, 25, 30, 35, 40), farben=FARBSTUFEN["waerme"],
        texte=("unter 25", "25 bis 30", "30 bis 35", "35 bis 40", "40 und mehr"))),
    Zeitwert("jahresmittel_c", "Jahresmitteltemperatur", "°C", Stufen(
        grenzen=(0, 9.5, 10, 10.5, 11), farben=FARBSTUFEN["waerme"],
        texte=("unter 9,5 °C", "9,5 bis 10 °C", "10 bis 10,5 °C", "10,5 bis 11 °C", "11 °C und mehr")),
        stellen=1),
)
ESSEN_ID = "essen"
ESSEN_NAME = "Essen gesamt"
MIN_ABDECKUNG = 0.5  # Anteil der Stadtteilfläche, der in gültigen Zellen liegen muss
LETZTE_JAHRE = 10

# Grenzen alle 2 Tage: Die Stadtteile liegen nah beieinander (2016–2025: 9,3 bis 12,5); feinere Stufen
# würden Unterschiede betonen, die das 1-km-Raster nicht hergibt.
STUFEN = Stufen(
    grenzen=(0, 6, 8, 10, 12),
    farben=FARBSTUFEN["waerme"],
    texte=("unter 6", "6 bis 8", "8 bis 10", "10 bis 12", "12 und mehr"),
)


# -------------------------------------------------------------------- Gitter lesen

@dataclass(frozen=True)
class Kopf:
    spalten: int
    zeilen: int
    x_links: float   # linker Rand der Zellen
    y_unten: float   # unterer Rand der Zellen
    zelle: float
    fehlwert: float

    @property
    def y_oben(self) -> float:
        return self.y_unten + self.zeilen * self.zelle


def lies_kopf(datei) -> Kopf:
    """Liest die sechs Kopfzeilen eines ESRI-ASCII-Gitters (Ecke oder Mitte der Zelle unten links)."""
    werte = {}
    for _ in range(6):
        teile = datei.readline().split()
        if len(teile) != 2:
            raise ValueError("Kein ESRI-ASCII-Gitter: Kopfzeile fehlt.")
        werte[teile[0].upper()] = float(teile[1])
    zelle = werte["CELLSIZE"]
    halb = zelle / 2
    x = werte["XLLCORNER"] if "XLLCORNER" in werte else werte["XLLCENTER"] - halb
    y = werte["YLLCORNER"] if "YLLCORNER" in werte else werte["YLLCENTER"] - halb
    return Kopf(int(werte["NCOLS"]), int(werte["NROWS"]), x, y, zelle, werte.get("NODATA_VALUE", FEHLWERT))


def _oeffnen(pfad):
    """Öffnet ein Gitter als Text. Nach den ersten Bytes, nicht nach der Endung: Beim DWD sind manche Dateien
    namens .asc.gz in Wahrheit ZIP-Archive (etwa beim Jahresmittel bis 2024)."""
    with open(pfad, "rb") as roh:
        anfang = roh.read(4)
    if anfang[:2] == b"\x1f\x8b":
        return gzip.open(pfad, "rt", encoding="ascii")
    if anfang == b"PK\x03\x04":
        archiv = zipfile.ZipFile(pfad)
        namen = [n for n in archiv.namelist() if n.lower().endswith(".asc")]
        if len(namen) != 1:
            raise ValueError(f"{pfad.name}: erwartet genau ein .asc im ZIP, gefunden {len(namen)}.")
        return io.TextIOWrapper(archiv.open(namen[0]), encoding="ascii")
    return open(pfad, encoding="ascii")


def lies_ausschnitt(pfad, grenzen: tuple[float, float, float, float]) -> tuple[np.ndarray, Kopf, int, int]:
    """Die Zellen eines Gitters, die das Rechteck (x1, y1, x2, y2) berühren. Fehlwerte als NaN.

    Gibt Werte (Zeilen von Nord nach Süd), Kopf und die Nummer der ersten Zeile und Spalte zurück."""
    x1, y1, x2, y2 = grenzen
    with _oeffnen(pfad) as datei:
        kopf = lies_kopf(datei)
        s0 = max(0, int(np.floor((x1 - kopf.x_links) / kopf.zelle)))
        s1 = min(kopf.spalten, int(np.ceil((x2 - kopf.x_links) / kopf.zelle)))
        z0 = max(0, int(np.floor((kopf.y_oben - y2) / kopf.zelle)))
        z1 = min(kopf.zeilen, int(np.ceil((kopf.y_oben - y1) / kopf.zelle)))
        if s1 <= s0 or z1 <= z0:
            raise ValueError(f"{pfad.name} deckt das Stadtgebiet nicht ab.")
        zeilen = []
        for nummer, zeile in enumerate(datei):
            if nummer >= z1:
                break
            if nummer >= z0:
                zeilen.append(np.array(zeile.split()[s0:s1], dtype=float))
    werte = np.vstack(zeilen)
    werte[werte == kopf.fehlwert] = np.nan
    return werte, kopf, z0, s0


def jahr_aus_name(name: str) -> int | None:
    """grids_germany_annual_hot_days_2025_17.asc.gz → 2025, …_air_temp_mean_202517.asc.gz → 2025."""
    treffer = re.search(r"_(\d{4})_?17\.asc(\.gz)?$", name)
    return int(treffer.group(1)) if treffer else None


# -------------------------------------------------------------------- Mittel je Gebiet

def gewichte(gebiete: gpd.GeoDataFrame, kopf: Kopf, z0: int, s0: int, form: tuple[int, int]) -> np.ndarray:
    """Matrix Gebiete × Zellen: Fläche in m², mit der ein Gebiet in jeder Zelle des Ausschnitts liegt."""
    zeilen, spalten = form
    zz, ss = np.meshgrid(np.arange(zeilen), np.arange(spalten), indexing="ij")
    links = kopf.x_links + (s0 + ss.ravel()) * kopf.zelle
    oben = kopf.y_oben - (z0 + zz.ravel()) * kopf.zelle
    zellen = shapely.box(links, oben - kopf.zelle, links + kopf.zelle, oben)
    im_raster = gebiete.to_crs(RASTER_CRS).geometry.reset_index(drop=True)
    matrix = np.zeros((len(im_raster), len(zellen)))
    baum = shapely.STRtree(zellen)
    for g, geometrie in enumerate(im_raster):
        treffer = baum.query(geometrie, predicate="intersects")
        matrix[g, treffer] = shapely.area(shapely.intersection(zellen[treffer], geometrie))
    return matrix


def gebietsmittel(werte: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Flächengewichtetes Mittel je Gebiet über gültige Zellen; NaN, wenn weniger als MIN_ABDECKUNG gültig ist."""
    flach = werte.ravel()
    gueltig = np.isfinite(flach)
    summe = matrix @ np.where(gueltig, flach, 0.0)
    gewicht = matrix @ gueltig.astype(float)
    gesamt = matrix.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mittel = summe / gewicht
    mittel[(gesamt == 0) | (gewicht < MIN_ABDECKUNG * gesamt)] = np.nan
    return mittel


def jahreswerte(gebiete: gpd.GeoDataFrame, melde=lambda m: None) -> tuple[pd.DataFrame, list[str]]:
    """Lange Tabelle: gebiet_id, stadtteil, jahr und je Kennwert eine Spalte; dazu „Essen gesamt“."""
    geladen = [k for k, (kennung, _, _) in KENNWERTE.items() if laden.vorhanden(kennung)]
    if HEISSE_ID not in [KENNWERTE[k][0] for k in geladen]:
        raise DatenFehlen([HEISSE_ID])
    grenzen = tuple(gebiete.to_crs(RASTER_CRS).total_bounds)
    alle = pd.concat([gebiete[["gebiet_id", "name", "geometry"]],
                      gpd.GeoDataFrame({"gebiet_id": [ESSEN_ID], "name": [ESSEN_NAME]},
                                       geometry=[gebiete.union_all()], crs=gebiete.crs)], ignore_index=True)
    teile, hinweise, matrix, gitter = [], [], None, None
    for spalte in geladen:
        kennung, titel, faktor = KENNWERTE[spalte]
        dateien = [(jahr_aus_name(p.name), p) for p in laden.dateien(kennung, "*.asc*")]
        dateien = sorted((j, p) for j, p in dateien if j is not None)
        if not dateien:
            raise ValueError(f"Im Datensatz {kennung} liegt kein Jahresraster (*.asc.gz).")
        melde(f"  {titel}: {len(dateien)} Jahre ({dateien[0][0]} bis {dateien[-1][0]})")
        zeilen = []
        for jahr, pfad in dateien:
            werte, kopf, z0, s0 = lies_ausschnitt(pfad, grenzen)
            schluessel = (kopf, z0, s0, werte.shape)
            if schluessel != gitter:  # alle Dateien haben bisher dasselbe Gitter; sonst neu verschneiden
                matrix, gitter = gewichte(alle, kopf, z0, s0, werte.shape), schluessel
            zeilen.append(pd.DataFrame({"gebiet_id": alle["gebiet_id"], "jahr": jahr,
                                        spalte: gebietsmittel(werte, matrix) * faktor}))
        teile.append(pd.concat(zeilen, ignore_index=True))
    tabelle = teile[0]
    for teil in teile[1:]:
        tabelle = tabelle.merge(teil, on=["gebiet_id", "jahr"], how="outer")
    tabelle = tabelle.merge(alle[["gebiet_id", "name"]].rename(columns={"name": "stadtteil"}), on="gebiet_id")
    tabelle["vollstaendig"] = True  # Jahresraster gibt es nur für abgeschlossene Jahre
    fehlend = [KENNWERTE[k][0] for k in KENNWERTE if k not in geladen]
    if fehlend:
        hinweise.append(f"Nicht geladen: {', '.join(fehlend)}. Diese Reihen fehlen.")
    spalten = ["gebiet_id", "stadtteil", "jahr", *geladen, "vollstaendig"]
    return tabelle[spalten].sort_values(["gebiet_id", "jahr"]).round({"heisse_tage": 1, "sommertage": 1,
                                                                      "jahresmittel_c": 2}).reset_index(drop=True), hinweise


def zeitraum_mittel(jahre: pd.DataFrame, spalte: str, von: int, bis: int) -> pd.Series:
    """Mittel je gebiet_id über die Jahre von bis (einschließlich)."""
    teil = jahre[(jahre["jahr"] >= von) & (jahre["jahr"] <= bis)]
    return teil.groupby("gebiet_id")[spalte].mean()


# -------------------------------------------------------------------- Ablauf

def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    melde("Lese die Jahresraster des DWD …")
    jahre, hinweise = jahreswerte(gebiete, melde)
    von, bis = int(p["bezug_von"]), int(p["bezug_bis"])
    letztes = int(jahre.dropna(subset=["heisse_tage"])["jahr"].max())
    zuletzt_von = letztes - LETZTE_JAHRE + 1
    erstes = int(jahre.dropna(subset=["heisse_tage"])["jahr"].min())
    if von < erstes:
        hinweise.append(f"Heiße Tage gibt es erst ab {erstes}; der Bezugszeitraum beginnt deshalb dort.")

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"})
    tabelle = tabelle.set_index("gebiet_id")
    for spalte in [k for k in KENNWERTE if k in jahre.columns]:
        endung = "_c" if spalte.endswith("_c") else ""
        basis = spalte.removesuffix("_c")
        tabelle[f"{basis}_bezug{endung}"] = zeitraum_mittel(jahre, spalte, von, bis)
        tabelle[f"{basis}_zuletzt{endung}"] = zeitraum_mittel(jahre, spalte, zuletzt_von, letztes)
        tabelle[f"{basis}_aenderung{endung}"] = tabelle[f"{basis}_zuletzt{endung}"] - tabelle[f"{basis}_bezug{endung}"]
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: (2 if c.endswith("_c") else 1) for c in tabelle.columns
                             if c.endswith(("_bezug", "_zuletzt", "_aenderung", "_bezug_c", "_zuletzt_c", "_aenderung_c"))})

    essen = jahre[jahre["gebiet_id"] == ESSEN_ID]
    stadt_bezug = essen[(essen["jahr"] >= von) & (essen["jahr"] <= bis)]["heisse_tage"].mean()
    stadt_zuletzt = essen[essen["jahr"] >= zuletzt_von]["heisse_tage"].mean()
    text = (f"Heiße Tage pro Jahr in Essen (Modellwert): {von} bis {bis} im Mittel {zahl(stadt_bezug, 1)}, "
            f"{zuletzt_von} bis {letztes} im Mittel {zahl(stadt_zuletzt, 1)}.")
    spanne = tabelle["heisse_tage_zuletzt"].dropna()
    if len(spanne):
        hinweise.append(f"{zuletzt_von} bis {letztes} liegen die Stadtteile zwischen {zahl(spanne.min(), 1)} und "
                        f"{zahl(spanne.max(), 1)} heißen Tagen im Jahr.")
    hinweise.append("Modellwerte aus dem 1-km-Raster des DWD, aus Stationen interpoliert. Die städtische Wärmeinsel "
                    "ist laut DWD nicht abgebildet; in dicht bebauten Vierteln ist es oft heißer.")
    hinweise.append("Das Messnetz hat sich über die Jahre verändert; einzelne Jahre schwanken stark.")
    melde(text)
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=float(stadt_zuletzt),
        kennzahl_text=text,
        hinweise=stadtteile.hinweise + hinweise,
        quellen=[stadtteile.datensatz] + [KENNWERTE[k][0] for k in KENNWERTE if k in jahre.columns],
        parameter=dict(p),
        jahreswerte=jahre,
    )


ANALYSE = Analyse(
    id="hitzetage-raster",
    gewicht="flaeche_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Heiße Tage je Stadtteil (DWD-Raster)",
    frage="Wie viele heiße Tage gibt es in meinem Stadtteil, und wie hat sich das seit 1951 verändert?",
    themen=("klima",),
    benoetigt=("stadtteile", HEISSE_ID),
    optional=(SOMMER_ID, MITTEL_ID),
    rechne=rechne,
    kennzahl="heisse_tage_zuletzt",
    kennzahl_titel="Heiße Tage pro Jahr, Mittel der letzten zehn Jahre",
    einheit="Tage",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("heisse_tage_zuletzt", "heiße Tage, letzte 10 Jahre", "zahl", stellen=1, balken=True),
        Spalte("heisse_tage_bezug", "heiße Tage, Vergleichszeitraum", "zahl", stellen=1),
        Spalte("heisse_tage_aenderung", "Änderung", "zahl", stellen=1),
        Spalte("sommertage_zuletzt", "Sommertage, letzte 10 Jahre", "zahl", stellen=1),
        Spalte("jahresmittel_aenderung_c", "Jahresmittel, Änderung °C", "zahl", stellen=1),
    ),
    parameter=(
        Parameter("bezug_von", "Vergleichszeitraum von", 1961,
                  "Mit diesem Zeitraum werden die letzten zehn Jahre verglichen. 1961 bis 1990 ist der übliche "
                  "Vergleichszeitraum des Wetterdienstes.", typ="ganzzahl", selten=True),
        Parameter("bezug_bis", "Vergleichszeitraum bis", 1990, "Ende des Vergleichszeitraums.", typ="ganzzahl",
                  selten=True),
    ),
    methodik="methodik/hitzetage-raster.md",
    zeitachse=ZEITACHSE,
    thema_titel="Heiße Tage im Stadtteil",
    kurz="Wie viele Tage mit mindestens 30 °C gibt es in jedem Stadtteil, und wie viele waren es früher?",
    richtung="hoch_schlecht",
    lesehilfe="Jeder Stadtteil ist nach der Zahl der heißen Tage pro Jahr gefärbt, gemittelt über die letzten zehn Jahre. Je dunkler, desto mehr heiße Tage. Die Werte stammen aus einem Raster des Wetterdienstes mit 1 km großen Zellen; benachbarte Stadtteile unterscheiden sich deshalb nur wenig.",
    grenzen_kurz=(
        "Modellwert aus Wetterstationen, keine Messung im Stadtteil.",
        "Die Aufheizung dicht bebauter Viertel ist nicht enthalten; dafür die Karten zur Hitze am Tag und in der Nacht ansehen.",
        "Einzelne Jahre schwanken stark; aussagekräftig ist der Verlauf über Jahrzehnte.",
    ),
)
