"""Originaldaten ansehen: Dateien eines geladenen Datensatzes, Proben aus Vektor-, Raster-, CSV- und JSON-Dateien.

Grundlage für die Werkstatt-Seite „Originaldaten ansehen“. Alles ist auf kleine Proben begrenzt, damit auch
Datensätze mit mehreren Gigabyte schnell antworten: Vektordaten nur im Rechteck um Essen und höchstens
MAX_OBJEKTE Objekte, Raster ausgedünnt auf höchstens MAX_PIXEL Bildpunkte, Tabellen höchstens MAX_ZEILEN Zeilen.
ZIP-Archive werden nicht entpackt, sondern über GDAL (/vsizip/) oder zipfile gelesen (E-014).

Die Funktionen geben rohe Tabellen und Zahlen zurück; Formatieren ist Sache der Oberfläche.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
import warnings
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio

from . import laden, legenden
from .geo import RASTER_ENDUNGEN, VEKTOR_ENDUNGEN, WEB_CRS, ZIEL_CRS, essen_bbox, gdb_ordner
from .inspizieren import feldtabelle

MAX_OBJEKTE = 2_000
MAX_PIXEL = 800_000
MAX_ZEILEN = 2_000
MAX_JSON_BYTES = 5_000_000

BEIWERK = (".shx", ".dbf", ".prj", ".cpg", ".qix", ".sbn", ".sbx", ".xml", ".aux", ".ovr", ".tfw", ".qmd")
ARTEN = {"vektor": "Vektordaten (Karte und Tabelle)", "raster": "Rasterbild", "tabelle": "Tabelle",
         "json": "JSON", "stil": "Legende (Stildatei)", "dokument": "Dokument", "archiv": "Archiv",
         "beiwerk": "Begleitdatei", "sonstig": "andere Datei"}
ANSEHBAR = ("vektor", "raster", "tabelle", "json")
SKALA = ((222, 235, 247), (8, 48, 107))   # neutrale Skala hell → dunkel für Raster ohne Farben (keine Wertung)


@dataclass(frozen=True)
class Datei:
    name: str          # für Menschen, relativ zum Datensatzordner
    pfad: str          # lesbarer Pfad, bei Archiven ein GDAL-Pfad /vsizip/…
    art: str           # Schlüssel aus ARTEN
    bytes: int
    im_archiv: bool = False


# -------------------------------------------------------------------- Dateien

def _art(name: str, kopf: bytes | None = None, neben: set[str] | None = None) -> str:
    endung = Path(name).suffix.lower()
    if endung == ".json":
        return "vektor" if kopf is not None and (b'"FeatureCollection"' in kopf or b'"Feature"' in kopf) else "json"
    if endung == ".dbf" and neben is not None and Path(name).with_suffix(".shp").name.lower() not in neben:
        return "vektor"  # dBase ohne Shapefile: reine Attributtabelle
    if endung == ".xml" and name.lower().endswith(".aux.xml"):
        return "beiwerk"
    if endung in legenden.STIL_ENDUNGEN:
        return "stil"
    if endung in VEKTOR_ENDUNGEN:
        return "vektor"
    if endung in RASTER_ENDUNGEN:
        return "raster"
    if endung in (".csv", ".txt", ".tsv"):
        return "tabelle"
    if endung in (".pdf", ".html", ".htm", ".docx", ".md"):
        return "dokument"
    if endung == ".zip":
        return "archiv"
    if endung in BEIWERK:
        return "beiwerk"
    return "sonstig"


def _kopf_datei(pfad: Path) -> bytes:
    try:
        with open(pfad, "rb") as datei:
            return datei.read(2000)
    except OSError:
        return b""


def stempel(pfad: str) -> float:
    """Änderungszeit der Datei (bei /vsizip/-Pfaden des Archivs), damit Zwischenspeicher neue Downloads bemerken."""
    echt = pfad.removeprefix("/vsizip/")
    if ".zip/" in echt.lower():
        echt = echt[: echt.lower().index(".zip/") + 4]
    try:
        return Path(echt).stat().st_mtime
    except OSError:
        return 0.0


def dateiliste(ds) -> list[Datei]:
    """Alle Dateien eines geladenen Datensatzes. ZIPs, die nicht entpackt sind, werden hineingeschaut (nicht entpackt).

    File-Geodatabases (.gdb-Ordner) erscheinen als eine Datei der Art „vektor“."""
    basis = laden.ordner(ds)
    vorhanden = laden.dateien(ds)
    ergebnis: list[Datei] = []
    for gdb in gdb_ordner(vorhanden):
        groesse = sum(p.stat().st_size for p in gdb.rglob("*") if p.is_file())
        ergebnis.append(Datei(str(gdb.relative_to(basis)), str(gdb), "vektor", groesse))
    namen = {p.name.lower() for p in vorhanden}
    for p in vorhanden:
        if gdb_ordner([p]):
            continue
        kopf = _kopf_datei(p) if p.suffix.lower() == ".json" else None
        ergebnis.append(Datei(str(p.relative_to(basis)), str(p), _art(p.name, kopf, namen), p.stat().st_size))
        if p.suffix.lower() == ".zip" and not (p.parent / f"entpackt_{p.stem}").exists():
            ergebnis += _zip_dateien(p, basis)
    return ergebnis


def _zip_dateien(archiv: Path, basis: Path) -> list[Datei]:
    try:
        with zipfile.ZipFile(archiv) as zf:
            eintraege = [i for i in zf.infolist() if not i.is_dir()]
            namen = {Path(i.filename).name.lower() for i in eintraege}
            ergebnis, gdbs = [], {}
            for i in eintraege:
                gdb = next((e for e in Path(i.filename).parents if e.suffix.lower() == ".gdb"), None)
                if gdb is not None:
                    gdbs[str(gdb)] = gdbs.get(str(gdb), 0) + i.file_size
                    continue
                kopf = zf.open(i).read(2000) if i.filename.lower().endswith(".json") else None
                ergebnis.append(Datei(f"{archiv.relative_to(basis)} › {i.filename}", f"/vsizip/{archiv}/{i.filename}",
                                      _art(i.filename, kopf, namen), i.file_size, im_archiv=True))
            for name, groesse in gdbs.items():
                ergebnis.append(Datei(f"{archiv.relative_to(basis)} › {name}", f"/vsizip/{archiv}/{name}", "vektor",
                                      groesse, im_archiv=True))
            return ergebnis
    except zipfile.BadZipFile:
        return []


def tabelle_dateien(dateien: list[Datei]) -> pd.DataFrame:
    """Dateiliste als Tabelle: Datei, Art (für Menschen), Bytes, im Archiv."""
    return pd.DataFrame([{"datei": d.name, "art": ARTEN[d.art], "bytes": d.bytes, "im_archiv": d.im_archiv}
                         for d in dateien], columns=["datei", "art", "bytes", "im_archiv"])


def _bytes_lesen(pfad: str, grenze: int | None = None) -> bytes:
    """Liest eine Datei oder einen Eintrag in einem ZIP (GDAL-Pfad /vsizip/archiv.zip/innen)."""
    if pfad.startswith("/vsizip/"):
        rest = pfad.removeprefix("/vsizip/")
        teil = rest.lower().index(".zip/") + 4
        with zipfile.ZipFile(rest[:teil]) as zf, zf.open(rest[teil + 1:]) as datei:
            return datei.read(grenze) if grenze else datei.read()
    with open(pfad, "rb") as datei:
        return datei.read(grenze) if grenze else datei.read()


# -------------------------------------------------------------------- Vektor

def layer(pfad: str) -> list[tuple[str, str]]:
    """Layer einer Vektorquelle mit Geometrietyp (leer bei reinen Tabellen)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return [(str(name), str(art or "")) for name, art in pyogrio.list_layers(pfad)]


