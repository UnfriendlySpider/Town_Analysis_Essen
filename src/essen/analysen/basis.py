"""Bausteine jeder Analyse: Beschreibung, Parameter, Ergebnis.

Eine Analyse ist ein Modul in essen/analysen/ mit einer Konstante ANALYSE vom Typ Analyse.
Sie liest nur geladene Daten (data/raw), rechnet und gibt ein Ergebnis zurück. Speichern,
Anzeigen in der App und Export übernimmt der Rahmen. Anleitung: Skill neue-analyse.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import math
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .. import laden, pfade
from ..geo import WEB_CRS, DatenFehlen
from ..katalog import Katalog
from ..text import ist_leer


@dataclass(frozen=True)
class Parameter:
    name: str
    titel: str
    standard: object
    hilfe: str = ""
    optionen: tuple = ()          # feste Auswahl, sonst freie Eingabe
    typ: str = "text"             # text | zahl | ganzzahl | wahl
    beschriftungen: dict = field(default_factory=dict, hash=False, compare=False)  # Wahlwert → Text für Menschen
    selten: bool = False          # nur für Fortgeschrittene (in der App eingeklappt)

    def beschriftung(self, wert) -> str:
        return self.beschriftungen.get(wert, str(wert))


@dataclass(frozen=True)
class Stufen:
    """Farbstufen für Karten: Grenzen (aufsteigend, erste ist die Untergrenze) und je Stufe Farbe und Text."""

    grenzen: tuple[float, ...]
    farben: tuple[str, ...]
    texte: tuple[str, ...]
    keine_daten: str = "#d9ddd8"
    keine_daten_text: str = "keine Angabe"

    def farbe(self, wert) -> str:
        if ist_leer(wert):
            return self.keine_daten
        stufe = 0
        for nummer, grenze in enumerate(self.grenzen):
            if wert >= grenze:
                stufe = nummer
        return self.farben[min(stufe, len(self.farben) - 1)]


@dataclass(frozen=True)
class Spalte:
    """Eine Spalte der Ergebnistabelle, wie sie App und Export zeigen."""

    feld: str
    titel: str
    art: str = "zahl"   # text | zahl | prozent | flaeche
    stellen: int = 0
    balken: bool = False


@dataclass(frozen=True)
class Zeitwert:
    """Ein Wert aus Ergebnis.jahreswerte, der als Karte über die Jahre gezeigt werden kann (essen.zeitkarte).

    Die Stufen gelten für alle Jahre gleich, damit Farben zwischen den Jahren vergleichbar bleiben."""

    feld: str            # Spalte in jahreswerte
    titel: str
    einheit: str
    stufen: Stufen
    stellen: int = 1
    hinweis: str = ""    # z. B. ein Bruch in der Methode, steht unter der Karte
    jahrzehnte: bool = True   # False bei Bestandszahlen (aufsummiert): ein Mittel je Jahrzehnt ergäbe keinen Sinn


@dataclass(frozen=True)
class Analyse:
    id: str
    titel: str
    frage: str
    themen: tuple[str, ...]
    benoetigt: tuple[str, ...]
    rechne: Callable[[Kontext], Ergebnis]
    optional: tuple[str, ...] = ()
    raumbezug: str = "stadtteil"            # stadtteil | station | stadt
    kennzahl: str = ""                      # Hauptspalte der Tabelle
    kennzahl_titel: str = ""
    einheit: str = "%"
    stufen: Stufen | None = None
    spalten: tuple[Spalte, ...] = ()
    parameter: tuple[Parameter, ...] = ()
    methodik: str = ""                      # Pfad unter docs/, z. B. methodik/hitze-nacht.md
    # Erklärungen in einfacher Sprache für die App (Bereich „Essen entdecken“)
    thema_titel: str = ""                   # kurzer Name im Menü, z. B. „Hitze in der Nacht“
    kurz: str = ""                          # ein Satz ohne Fachwörter: worum geht es?
    richtung: str = "neutral"               # hoch_schlecht | hoch_gut | neutral
    lesehilfe: str = ""                     # 2–3 Sätze: so lesen Sie Karte und Zahl
    grenzen_kurz: tuple[str, ...] = ()      # höchstens 3 Punkte: was die Zahl nicht sagt
    daten_fuer: Callable[[dict], tuple[str, ...]] | None = None  # Datenbedarf, wenn er von Parametern abhängt
    zeitachse: tuple[Zeitwert, ...] = ()   # Werte mit Jahreswerten je Stadtteil (Karte über die Jahre)
    # Spalte, mit der die Kennzahl über mehrere Stadtteile gemittelt wird, wie beim stadtweiten Wert (Bezugsfläche,
    # Haushalte …). Damit entstehen Werte je Stadtbezirk (E-018); leer heißt: nicht sinnvoll zusammenzufassen.
    gewicht: str = ""
    # Anteile, die zusammen 100 % ergeben (z. B. Stufen oder Klimatope): die App zeigt sie als gestapelten Balken
    zusammensetzung: tuple[Spalte, ...] = ()
    verwandt: tuple[str, ...] = ()           # andere Themen, die dazu passen (Kasten „Dazu passend“ in der App)

    @property
    def stellen(self) -> int:
        """Nachkommastellen der Hauptkennzahl für Menschen: Anteile und Tage mit einer, sonst ganze Zahlen."""
        return 1 if self.einheit in ("%", "Tage") else 0

    def benoetigt_bei(self, parameter: dict | None = None) -> tuple[str, ...]:
        if self.daten_fuer and parameter is not None:
            return tuple(self.daten_fuer(self.parameter_mit_standard(parameter)))
        return self.benoetigt

    def fehlende_daten(self, parameter: dict | None = None) -> list[str]:
        return [kennung for kennung in self.benoetigt_bei(parameter) if not laden.vorhanden(kennung)]

    def parameter_mit_standard(self, werte: dict | None = None) -> dict:
        ergebnis = {p.name: p.standard for p in self.parameter}
        for name, wert in (werte or {}).items():
            if name not in ergebnis:
                raise ValueError(f"Unbekannter Parameter {name}. Möglich: {', '.join(ergebnis) or 'keine'}")
            ergebnis[name] = _umwandeln(next(p for p in self.parameter if p.name == name), wert)
        return ergebnis


def _umwandeln(parameter: Parameter, wert):
    if wert is None or wert == "":
        return parameter.standard
    try:
        if parameter.typ == "zahl":
            return float(str(wert).replace(",", "."))
        if parameter.typ == "ganzzahl":
            return int(wert)
    except (TypeError, ValueError):
        art = "eine Zahl" if parameter.typ == "zahl" else "eine ganze Zahl"
        raise ValueError(f"{parameter.name}: „{wert}“ ist keine gültige Eingabe, erwartet wird {art}.") from None
    if parameter.optionen and wert not in parameter.optionen:
        raise ValueError(f"{parameter.name}: {wert} ist nicht erlaubt. Möglich: {', '.join(map(str, parameter.optionen))}")
    return wert


@dataclass
class Kontext:
    katalog: Katalog
    parameter: dict
    melde: Callable[[str], None] = print


@dataclass
class Ergebnis:
    analyse_id: str
    tabelle: pd.DataFrame
    kennzahl_text: str
    quellen: list[str]
    parameter: dict
    geometrie: gpd.GeoDataFrame | None = None
    kennzahl_stadt: float | None = None
    hinweise: list[str] = field(default_factory=list)
    jahreswerte: pd.DataFrame | None = None   # optional: eine Zeile je Gebiet und Jahr (Zeitreihen je Stadtteil)
    erstellt: str = field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))
    testdaten: bool = field(default_factory=pfade.ist_testdaten)

    _TABELLEN = ("tabelle", "geometrie", "jahreswerte")  # eigene Dateien, nicht in ergebnis.json

    # ---------------------------------------------------------------- Speichern und Laden

    def speichern(self) -> dict[str, Path]:
        ordner = pfade.verarbeitet(self.analyse_id)
        ordner.mkdir(parents=True, exist_ok=True)
        dateien = {"tabelle": ordner / "tabelle.csv", "ergebnis": ordner / "ergebnis.json"}
        _atomar(dateien["tabelle"], self.tabelle.to_csv(index=False))
        if self.geometrie is not None:
            dateien["geometrie"] = ordner / "gebiete.geojson"
            _atomar(dateien["geometrie"], self.geometrie.to_crs(WEB_CRS).to_json(drop_id=True, ensure_ascii=False))
        elif (ordner / "gebiete.geojson").exists():
            (ordner / "gebiete.geojson").unlink()
        if self.jahreswerte is not None:
            dateien["jahreswerte"] = ordner / "jahreswerte.csv"
            _atomar(dateien["jahreswerte"], self.jahreswerte.to_csv(index=False))
        elif (ordner / "jahreswerte.csv").exists():
            (ordner / "jahreswerte.csv").unlink()
        meta = {f.name: getattr(self, f.name) for f in fields(self) if f.name not in self._TABELLEN}
        meta["kennzahl_stadt"] = None if self.kennzahl_stadt is None or math.isnan(self.kennzahl_stadt) else self.kennzahl_stadt
        _atomar(dateien["ergebnis"], json.dumps(meta, ensure_ascii=False, indent=2, default=str))  # zuletzt: gilt als fertig
        return dateien

    @classmethod
    def laden(cls, analyse_id: str) -> Ergebnis | None:
        """Liest ein gespeichertes Ergebnis. Unvollständige oder alte Ergebnisse gelten als nicht vorhanden.

        Gelesene Ergebnisse bleiben im Speicher, bis sich die Dateien ändern (die App fragt sie je Seite oft ab;
        gebiete.geojson hat einige MB). Zurück kommt jedes Mal eine Kopie, Änderungen daran wirken nicht zurück."""
        gemerkt = cls.ansehen(analyse_id)
        return gemerkt.kopie() if gemerkt is not None else None

    @classmethod
    def ansehen(cls, analyse_id: str) -> Ergebnis | None:
        """Wie `laden`, aber ohne Kopie: das gemerkte Ergebnis selbst. Nur lesen, nie verändern.

        Für Stellen, die nur nachsehen, ob es ein Ergebnis gibt, oder einzelne Werte lesen; die tiefe Kopie mit
        Flächen kostet bei vielen Aufrufen je Seite spürbar Zeit."""
        ordner = pfade.verarbeitet(analyse_id)
        stempel = _stempel(ordner)
        if stempel is None:
            return None
        gemerkt = _GELESEN.get(ordner)
        if gemerkt is None or gemerkt[0] != stempel:
            gemerkt = (stempel, cls._lies(ordner))
            _GELESEN[ordner] = gemerkt
        return gemerkt[1]

    def kopie(self) -> Ergebnis:
        """Kopie mit eigenen Tabellen (die Metadaten sind klein und werden mitkopiert)."""
        neu = copy.deepcopy({f.name: getattr(self, f.name) for f in fields(self) if f.name not in self._TABELLEN})
        return type(self)(tabelle=self.tabelle.copy(),
                          geometrie=None if self.geometrie is None else self.geometrie.copy(),
                          jahreswerte=None if self.jahreswerte is None else self.jahreswerte.copy(), **neu)

    @classmethod
    def _lies(cls, ordner: Path) -> Ergebnis | None:
        meta_pfad = ordner / "ergebnis.json"
        try:
            meta = json.loads(meta_pfad.read_text(encoding="utf-8"))
            if not isinstance(meta, dict):
                raise ValueError("ergebnis.json hat nicht das erwartete Format")
            bekannt = {f.name for f in fields(cls)} - set(cls._TABELLEN)
            meta = {k: v for k, v in meta.items() if k in bekannt}
            tabelle = pd.read_csv(ordner / "tabelle.csv", encoding="utf-8", dtype={"gebiet_id": str})
            geometrie = None
            if (ordner / "gebiete.geojson").exists():
                geometrie = gpd.read_file(ordner / "gebiete.geojson")
                if "gebiet_id" in geometrie.columns:
                    geometrie["gebiet_id"] = geometrie["gebiet_id"].astype(str)
            jahreswerte = None
            if (ordner / "jahreswerte.csv").exists():
                jahreswerte = pd.read_csv(ordner / "jahreswerte.csv", encoding="utf-8", dtype={"gebiet_id": str})
            return cls(tabelle=tabelle, geometrie=geometrie, jahreswerte=jahreswerte, **meta)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as fehler:
            warnings.warn(f"Ergebnis {ordner.name} ist unvollständig und wird ignoriert: {fehler}", stacklevel=3)
            return None


# Gelesene Ergebnisse je Ordner: (Stempel der Dateien, Ergebnis). Siehe Ergebnis.laden.
_GELESEN: dict[Path, tuple[tuple, Ergebnis | None]] = {}


def _stempel(ordner: Path) -> tuple | None:
    """Kennzeichen des gespeicherten Stands: Inode, Zeit und Größe jeder Datei (Speichern ersetzt die Dateien
    durch Umbenennen, die Inode ändert sich also auch bei gleicher Zeit). None, wenn kein Ergebnis da ist."""
    teile = []
    for name in ("ergebnis.json", "tabelle.csv", "gebiete.geojson", "jahreswerte.csv"):
        try:
            st = (ordner / name).stat()
        except OSError:
            if name == "ergebnis.json":
                return None
            teile.append(None)
            continue
        teile.append((st.st_ino, st.st_mtime_ns, st.st_size))
    return tuple(teile)


def _atomar(pfad: Path, text: str) -> None:
    """Erst in eine Nachbardatei schreiben, dann umbenennen: kein halbes Ergebnis nach einem Abbruch."""
    teil = pfad.with_name(pfad.name + ".part")
    teil.write_text(text, encoding="utf-8")
    teil.replace(pfad)


def veraltet(analyse: Analyse, ergebnis: Ergebnis, werte: dict | None = None) -> list[str]:
    """Gründe, warum ein gespeichertes Ergebnis nicht mehr zu den Einstellungen oder Daten passt. Leer: passt."""
    gruende = []
    if werte is not None:
        try:
            soll = analyse.parameter_mit_standard(werte)
        except ValueError:
            soll = {}
        for p in analyse.parameter:
            if p.name in soll and str(ergebnis.parameter.get(p.name)) != str(soll[p.name]):
                gruende.append(f"Einstellung „{p.titel}“: gerechnet mit {p.beschriftung(ergebnis.parameter.get(p.name))}, "
                               f"gewählt ist {p.beschriftung(soll[p.name])}")
    if ergebnis.testdaten != pfade.ist_testdaten():
        gruende.append("gerechnet mit Testdaten" if ergebnis.testdaten else "gerechnet mit echten Daten")
    for kennung in ergebnis.quellen:
        abruf = laden.lese_abruf(kennung)
        if abruf and abruf.zeit > ergebnis.erstellt:
            gruende.append(f"{kennung} wurde danach neu geladen ({abruf.datum})")
        zuordnung = pfade.katalog() / "zuordnungen" / f"{kennung}.yaml"
        if zuordnung.exists():
            geaendert = dt.datetime.fromtimestamp(zuordnung.stat().st_mtime).isoformat(timespec="seconds")
            if geaendert > ergebnis.erstellt:
                gruende.append(f"Zuordnung {kennung} wurde danach geändert ({geaendert[:10]})")
    return gruende


def pruefe_daten(analyse: Analyse, parameter: dict | None = None) -> None:
    fehlend = analyse.fehlende_daten(parameter)
    if fehlend:
        raise DatenFehlen(fehlend)
