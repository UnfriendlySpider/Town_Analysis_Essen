"""Unbekannte Dateien untersuchen: Layer, Felder, Wertebereiche, Rasterbänder, Legenden.

Ergebnis ist ein Bericht als Markdown (data/inspektion/<id>.md), den man lesen oder
weitergeben kann. Er beantwortet: Was steckt drin, in welchem Koordinatensystem, und
welche Werte kommen im Stadtgebiet vor?
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import math
import warnings
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio

from . import laden, legenden, pfade
from .geo import RASTER_ENDUNGEN, VEKTOR_ENDUNGEN, essen_bbox, gdb_ordner
from .katalog import Katalog
from .text import anteil, groesse, mehrzahl, zahl

MAX_ZELLEN = 16_000_000   # größere Ausschnitte werden für die Statistik ausgedünnt
MAX_EINDEUTIG = 64        # bis zu so vielen verschiedenen Werten gilt ein Band als Klassenraster
PROBE_OBJEKTE = 20_000


@dataclass
class Abschnitt:
    titel: str
    zeilen: list[str] = field(default_factory=list)
    tabelle: pd.DataFrame | None = None


@dataclass
class Bericht:
    titel: str
    gegenstand: str
    abschnitte: list[Abschnitt] = field(default_factory=list)
    legende: list[legenden.Eintrag] = field(default_factory=list)
    rasterwerte: dict[str, dict] = field(default_factory=dict)   # Datei -> {"werte": {wert: anzahl}, "farben": {...}}
    erstellt: str = field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))

    def als_markdown(self) -> str:
        zeilen = [f"# {self.titel}", "", f"Untersucht: `{self.gegenstand}` · {self.erstellt[:16].replace('T', ' ')}", ""]
        if pfade.ist_testdaten():
            zeilen += ["> Achtung: Das sind erfundene Testdaten.", ""]
        for abschnitt in self.abschnitte:
            zeilen += [f"## {abschnitt.titel}", ""]
            zeilen += abschnitt.zeilen
            if abschnitt.zeilen:
                zeilen.append("")
            if abschnitt.tabelle is not None and not abschnitt.tabelle.empty:
                zeilen += [_markdown_tabelle(abschnitt.tabelle), ""]
        if self.legende:
            zeilen += ["## Legenden aus Stildateien", ""]
            tabelle = pd.DataFrame([{"Wert": e.wert, "Beschriftung": e.label, "Farbe": e.farbe or "", "Datei": e.datei}
                                    for e in self.legende])
            zeilen += [_markdown_tabelle(tabelle.head(200)), ""]
        return "\n".join(zeilen)

    def speichern(self, name: str) -> Path:
        ziel = pfade.inspektion() / f"{name}.md"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(self.als_markdown(), encoding="utf-8")
        return ziel


def _markdown_tabelle(df: pd.DataFrame) -> str:
    def zelle(wert) -> str:
        return str(wert).replace("|", "\\|").replace("\n", " ")
    kopf = "| " + " | ".join(map(zelle, df.columns)) + " |"
    trenner = "| " + " | ".join("---" for _ in df.columns) + " |"
    reihen = ["| " + " | ".join(zelle(w) for w in reihe) + " |" for reihe in df.itertuples(index=False)]
    return "\n".join([kopf, trenner, *reihen])


# -------------------------------------------------------------------- Einstieg

def inspiziere_datensatz(katalog: Katalog, kennung: str) -> Bericht:
    """Untersucht alle Dateien eines geladenen Datensatzes."""
    ds = katalog.datensatz(kennung)
    if not laden.vorhanden(ds):
        from .geo import DatenFehlen

        raise DatenFehlen([ds.id])
    bericht = Bericht(titel=f"Inspektion: {ds.titel}", gegenstand=f"{pfade.daten().name}/raw/{ds.id}")
    abruf = laden.lese_abruf(ds)
    bericht.abschnitte.append(Abschnitt("Datensatz", [
        f"- Kennung: `{ds.id}`, Quelle: {katalog.quelle_von(ds).name}",
        f"- Abgerufen am {abruf.datum} von {abruf.url}",
        f"- Lizenz: {katalog.lizenz_von(ds).kurz}",
    ]))
    for archiv in sorted(laden.ordner(ds).glob("*.zip")):
        _zip_inhalt(archiv, bericht)
    _dateien(laden.entpackt(ds), bericht, basis=laden.ordner(ds))
    for archiv in sorted(laden.ordner(ds).rglob("*.zip")):
        if archiv.parent != laden.ordner(ds):  # ZIPs im ZIP: Stildateien darin auch lesen
            bericht.legende += legenden.aus_pfad(archiv)
    for begleitend in ds.begleitend:  # z. B. die Datenbeschreibung mit Legenden
        if laden.vorhanden(begleitend):
            bericht.legende += legenden.aus_pfad(laden.ordner(begleitend))
        else:
            bericht.abschnitte.append(Abschnitt("Begleitende Daten", [
                f"Die Beschreibung `{begleitend}` ist noch nicht geladen. Sie enthält oft Legenden und Feldbedeutungen: "
                f"`uv run essen laden {begleitend}`."]))
    if bericht.rasterwerte and not bericht.legende:
        bericht.abschnitte.append(Abschnitt("Legende", [
            "Keine Stildatei mit Legende gefunden. Die Bedeutung der Werte steht dann meist in einer PDF-Beschreibung."]))
    return bericht


def inspiziere_pfad(pfad: Path) -> Bericht:
    """Untersucht eine beliebige Datei oder einen Ordner."""
    pfad = Path(pfad).expanduser().resolve()
    bericht = Bericht(titel=f"Inspektion: {pfad.name}", gegenstand=pfad.name)
    if pfad.is_dir() and pfad.suffix.lower() == ".gdb":
        _dateien([p for p in pfad.rglob("*") if p.is_file()], bericht, basis=pfad.parent)
    elif pfad.is_dir():
        _dateien(sorted(p for p in pfad.rglob("*") if p.is_file())[:300], bericht, basis=pfad)
    elif pfad.suffix.lower() == ".zip":
        _zip_inhalt(pfad, bericht)
        bericht.legende += legenden.aus_pfad(pfad)
        for name in _zip_namen(pfad, VEKTOR_ENDUNGEN + RASTER_ENDUNGEN):
            _datei(f"/vsizip/{pfad}/{name}", bericht, anzeige=f"{pfad.name}/{name}")
    else:
        _datei(pfad, bericht)
    return bericht


def _dateien(dateien: list[Path], bericht: Bericht, basis: Path) -> None:
    """Dateien beschreiben; File-Geodatabases (.gdb-Ordner) als eine Vektorquelle statt als Dateiliste."""
    for gdb in gdb_ordner(dateien):
        try:
            _vektor(gdb, gdb.name, bericht)
        except Exception as fehler:  # noqa: BLE001 - ein kaputter Teil soll den Bericht nicht verhindern
            bericht.abschnitte.append(Abschnitt(f"{gdb.name}: nicht lesbar", [f"Fehler: {type(fehler).__name__}: "
                                                                              f"{str(fehler).replace(str(basis), '…')}"]))
    for datei in dateien:
        if not gdb_ordner([datei]):
            _datei(datei, bericht, basis=basis)


def _zip_namen(archiv: Path, endungen: tuple[str, ...]) -> list[str]:
    with zipfile.ZipFile(archiv) as zf:
        return [n for n in zf.namelist() if Path(n).suffix.lower() in endungen]


def _zip_inhalt(archiv: Path, bericht: Bericht) -> None:
    with zipfile.ZipFile(archiv) as zf:
        eintraege = [i for i in zf.infolist() if not i.is_dir()]
    zeilen_tabelle, gdbs = [], {}
    for i in eintraege:
        gdb = next((e for e in Path(i.filename).parents if e.suffix.lower() == ".gdb"), None)
        if gdb is not None:  # File-Geodatabase: ein Ordner mit vielen internen Dateien, als eine Zeile
            summe = gdbs.setdefault(str(gdb), [0, 0, 0])
            summe[0] += 1
            summe[1] += i.file_size
            summe[2] += i.compress_size
            continue
        zeilen_tabelle.append({"Datei": i.filename, "Größe": groesse(i.file_size), "gepackt": groesse(i.compress_size),
                               "Methode": "gespeichert" if i.compress_type == zipfile.ZIP_STORED else "komprimiert"})
    for name, (anzahl, roh, gepackt) in gdbs.items():
        zeilen_tabelle.append({"Datei": f"{name}/ (File-Geodatabase, {anzahl} interne Dateien)", "Größe": groesse(roh),
                               "gepackt": groesse(gepackt), "Methode": "komprimiert"})
    tabelle = pd.DataFrame(zeilen_tabelle[:200])
    zeilen = [f"{mehrzahl(len(eintraege), 'Datei', 'Dateien')}, zusammen {groesse(sum(i.file_size for i in eintraege))} entpackt."]
    bericht.abschnitte.append(Abschnitt(f"Inhalt von {archiv.name}", zeilen, tabelle))


def _datei(pfad: Path | str, bericht: Bericht, basis: Path | None = None, anzeige: str | None = None) -> None:
    """Eine Datei beschreiben. `pfad` darf ein GDAL-Pfad wie /vsizip/… sein (dann als Text)."""
    im_archiv = isinstance(pfad, str)
    name = anzeige or Path(pfad).name
    endung = Path(anzeige or str(pfad)).suffix.lower()
    try:
        if im_archiv:
            if endung in VEKTOR_ENDUNGEN:
                _vektor(pfad, name, bericht)
            elif endung in RASTER_ENDUNGEN:
                _raster(pfad, name, bericht)
            return
        if endung in (".geojson", ".json") and not _ist_geojson(pfad):
            _json(pfad, name, bericht)
        elif endung in VEKTOR_ENDUNGEN:
            _vektor(pfad, name, bericht)
        elif endung in RASTER_ENDUNGEN:
            _raster(pfad, name, bericht)
        elif endung in (".csv", ".txt") and pfad.stat().st_size > 0:
            _tabelle(pfad, name, bericht)
        elif endung in legenden.STIL_ENDUNGEN:
            eintraege = legenden.aus_pfad(pfad)
            bericht.legende += eintraege
            if eintraege:
                bericht.abschnitte.append(Abschnitt(f"Stildatei {name}", [f"{len(eintraege)} Legendeneinträge, siehe unten."]))
        elif endung == ".pdf":
            bericht.abschnitte.append(Abschnitt(f"Dokument {name}", [
                f"PDF, {groesse(pfad.stat().st_size)}. Bitte im PDF-Viewer lesen; oft stehen hier Legende und Feldbeschreibung."]))
    except Exception as fehler:  # noqa: BLE001 - ein kaputter Teil soll den Bericht nicht verhindern
        meldung = str(fehler).replace(str(pfad), name)
        if basis is not None:
            meldung = meldung.replace(str(basis), "…")
        bericht.abschnitte.append(Abschnitt(f"{name}: nicht lesbar", [f"Fehler: {type(fehler).__name__}: {meldung}"]))


def _ist_geojson(pfad: Path) -> bool:
    try:
        with open(pfad, encoding="utf-8", errors="replace") as datei:
            anfang = datei.read(2000)
    except OSError:
        return False
    return '"FeatureCollection"' in anfang or '"Feature"' in anfang


# -------------------------------------------------------------------- Vektor

def _vektor(pfad: Path, name: str, bericht: Bericht) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        layer_liste = pyogrio.list_layers(pfad)
    zeilen = [f"{len(layer_liste)} Layer."]
    bericht.abschnitte.append(Abschnitt(f"Vektordatei {name}", zeilen))
    for layer, geometrie in layer_liste:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            info = pyogrio.read_info(pfad, layer=layer)
            crs = info.get("crs")
            bbox = essen_bbox(crs) if crs else None
            probe = pyogrio.read_dataframe(pfad, layer=layer, bbox=bbox, max_features=PROBE_OBJEKTE,
                                           read_geometry=False)
        teile = [
            f"- Geometrie: {geometrie or 'keine'}, Koordinatensystem: {crs or 'unbekannt'}",
            f"- Objekte gesamt: {zahl(info.get('features'))}; im Stadtgebiet (Probe, höchstens {zahl(PROBE_OBJEKTE)}): {zahl(len(probe))}",
        ]
        grenzen = info.get("total_bounds")
        if grenzen is not None and len(grenzen) == 4 and all(np.isfinite(grenzen)):
            teile.append(f"- Ausdehnung: {', '.join(zahl(g, 0) for g in grenzen)}")
        bericht.abschnitte.append(Abschnitt(f"Layer {layer}", teile, feldtabelle(probe)))


def feldtabelle(df: pd.DataFrame) -> pd.DataFrame:
    """Je Feld: Typ, Füllgrad, Anzahl verschiedener Werte, häufigste Werte oder Spanne (für Menschen formatiert)."""
    zeilen = []
    for spalte in df.columns:
        werte = df[spalte]
        gefuellt = werte.notna().mean() if len(werte) else 0
        eindeutig = werte.nunique(dropna=True)
        if pd.api.types.is_numeric_dtype(werte) and not pd.api.types.is_bool_dtype(werte) and eindeutig > 12:
            zahlen = werte.dropna().astype(float)
            beschreibung = (f"{zahl(zahlen.min(), 2)} bis {zahl(zahlen.max(), 2)}, Mittel {zahl(zahlen.mean(), 2)}"
                            if len(zahlen) else "–")
        else:
            haeufig = werte.astype(str).where(werte.notna(), None).value_counts().head(8)
            beschreibung = "; ".join(f"{_abkuerzen(w)} ({zahl(n)})" for w, n in haeufig.items())
        zeilen.append({"Feld": spalte, "Typ": str(werte.dtype), "gefüllt": anteil(gefuellt, 0),
                       "verschiedene": zahl(eindeutig), "häufigste Werte oder Spanne": beschreibung})
    return pd.DataFrame(zeilen)


def _abkuerzen(text, laenge: int = 60) -> str:
    text = str(text)
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


# -------------------------------------------------------------------- Raster

def _raster(pfad: Path, name: str, bericht: Bericht) -> None:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import Window, from_bounds

    with rasterio.open(pfad) as r:
        zeilen = [
            f"- Format: {r.driver}, {zahl(r.width)} × {zahl(r.height)} Zellen, {mehrzahl(r.count, 'Band', 'Bänder')}, Typ {', '.join(sorted(set(r.dtypes)))}",
            f"- Koordinatensystem: {r.crs.to_string() if r.crs else 'unbekannt'}, Zellgröße {zahl(abs(r.res[0]), 2)} × {zahl(abs(r.res[1]), 2)}",
            f"- Ausdehnung: {', '.join(zahl(g, 0) for g in r.bounds)}",
            f"- Fehlwert (nodata): {r.nodata}, Farbdeutung: {', '.join(c.name for c in r.colorinterp)}",
            f"- Kompression: {r.profile.get('compress', 'keine')}, Blöcke: {r.block_shapes[0] if r.block_shapes else '–'}",
        ]
        if r.tags():
            zeilen.append(f"- Metadaten: {_abkuerzen(json.dumps(r.tags(), ensure_ascii=False), 400)}")
        for band in range(1, r.count + 1):
            beschreibung = r.descriptions[band - 1]
            if beschreibung:
                zeilen.append(f"- Band {band}: {beschreibung}")
        farbtabelle = {}
        with contextlib.suppress(ValueError):
            farbtabelle = r.colormap(1)
        if farbtabelle:
            zeilen.append(f"- Band 1 hat eine Farbtabelle mit {len(farbtabelle)} Einträgen.")
        fenster = Window(0, 0, r.width, r.height)
        if r.crs:
            x1, y1, x2, y2 = essen_bbox(r.crs.to_string())
            roh_fenster = from_bounds(x1, y1, x2, y2, r.transform)
            spalte0 = max(0, math.floor(roh_fenster.col_off))
            zeile0 = max(0, math.floor(roh_fenster.row_off))
            spalte1 = min(r.width, math.ceil(roh_fenster.col_off + roh_fenster.width))
            zeile1 = min(r.height, math.ceil(roh_fenster.row_off + roh_fenster.height))
            if spalte1 <= spalte0 or zeile1 <= zeile0:
                zeilen.append("- Das Raster liegt nicht über Essen.")
                bericht.abschnitte.append(Abschnitt(f"Raster {name}", zeilen))
                return
            fenster = Window(spalte0, zeile0, spalte1 - spalte0, zeile1 - zeile0)
        zellen = int(fenster.width * fenster.height)
        faktor = max(1, math.ceil(math.sqrt(zellen / MAX_ZELLEN)))
        form = (r.count, max(1, int(fenster.height // faktor)), max(1, int(fenster.width // faktor)))
        daten = r.read(window=fenster, out_shape=form, masked=True, resampling=Resampling.nearest)
        zeilen.append(f"- Ausschnitt Essen: {zahl(fenster.width)} × {zahl(fenster.height)} Zellen"
                      + (f", für die Statistik jede {faktor}. Zelle" if faktor > 1 else ""))
        bericht.abschnitte.append(Abschnitt(f"Raster {name}", zeilen))
        werte_eintrag: dict = {}
        for band in range(r.count):
            werte = daten[band].compressed()
            titel = f"Band {band + 1} im Stadtgebiet"
            if werte.size == 0:
                bericht.abschnitte.append(Abschnitt(titel, ["Nur Fehlwerte im Ausschnitt."]))
                continue
            eindeutig, anzahl = np.unique(werte, return_counts=True)
            if np.issubdtype(werte.dtype, np.integer) and len(eindeutig) <= MAX_EINDEUTIG:
                farben = farbtabelle if band == 0 else {}
                tabelle = pd.DataFrame({
                    "Wert": eindeutig,
                    "Zellen": [zahl(n) for n in anzahl],
                    "Anteil": [anteil(n / werte.size) for n in anzahl],
                    "Farbe (Tabelle)": ["#{:02x}{:02x}{:02x}".format(*farben[int(w)][:3]) if int(w) in farben else "" for w in eindeutig],
                })
                bericht.abschnitte.append(Abschnitt(titel, [f"{len(eindeutig)} verschiedene Werte: ein Klassenraster."], tabelle))
                if band == 0:
                    werte_eintrag = {
                        "werte": {int(w): int(n) for w, n in zip(eindeutig, anzahl, strict=True)},
                        "farben": {int(w): "#{:02x}{:02x}{:02x}".format(*farben[int(w)][:3]) for w in eindeutig if int(w) in farben},
                    }
            else:
                quantile = np.percentile(werte.astype(float), [5, 50, 95])
                kanten = np.histogram_bin_edges(werte.astype(float), bins=10)
                haeufigkeit, _ = np.histogram(werte.astype(float), bins=kanten)
                tabelle = pd.DataFrame({
                    "von": [zahl(k, 2) for k in kanten[:-1]], "bis": [zahl(k, 2) for k in kanten[1:]],
                    "Zellen": [zahl(n) for n in haeufigkeit],
                })
                bericht.abschnitte.append(Abschnitt(titel, [
                    f"Stetige Werte: {zahl(werte.min(), 2)} bis {zahl(werte.max(), 2)}, Median {zahl(quantile[1], 2)}, "
                    f"5 % unter {zahl(quantile[0], 2)}, 5 % über {zahl(quantile[2], 2)}; {zahl(len(eindeutig))} verschiedene Werte."
                ], tabelle))
                if band == 0:
                    werte_eintrag = {"stetig": True, "min": float(werte.min()), "max": float(werte.max())}
        if r.count >= 3 and all(t == "uint8" for t in r.dtypes[:3]):
            farben = _haeufige_farben(daten[:3])
            bericht.abschnitte.append(Abschnitt("Häufigste Farben (RGB)", ["Das Raster ist vermutlich eine eingefärbte Karte."], farben))
            werte_eintrag["rgb"] = True
        bericht.rasterwerte[name] = werte_eintrag
    for nebendatei in (Path(str(pfad) + ".aux.xml"), Path(str(pfad) + ".vat.dbf")):
        if not str(pfad).startswith("/vsi") and nebendatei.exists():
            bericht.abschnitte.append(Abschnitt(f"Begleitdatei {nebendatei.name}", [
                f"Vorhanden ({groesse(nebendatei.stat().st_size)}). Enthält oft eine Attributtabelle mit den Klassennamen."]))
            if nebendatei.suffix == ".dbf":
                tabelle = pyogrio.read_dataframe(nebendatei, read_geometry=False)
                bericht.abschnitte[-1].tabelle = tabelle.head(64)


def _haeufige_farben(rgb: np.ma.MaskedArray) -> pd.DataFrame:
    gueltig = ~np.ma.getmaskarray(rgb).any(axis=0)
    r, g, b = (np.asarray(rgb[i])[gueltig].astype(np.uint32) for i in range(3))
    codes = (r << 16) | (g << 8) | b
    werte, anzahl = np.unique(codes, return_counts=True)
    reihenfolge = np.argsort(anzahl)[::-1][:30]
    return pd.DataFrame({
        "Farbe": [f"#{werte[i]:06x}" for i in reihenfolge],
        "Zellen": [zahl(anzahl[i]) for i in reihenfolge],
        "Anteil": [anteil(anzahl[i] / codes.size) for i in reihenfolge],
    })


# -------------------------------------------------------------------- Tabellen und JSON

def _tabelle(pfad: Path, name: str, bericht: Bericht) -> None:
    with open(pfad, encoding="utf-8", errors="replace") as datei:
        anfang = [datei.readline() for _ in range(5)]
    trenner = max([";", ",", "\t", "|"], key=lambda t: anfang[0].count(t))
    try:
        df = pd.read_csv(pfad, sep=trenner, nrows=5000, encoding="utf-8", encoding_errors="replace",
                         skipinitialspace=True, low_memory=False)
    except Exception:  # noqa: BLE001 - keine lesbare Tabelle: dann wenigstens die ersten Zeilen zeigen
        bericht.abschnitte.append(Abschnitt(f"Textdatei {name}", ["Erste Zeilen:", "```", *[z.rstrip() for z in anfang], "```"]))
        return
    zeilen = [f"Trennzeichen „{trenner}“, {len(df.columns)} Spalten, Probe von {zahl(len(df))} Zeilen.",
              "Erste Zeilen:", "```", *[z.rstrip()[:200] for z in anfang[:3]], "```"]
    bericht.abschnitte.append(Abschnitt(f"Tabelle {name}", zeilen, feldtabelle(df)))


def _json(pfad: Path, name: str, bericht: Bericht) -> None:
    daten = json.loads(pfad.read_text(encoding="utf-8", errors="replace"))

    def beschreibe(knoten, tiefe=0, schluessel="Wurzel") -> list[str]:
        einzug = "  " * tiefe
        if tiefe > 3:
            return []
        if isinstance(knoten, dict):
            zeilen = [f"{einzug}- {schluessel}: Objekt mit {len(knoten)} Feldern"]
            for k, v in list(knoten.items())[:15]:
                zeilen += beschreibe(v, tiefe + 1, k)
            return zeilen
        if isinstance(knoten, list):
            zeilen = [f"{einzug}- {schluessel}: Liste mit {zahl(len(knoten))} Einträgen"]
            if knoten:
                zeilen += beschreibe(knoten[0], tiefe + 1, "erster Eintrag")
            return zeilen
        return [f"{einzug}- {schluessel}: {_abkuerzen(knoten, 80)}"]

    bericht.abschnitte.append(Abschnitt(f"JSON {name}", beschreibe(daten)))