@dataclass
class VektorProbe:
    daten: pd.DataFrame            # GeoDataFrame (mit Geometrie) oder DataFrame (reine Tabelle)
    gesamt: int | None             # Objekte im ganzen Layer
    crs: str | None
    geometrie: str
    nur_essen: bool                # nur das Rechteck um Essen gelesen
    begrenzt: bool                 # mehr Objekte vorhanden als gelesen

    @property
    def felder(self) -> pd.DataFrame:
        return feldtabelle(self.daten.drop(columns="geometry", errors="ignore"))


def vektor_probe(pfad: str, layer_name: str | None = None, anzahl: int = MAX_OBJEKTE) -> VektorProbe:
    """Höchstens `anzahl` Objekte im Rechteck um Essen (ohne Koordinatensystem: die ersten im Layer)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        info = pyogrio.read_info(pfad, layer=layer_name)
        crs = info.get("crs")
        geometrie = str(info.get("geometry_type") or "")
        mit_geometrie = bool(geometrie) and geometrie.lower() != "none"
        bbox = essen_bbox(crs) if crs and mit_geometrie else None
        daten = pyogrio.read_dataframe(pfad, layer=layer_name, bbox=bbox, max_features=anzahl,
                                       read_geometry=mit_geometrie)
    if mit_geometrie and getattr(daten, "crs", None) is None and hasattr(daten, "set_crs"):
        daten = daten.set_crs(WEB_CRS if str(pfad).lower().endswith((".json", ".geojson")) else ZIEL_CRS)
    gesamt = info.get("features")
    gesamt = int(gesamt) if gesamt is not None and gesamt >= 0 else None
    return VektorProbe(daten, gesamt, crs, geometrie if mit_geometrie else "", bbox is not None,
                       len(daten) >= anzahl)


# -------------------------------------------------------------------- Raster

@dataclass
class RasterVorschau:
    bild: np.ndarray               # Höhe × Breite × 4 (RGBA, uint8), in Web-Mercator ausgerichtet
    grenzen: tuple[float, float, float, float]   # west, süd, ost, nord in WGS84
    art: str                       # farbtabelle | legende | rgb | skala
    hinweis: str
    legende: list[tuple[str, str]] = field(default_factory=list)  # (Farbe, Text)
    werte: pd.DataFrame = field(default_factory=pd.DataFrame)       # Klassen (wert, zellen) oder Histogramm (von, bis, zellen)
    stetig: bool = False
    info: dict = field(default_factory=dict)


def _hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(int(v) for v in rgb[:3]))


def _aus_hex(farbe: str) -> tuple[int, int, int]:
    farbe = farbe.lstrip("#")
    return int(farbe[0:2], 16), int(farbe[2:4], 16), int(farbe[4:6], 16)


def raster_vorschau(pfad: str, max_pixel: int = MAX_PIXEL,
                    legende: list[legenden.Eintrag] | None = None) -> RasterVorschau:
    """Ausschnitt Essen als Bild für eine Webkarte, ausgedünnt (nächster Nachbar) auf höchstens `max_pixel`.

    Farben: eingebaute Farbtabelle, sonst RGB-Bänder, sonst eine Legende aus einer Stildatei, wenn sie die
    vorkommenden Werte abdeckt; sonst eine neutrale Skala mit Hinweis. Bedeutungen werden nie geraten (E-009)."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_bounds as from_bounds_transform
    from rasterio.vrt import WarpedVRT

    with rasterio.open(pfad) as quelle:
        if quelle.crs is None:
            raise ValueError("Das Raster hat kein Koordinatensystem; eine Kartenvorschau ist nicht möglich.")
        info = {"breite": quelle.width, "hoehe": quelle.height, "baender": quelle.count, "typ": quelle.dtypes[0],
                "crs": quelle.crs.to_string(), "zellgroesse": abs(quelle.res[0]), "nodata": quelle.nodata,
                "treiber": quelle.driver}
        farbtabelle = {}
        with contextlib.suppress(ValueError):
            farbtabelle = quelle.colormap(1)
        # Ziel: das Rechteck um Essen in Web-Mercator, so fein wie die Datei, höchstens max_pixel Bildpunkte
        x1, y1, x2, y2 = essen_bbox("EPSG:3857")
        mercator_zelle = abs(quelle.res[0]) * (1.6 if quelle.crs.is_projected else 111_000 * 1.6)
        breite, hoehe = max(1.0, (x2 - x1) / mercator_zelle), max(1.0, (y2 - y1) / mercator_zelle)
        faktor = max(1.0, math.sqrt(breite * hoehe / max_pixel))
        form = (max(1, round(hoehe / faktor)), max(1, round(breite / faktor)))
        ziel = from_bounds_transform(x1, y1, x2, y2, form[1], form[0])
        baender = min(3, quelle.count) if quelle.count >= 3 and all(t == "uint8" for t in quelle.dtypes[:3]) else 1
        with WarpedVRT(quelle, crs="EPSG:3857", transform=ziel, width=form[1], height=form[0],
                       resampling=Resampling.nearest) as vrt:
            daten = vrt.read(indexes=list(range(1, baender + 1)), masked=True)
    info["faktor"] = faktor
    west, sued, ost, nord = essen_bbox(WEB_CRS)
    bild = np.zeros((*form, 4), dtype=np.uint8)
    band = daten[0]
    maske = np.ma.getmaskarray(band)
    gueltig = band.compressed()
    werte_tabelle, stetig = _werte(gueltig)

    if farbtabelle and np.issubdtype(band.dtype, np.integer):
        art, hinweis = "farbtabelle", "Farben aus der Farbtabelle der Datei."
        lut = np.zeros((max(256, int(gueltig.max(initial=0)) + 1), 4), dtype=np.uint8)
        for wert, farbe in farbtabelle.items():
            if 0 <= wert < len(lut):
                lut[wert] = farbe[:4] if len(farbe) >= 4 else (*farbe[:3], 255)
        bild[:] = lut[np.clip(np.asarray(band.filled(0)), 0, len(lut) - 1)]
        vorkommend = set(int(w) for w in werte_tabelle["wert"]) if not stetig else set()
        eintraege = [(_hex(f), str(w)) for w, f in sorted(farbtabelle.items()) if w in vorkommend]
    elif baender == 3:
        art, hinweis, eintraege = "rgb", "Die Datei ist ein eingefärbtes Kartenbild (drei Farbbänder).", []
        for i in range(3):
            bild[..., i] = np.asarray(daten[i].filled(0))
        bild[..., 3] = 255
        maske = np.ma.getmaskarray(daten).any(axis=0)
    else:
        passend = _legende_passt(legende or [], werte_tabelle, stetig)
        if passend:
            art, hinweis = "legende", "Farben aus der Stildatei des Anbieters."
            eintraege = [(e.farbe, e.label or str(e.wert)) for e in passend]
            nach_wert = {float(e.wert): _aus_hex(e.farbe) for e in passend}
            flach = np.asarray(band.filled(np.nan if np.issubdtype(band.dtype, np.floating) else 0), dtype=float)
            for wert, rgb in nach_wert.items():
                treffer = flach == wert
                bild[treffer, :3] = rgb
                bild[treffer, 3] = 255
            maske = maske | (bild[..., 3] == 0)
        else:
            art = "skala"
            hinweis = ("Keine Farben in der Datei und keine passende Legende: eine neutrale Skala von niedrigen (hell) "
                       "zu hohen Werten (dunkel). Was die Werte bedeuten, steht in der Beschreibung des Anbieters.")
            if gueltig.size:
                unten, oben = np.percentile(gueltig.astype(float), [2, 98])
                spanne = (oben - unten) or 1.0
                anteil = np.clip((np.asarray(band.filled(unten), dtype=float) - unten) / spanne, 0, 1)[..., None]
                hell, dunkel = np.array(SKALA[0], dtype=float), np.array(SKALA[1], dtype=float)
                bild[..., :3] = (hell + (dunkel - hell) * anteil).astype(np.uint8)
                eintraege = [(_hex(SKALA[0]), f"niedrig ({_kurz(unten)} und weniger)"),
                             (_hex(SKALA[1]), f"hoch ({_kurz(oben)} und mehr)")]
            else:
                eintraege = []
    # Fehlwerte durchsichtig; sonst deckend, außer die Farbtabelle macht einen Wert selbst durchsichtig
    deckkraft = bild[..., 3] if art == "farbtabelle" else 255
    bild[..., 3] = np.where(maske, 0, deckkraft)
    return RasterVorschau(bild, (west, sued, ost, nord), art, hinweis, eintraege, werte_tabelle, stetig, info)


def _kurz(wert: float) -> str:
    return f"{wert:.4g}".replace(".", ",")


def _werte(gueltig: np.ndarray) -> tuple[pd.DataFrame, bool]:
    """Klassen (bis 64 ganzzahlige Werte) oder ein Histogramm mit 20 Stufen."""
    if gueltig.size == 0:
        return pd.DataFrame(columns=["wert", "zellen"]), False
    if np.issubdtype(gueltig.dtype, np.integer):
        werte, anzahl = np.unique(gueltig, return_counts=True)
        if len(werte) <= 64:
            return pd.DataFrame({"wert": werte.astype(int), "zellen": anzahl.astype(int)}), False
    haeufigkeit, kanten = np.histogram(gueltig.astype(float), bins=20)
    return pd.DataFrame({"von": kanten[:-1], "bis": kanten[1:], "zellen": haeufigkeit.astype(int)}), True


def _legende_passt(eintraege: list[legenden.Eintrag], werte: pd.DataFrame, stetig: bool) -> list[legenden.Eintrag]:
    """Legendeneinträge mit Zahlwert und Farbe, wenn sie mindestens 90 % der Zellen abdecken; sonst leer."""
    if stetig or werte.empty:
        return []
    mit_farbe = []
    for e in eintraege:
        try:
            wert = float(str(e.wert).replace(",", "."))
        except (TypeError, ValueError):
            continue
        if e.farbe and str(e.farbe).startswith("#") and len(str(e.farbe)) >= 7:
            mit_farbe.append(legenden.Eintrag(wert, e.label, str(e.farbe)[:7], e.datei))
    if not mit_farbe:
        return []
    bekannt = {e.wert for e in mit_farbe}
    abgedeckt = werte.loc[werte["wert"].astype(float).isin(bekannt), "zellen"].sum()
    if abgedeckt < 0.9 * werte["zellen"].sum():
        return []
    vorkommend = set(werte["wert"].astype(float))
    gesehen, ergebnis = set(), []
    for e in mit_farbe:
        if e.wert in vorkommend and e.wert not in gesehen:
            gesehen.add(e.wert)
            ergebnis.append(e)
    return ergebnis


# -------------------------------------------------------------------- Tabellen und JSON

def tabelle_probe(pfad: str, anzahl: int = MAX_ZEILEN) -> tuple[pd.DataFrame, str]:
    """Die ersten `anzahl` Zeilen einer CSV- oder Textdatei und das erkannte Trennzeichen."""
    roh = _bytes_lesen(pfad, grenze=20_000_000)
    text = roh.decode("utf-8", errors="replace")
    erste = text.splitlines()[:1] or [""]
    trenner = max([";", ",", "\t", "|"], key=lambda t: erste[0].count(t))
    daten = pd.read_csv(io.StringIO(text), sep=trenner, nrows=anzahl, skipinitialspace=True, low_memory=False,
                        on_bad_lines="skip")
    return daten, trenner


@dataclass
class JsonVorschau:
    daten: object | None           # geladene Struktur, None wenn zu groß
    bytes: int
    tabelle: pd.DataFrame | None   # wenn die Daten eine Liste gleichartiger Objekte enthalten


def json_vorschau(pfad: str, max_bytes: int = MAX_JSON_BYTES) -> JsonVorschau:
    """JSON lesen, wenn es nicht zu groß ist; eine Liste von Objekten zusätzlich als Tabelle."""
    roh = _bytes_lesen(pfad, grenze=max_bytes + 1)
    if len(roh) > max_bytes:
        return JsonVorschau(None, len(roh), None)
    daten = json.loads(roh.decode("utf-8", errors="replace"))
    return JsonVorschau(daten, len(roh), _als_tabelle(daten))


def _als_tabelle(daten) -> pd.DataFrame | None:
    kandidaten = [daten] if isinstance(daten, list) else [v for v in daten.values() if isinstance(v, list)] \
        if isinstance(daten, dict) else []
    for liste in kandidaten:
        if liste and all(isinstance(e, dict) for e in liste[:50]):
            return pd.json_normalize(liste[:MAX_ZEILEN], max_level=1)
    return None
