"""Nächtliche Überwärmung je Stadtteil.

Grundlage ist die Klimaanalyse NRW 2026, Klimaanalysekarte Nacht (4 Uhr MEZ, sommerliche
Strahlungsnacht, Modell FITNAH-3D). Für jeden Stadtteil: welcher Anteil der bebauten Fläche
(Wirkraum) liegt in welcher der acht Temperaturklassen, und wie viel davon ist wärmer als 20 °C?

Zwei Wege zu den Klassen:
- Raster (Standard): das GeoTIFF der Klimaanalysekarte. Wie die Klassen darin stecken, steht in
  einer Zuordnung (katalog/zuordnungen/klimaanalyse-nacht-raster.yaml) oder wird aus Legende,
  Farbtabelle oder Wertebereich erkannt.
- Vektor: ein Layer mit Klassenfeld, falls ein GeoPackage einen solchen enthält.

Methodik: docs/methodik/hitze-nacht.md
"""

from __future__ import annotations

import re

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import yaml

from .. import einwohner, kennzahlen, laden, legenden, pfade
from ..farben import FARBSTUFEN
from ..geo import (
    RASTER_ENDUNGEN,
    ZIEL_CRS,
    DatenFehlen,
    lade_stadtteile,
    lies_im_stadtgebiet,
    lies_raster_fenster,
    vektordatei,
)
from ..text import ist_leer, norm, zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen

RASTER_ID = "klimaanalyse-nacht-raster"
VEKTOR_ID = "klimaanalyse-nacht-vektor"
BESCHREIBUNG_ID = "klimaanalyse-beschreibung"

# Klimaanalysekarte Nacht, Wirkraum, 4 Uhr MEZ (LANUK Fachbericht 171, Tabelle 6)
KLASSEN = {
    1: "sehr niedrige nächtliche Lufttemperaturen (bis 14 °C)",
    2: "niedrige nächtliche Lufttemperaturen (14 bis 15,5 °C)",
    3: "keine nächtliche Überwärmung (15,5 bis 17 °C)",
    4: "schwache nächtliche Überwärmung (17 bis 18,5 °C)",
    5: "mäßige nächtliche Überwärmung (18,5 bis 20 °C)",
    6: "starke nächtliche Überwärmung (20 bis 21,5 °C)",
    7: "sehr starke nächtliche Überwärmung (21,5 bis 23 °C)",
    8: "extreme nächtliche Überwärmung (über 23 °C)",
}
GRENZEN_C = [14.0, 15.5, 17.0, 18.5, 20.0, 21.5, 23.0]  # Obergrenzen der Klassen 1 bis 7
AB_STARK = 6       # ab Klasse 6: mehr als 20 °C um 4 Uhr
AB_SEHR_STARK = 7  # ab Klasse 7: mehr als 21,5 °C

# Die Klimaanalyse rechnet zwei Wetterlagen (Methodik Karte Nacht, „Beschreibung des Inhalts“)
SZENARIEN = {"extrem": "extremer Sommertag", "typisch": "typischer Sommertag"}
SZENARIO_STANDARD = "extrem"

# Reihenfolge wichtig: spezifische Begriffe vor allgemeinen ("sehr stark" vor "stark")
TEXT_MUSTER = [
    ("sehr niedrig", 1), ("niedrig", 2), ("keine", 3), ("schwach", 4),
    ("maessig", 5), ("massig", 5), ("sehr stark", 7), ("extrem", 8), ("stark", 6),
]
AUSGLEICH_MUSTER = ("kaltluft", "ausgleich", "volumenstrom", "m³/(s", "m3/(s", "gruen", "freiflaech")
AUSGLEICH = 0  # Klassencode für Flächen, die nicht zum Wirkraum gehören

FARBEN = FARBSTUFEN["waerme"]
STUFEN = Stufen(
    grenzen=(0, 20, 40, 60, 80),
    farben=FARBEN,
    texte=("unter 20 %", "20 bis 40 %", "40 bis 60 %", "60 bis 80 %", "80 % und mehr"),
    keine_daten_text="zu wenig bebaut, kein Anteil",
)


class ZuordnungFehlt(RuntimeError):
    """Die Kodierung des Rasters ist unklar. Die Meldung sagt, wo die Vorlage liegt."""


# -------------------------------------------------------------------- Klassen lesen

def klasse_aus_text(wert) -> int | None:
    if ist_leer(wert):
        return None
    text = norm(wert)
    if "ueberwaerm" not in text and "lufttemperatur" not in text:
        return None  # z. B. Kaltluftklassen im Ausgleichsraum
    for muster, klasse in TEXT_MUSTER:
        if muster in text:
            return klasse
    return None


def klasse_aus_temperatur(wert) -> int | None:
    if ist_leer(wert):
        return None
    temperatur = float(wert)
    for klasse, grenze in enumerate(GRENZEN_C, start=1):
        if temperatur <= grenze:
            return klasse
    return 8


def klasse_aus_code(wert) -> int | None:
    if ist_leer(wert):
        return None
    try:
        code = int(float(wert))
    except (TypeError, ValueError):
        return None
    return code if 1 <= code <= 8 else None


KLASSIERER = {"text": klasse_aus_text, "temperatur": klasse_aus_temperatur, "code": klasse_aus_code}


def temperatur_aus_label(label: str) -> float | None:
    """Eine Temperatur, die für die Beschriftung steht: Mitte einer Spanne, sonst die genannte Grenze.

    Nur Zahlen direkt vor °C zählen; „4 Uhr“ oder „Klasse 3“ werden übergangen.
    """
    text = norm(label)
    text = re.sub(r"\d+\s*uhr", " ", text)
    text = re.sub(r"klasse\s*\d+", " ", text)
    grad = r"\s*(?:°\s*c|grad)"
    zahl_ = r"(\d+(?:[.,]\d+)?)"
    werte = lambda treffer: [float(z.replace(",", ".")) for z in treffer.groups() if z and z[0].isdigit()]  # noqa: E731
    if (treffer := re.search(zahl_ + r"\s*(?:°\s*c)?\s*(?:-|–|bis)\s*" + zahl_ + grad, text)):
        a, b = werte(treffer)
        return (a + b) / 2
    if (treffer := re.search(r"(?:>=|≥|>|ueber|mehr als|ab)\s*" + zahl_ + grad, text)):
        return werte(treffer)[0] + 0.01
    if (treffer := re.search(r"(?:<=|≤|<|bis|unter|weniger als)\s*" + zahl_ + grad, text)):
        return werte(treffer)[0]
    if (treffer := re.search(zahl_ + grad, text)):
        return werte(treffer)[0]
    return None


def klasse_aus_label(label: str) -> int | None:
    """Liest eine Legendenbeschriftung: Klassenname, Temperaturspanne oder Ausgleichsraum.

    Gibt 1 bis 8 für Wirkraumklassen zurück, AUSGLEICH (0) für Kaltluft und Grünflächen, sonst None.
    """
    if not label:
        return None
    text = norm(label)
    if any(m in text for m in ("keine angabe", "keine daten", "keine werte", "nodata", "no data", "ohne daten")):
        return None
    klasse = klasse_aus_text(label)
    if klasse:
        return klasse
    if any(m in text for m in AUSGLEICH_MUSTER):
        return AUSGLEICH
    temperatur = temperatur_aus_label(label)
    return klasse_aus_temperatur(temperatur) if temperatur is not None else None


# -------------------------------------------------------------------- Zuordnung für Raster

def zuordnung_ordner() -> list:
    """Wo Zuordnungen gesucht werden: zuerst im Datenordner (z. B. für Testdaten), dann im Katalog."""
    return [pfade.zuordnungen(), pfade.katalog() / "zuordnungen"]


def lade_zuordnung(kennung: str = RASTER_ID) -> dict | None:
    for ordner in zuordnung_ordner():
        pfad = ordner / f"{kennung}.yaml"
        if pfad.exists():
            try:
                daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as fehler:
                raise ZuordnungFehlt(f"{pfade.relativ(pfad)} ist kein gültiges YAML: {fehler}") from None
            if not isinstance(daten, dict):
                raise ZuordnungFehlt(f"{pfade.relativ(pfad)} hat nicht das erwartete Format (siehe docs/katalog.md).")
            daten["_pfad"] = pfade.relativ(pfad)
            return daten
    return None


def _ziel_klasse(wert, ort: str) -> int | None:
    """Klasse aus einer Zuordnungsdatei: 1 bis 8, ausgleich (0) oder ? (noch offen, None)."""
    if wert is None:
        return None
    if isinstance(wert, str):
        w = norm(wert).strip()
        if w in ("?", ""):
            return None
        if w in ("ausgleich", "ignorieren", "keine", "-"):
            return AUSGLEICH
        if not w.isdigit():
            raise ZuordnungFehlt(f"{ort}: „{wert}“ ist keine Klasse (1 bis 8, ausgleich oder ?).")
        wert = int(w)
    if not isinstance(wert, int) or not 0 <= wert <= 8:
        raise ZuordnungFehlt(f"{ort}: Klasse {wert} ist nicht erlaubt (1 bis 8, ausgleich oder ?).")
    return int(wert)


def schreibe_vorlage(werte: dict[int, int], farben: dict[int, str], vorschlag: dict[int, int | None],
                     legende_quelle: str) -> str:
    """Schreibt eine Zuordnungsvorlage zum Ausfüllen und gibt den Pfad zurück."""
    ziel = pfade.zuordnungen() / f"{RASTER_ID}.vorlage.yaml"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    zeilen = [
        f"# Vorlage: Welche Rasterwerte von {RASTER_ID} gehören zu welcher Klasse?",
        "# Klassen 1 bis 8 laut LANUK Fachbericht 171, Tabelle 6 (8 = extreme nächtliche Überwärmung).",
        "# Grün- und Freiflächen, Kaltluft und alles andere: ausgleich. Noch unklar: \"?\"",
        "# Ausfüllen, `geprueft: true` setzen und nach katalog/zuordnungen/klimaanalyse-nacht-raster.yaml verschieben.",
        f"# Vorschläge stammen aus: {legende_quelle or 'keiner Legende (bitte Beschreibung lesen)'}",
        f"datensatz: {RASTER_ID}",
        "lesart: werte",
        "band: 1",
        "geprueft: false",
        "werte:",
    ]
    for wert, anzahl in sorted(werte.items()):
        klasse = vorschlag.get(wert)
        eintrag = "ausgleich" if klasse == AUSGLEICH else ('"?"' if klasse is None else klasse)
        farbe = f", Farbe {farben[wert]}" if wert in farben else ""
        zeilen.append(f"  {wert}: {eintrag}    # {zahl(anzahl)} Zellen im Stadtgebiet{farbe}")
    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return pfade.relativ(ziel)


def _legende(rastername: str = "") -> tuple[list[legenden.Eintrag], str]:
    """Legenden aus Beschreibung und Rasterordner. Gibt es Stildateien, deren Name zum Raster passt
    (z. B. „nacht“), zählen nur diese, damit keine Legende eines anderen Produkts entscheidet."""
    eintraege: list[legenden.Eintrag] = []
    for kennung in (BESCHREIBUNG_ID, RASTER_ID):
        if laden.vorhanden(kennung):
            eintraege += legenden.aus_pfad(laden.ordner(kennung))
    stichworte = [w for w in ("nacht", "tag", "klimatop", "planung", "betroffen") if w in norm(rastername)]
    passend = [e for e in eintraege if any(w in norm(e.datei) for w in stichworte)]
    if passend:
        eintraege = passend
    quelle = ", ".join(sorted({e.datei for e in eintraege}))
    return eintraege, quelle


def _eindeutig(paare) -> tuple[dict, list]:
    """Aus (Schlüssel, Klasse)-Paaren: eindeutige Zuordnungen und Schlüssel mit Widerspruch."""
    gesammelt: dict = {}
    for schluessel, klasse in paare:
        if klasse is not None:
            gesammelt.setdefault(schluessel, set()).add(klasse)
    eindeutig = {k: next(iter(v)) for k, v in gesammelt.items() if len(v) == 1}
    widerspruch = sorted(k for k, v in gesammelt.items() if len(v) > 1)
    return eindeutig, widerspruch


# -------------------------------------------------------------------- Raster

def _rasterdatei(szenario: str = SZENARIO_STANDARD):
    """Die Datei des Szenarios aus der Zuordnung (dateien). Ohne Zuordnung nur, wenn es genau ein Raster gibt:
    Das echte ZIP enthält Lufttemperatur, Kaltluftvolumenstromdichte und Strömung nebeneinander (E-009)."""
    if not laden.vorhanden(RASTER_ID):
        raise DatenFehlen([RASTER_ID])
    kandidaten = [p for p in laden.entpackt(RASTER_ID) if p.suffix.lower() in RASTER_ENDUNGEN]
    if not kandidaten:
        raise FileNotFoundError(f"Im Datensatz {RASTER_ID} liegt kein Raster ({', '.join(RASTER_ENDUNGEN)}).")
    zuordnung = lade_zuordnung() or {}
    dateien = zuordnung.get("dateien") or {}
    if dateien:
        name = dateien.get(szenario)
        if not name:
            raise ZuordnungFehlt(f"{zuordnung['_pfad']}: keine Datei für das Szenario „{szenario}“ "
                                 f"(vorhanden: {', '.join(dateien)}).")
        treffer = [p for p in kandidaten if p.name.lower() == str(name).lower()]
        if not treffer:
            raise ZuordnungFehlt(f"{zuordnung['_pfad']}: Datei {name} fehlt im Datensatz {RASTER_ID}. "
                                 f"Vorhanden: {', '.join(sorted(p.name for p in kandidaten))}.")
        return treffer[0]
    if len(kandidaten) > 1:
        raise ZuordnungFehlt(
            f"Im Datensatz {RASTER_ID} liegen {len(kandidaten)} Raster ({', '.join(sorted(p.name for p in kandidaten))}). "
            f"Welche Datei die Lufttemperatur enthält, gehört unter dateien in katalog/zuordnungen/{RASTER_ID}.yaml "
            "(Format in docs/katalog.md).")
    return kandidaten[0]


def _farbe_hex(rgba) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(int(x) for x in rgba[:3]))


ABDECKUNG_MIN = 0.99  # so viele gültige Zellen müssen eine Zuordnung haben, sonst Abbruch


def _pruefe_abdeckung(band: np.ndarray, maske: np.ndarray, tabelle: dict[int, int | None], ort: str,
                      hinweise: list[str], als_farbe: bool = False, bereich: np.ndarray | None = None) -> None:
    """Bricht ab, wenn mehr als 1 % der gültigen Zellen in den Stadtteilen (`bereich`) keine Zuordnung haben."""
    auswahl = ~maske if bereich is None or bereich.shape != band.shape else (~maske & bereich)
    gueltig = band[auswahl]
    if gueltig.size == 0:
        raise ValueError("Im Stadtgebiet liegen nur Fehlwerte.")
    werte, anzahl = np.unique(gueltig, return_counts=True)
    offen = {int(w): int(n) for w, n in zip(werte, anzahl, strict=True) if tabelle.get(int(w)) is None}
    if not offen:
        return
    anteil = sum(offen.values()) / gueltig.size
    haeufigste = sorted(offen, key=lambda w: -offen[w])[:10]
    namen = ", ".join((f"#{w:06x}") if als_farbe else str(w) for w in haeufigste)
    mehr = f" und {zahl(len(offen) - 10)} weitere" if len(offen) > 10 else ""
    art = "Farben" if als_farbe else "Rasterwerte"
    if anteil > 1 - ABDECKUNG_MIN:
        raise ZuordnungFehlt(f"{ort}: Für die {art} {namen}{mehr} fehlt eine Klasse "
                             f"({zahl(100 * anteil, 1)} % der Zellen in den Stadtteilen).")
    hinweise.append(f"{art} ohne Zuordnung ({namen}{mehr}; {zahl(100 * anteil, 2)} % der Zellen) zählen nicht zum Wirkraum.")


def _klassen_aus_raster(daten: np.ma.MaskedArray, farbtabelle: dict, dtypes, rastername: str,
                        melde, bereich: np.ndarray | None = None) -> tuple[np.ndarray, str, list[str]]:
    """Wandelt das gelesene Raster in Klassencodes (1 bis 8, 0 = kein Wirkraum)."""
    hinweise: list[str] = []
    zuordnung = lade_zuordnung()

    if zuordnung:
        ort = zuordnung["_pfad"]
        lesart = zuordnung.get("lesart", "werte")
        band_nr = int(zuordnung.get("band", 1))
        if not 1 <= band_nr <= daten.shape[0]:
            raise ZuordnungFehlt(f"{ort}: Band {band_nr} gibt es nicht (das Raster hat {daten.shape[0]}).")
        herkunft = f"Zuordnung {ort}"
        if not zuordnung.get("geprueft", False):
            hinweise.append(f"Die Zuordnung {ort} ist noch nicht als geprüft markiert.")
        if lesart == "temperatur":
            return _klassen_aus_temperatur(daten[band_nr - 1], hinweise), herkunft + " (Temperatur)", hinweise
        if lesart == "farben":
            nach_farbe = {str(f).lower(): _ziel_klasse(k, ort) for f, k in (zuordnung.get("farben") or {}).items()}
            return _klassen_aus_farben(daten, farbtabelle, nach_farbe, ort, hinweise, bereich), herkunft + " (Farben)", hinweise
        if lesart != "werte":
            raise ZuordnungFehlt(f"{ort}: unbekannte lesart „{lesart}“ (werte, temperatur oder farben).")
        tabelle = {int(w): _ziel_klasse(k, ort) for w, k in (zuordnung.get("werte") or {}).items()}
        band = np.ma.filled(daten[band_nr - 1], 0).astype(np.int64)
        maske = np.ma.getmaskarray(daten[band_nr - 1])
        _pruefe_abdeckung(band, maske, tabelle, ort, hinweise, bereich=bereich)
        return _nachschlagen(band, maske, tabelle), herkunft + " (Werte)", hinweise

    # keine Zuordnung: selbst erkennen, aber nur mit eindeutiger Grundlage
    eintraege, quelle = _legende(rastername)
    if daten.shape[0] >= 3 and all(t == "uint8" for t in dtypes[:3]):
        nach_farbe, widerspruch = _eindeutig((e.farbe, klasse_aus_label(e.label)) for e in eintraege if e.farbe)
        if len({k for k in nach_farbe.values() if k}) >= 4:
            hinweise.append(f"Farben aus der Legende zugeordnet ({quelle}). Bitte stichprobenartig prüfen.")
            if widerspruch:
                hinweise.append(f"Widersprüchliche Legendenfarben übergangen: {', '.join(widerspruch)}.")
            return _klassen_aus_farben(daten, {}, nach_farbe, "Legende", hinweise, bereich), "Legende (Farben)", hinweise
        raise ZuordnungFehlt(
            "Das Raster ist eine eingefärbte Karte (RGB). Ohne Legende mit Farben lassen sich die Klassen nicht lesen. "
            "Bitte `uv run essen laden klimaanalyse-beschreibung` und danach `uv run essen inspizieren "
            "klimaanalyse-nacht-raster` ausführen und den Bericht schicken."
        )

    werte = daten[0].compressed()
    if werte.size == 0:
        raise ValueError("Im Stadtgebiet liegen nur Fehlwerte.")
    ist_ganzzahl = np.issubdtype(werte.dtype, np.integer)
    eindeutig, anzahl = np.unique(werte, return_counts=True)
    if not ist_ganzzahl or len(eindeutig) > 64:
        if np.mean((werte >= 5) & (werte <= 35)) > 0.95:
            hinweise.append("Rasterwerte als Lufttemperatur in °C gelesen und nach Tabelle 6 eingeteilt.")
            return _klassen_aus_temperatur(daten[0], hinweise), "Temperaturwerte", hinweise
        if ist_ganzzahl and np.mean((werte >= 50) & (werte <= 350)) > 0.95:
            hinweise.append("Rasterwerte als Zehntelgrad gelesen (215 = 21,5 °C). Bitte mit der Beschreibung abgleichen.")
            return _klassen_aus_temperatur(daten[0].astype(float) / 10, hinweise), "Temperaturwerte in Zehntelgrad", hinweise
        raise ZuordnungFehlt(
            f"Das Raster hat stetige Werte von {zahl(werte.min(), 2)} bis {zahl(werte.max(), 2)}, "
            "die nicht nach Temperatur in °C aussehen. Bitte inspizieren und eine Zuordnung anlegen."
        )

    # Klassenraster: Legende nach Werten, sonst nach Farben der Farbtabelle
    nach_wert, widerspruch = _eindeutig((_als_ganzzahl(e.wert), klasse_aus_label(e.label)) for e in eintraege
                                        if _als_ganzzahl(e.wert) is not None)
    if farbtabelle and len({k for k in nach_wert.values() if k}) < 4:
        nach_farbe, widerspruch_farbe = _eindeutig((e.farbe, klasse_aus_label(e.label)) for e in eintraege if e.farbe)
        for wert in eindeutig:
            farbe = _farbe_hex(farbtabelle[int(wert)]) if int(wert) in farbtabelle else None
            if farbe in nach_farbe:
                nach_wert.setdefault(int(wert), nach_farbe[farbe])
        widerspruch += [f"Farbe {f}" for f in widerspruch_farbe]
    if widerspruch:
        hinweise.append(f"Widersprüchliche Legendeneinträge übergangen: {', '.join(map(str, widerspruch))}.")
    gefunden = {int(w): nach_wert.get(int(w)) for w in eindeutig}
    unbekannt = [w for w, k in gefunden.items() if k is None and w != 0]  # 0 ohne Legende = keine Angabe
    if len({k for k in gefunden.values() if k}) >= 4 and not unbekannt:
        hinweise.append(f"Rasterwerte über die Legende zugeordnet ({quelle}). Bitte stichprobenartig prüfen.")
        band = np.ma.filled(daten[0], 0).astype(np.int64)
        return _nachschlagen(band, np.ma.getmaskarray(daten[0]), {w: k or AUSGLEICH for w, k in gefunden.items()}), \
            "Legende (Werte)", hinweise
    if not eintraege and set(int(w) for w in eindeutig) <= set(range(1, 9)):
        hinweise.append("Rasterwerte 1 bis 8 direkt als Klassen nach Tabelle 6 gelesen. Ohne Legende ungeprüft.")
        band = np.ma.filled(daten[0], 0).astype(np.int64)
        return _nachschlagen(band, np.ma.getmaskarray(daten[0]), {k: k for k in range(1, 9)}), "Werte 1 bis 8", hinweise
    farben = {int(w): _farbe_hex(farbtabelle[int(w)]) for w in eindeutig if int(w) in farbtabelle}
    vorlage = schreibe_vorlage({int(w): int(n) for w, n in zip(eindeutig, anzahl, strict=True)}, farben, gefunden, quelle)
    raise ZuordnungFehlt(
        f"Das Raster hat {len(eindeutig)} Klassenwerte ({', '.join(map(str, eindeutig[:20]))}), deren Bedeutung "
        f"nicht sicher erkannt wurde. Vorlage zum Ausfüllen: {vorlage}. Werte und Farben stehen im Bericht von "
        "`uv run essen inspizieren klimaanalyse-nacht-raster`."
    )


def _als_ganzzahl(wert) -> int | None:
    try:
        zahl_wert = float(wert)
    except (TypeError, ValueError):
        return None
    return int(zahl_wert) if zahl_wert == int(zahl_wert) else None


def _nachschlagen(band: np.ndarray, maske: np.ndarray, tabelle: dict[int, int | None]) -> np.ndarray:
    ergebnis = np.zeros(band.shape, dtype=np.int16)
    for wert, klasse in tabelle.items():
        if klasse:
            ergebnis[(band == wert) & ~maske] = klasse
    return ergebnis


def _klassen_aus_temperatur(band: np.ma.MaskedArray, hinweise: list[str]) -> np.ndarray:
    werte = np.ma.filled(band.astype(float), np.nan)
    ausreisser = np.isfinite(werte) & ((werte < 0) | (werte > 45))
    if ausreisser.any():  # Füllwerte wie -9999 ohne nodata-Angabe
        hinweise.append(f"{zahl(int(ausreisser.sum()))} Zellen mit Werten unter 0 oder über 45 °C als Fehlwert behandelt.")
        werte[ausreisser] = np.nan
    klassen = (1 + np.searchsorted(GRENZEN_C, werte, side="left")).astype(np.int16)
    klassen[np.isnan(werte)] = 0
    return klassen


def _klassen_aus_farben(daten: np.ma.MaskedArray, farbtabelle: dict, nach_farbe: dict[str, int | None], ort: str,
                        hinweise: list[str], bereich: np.ndarray | None = None) -> np.ndarray:
    """Klassen über Farben: RGB-Bänder direkt oder ein Band mit Farbtabelle."""
    if daten.shape[0] >= 3:
        r, g, b = (np.ma.filled(daten[i], 0).astype(np.uint32) for i in range(3))
        codes = (r << 16) | (g << 8) | b
        gueltig = ~np.ma.getmaskarray(daten[0])
        if daten.shape[0] >= 4:
            gueltig &= np.ma.filled(daten[3], 0) > 0  # durchsichtige Zellen
        tabelle = {int(f.lstrip("#"), 16): k for f, k in nach_farbe.items()}
        _pruefe_abdeckung(codes.astype(np.int64), ~gueltig, tabelle, ort, hinweise, als_farbe=True, bereich=bereich)
        ergebnis = np.zeros(codes.shape, dtype=np.int16)
        for code, klasse in tabelle.items():
            if klasse:
                ergebnis[(codes == code) & gueltig] = klasse
        return ergebnis
    if not farbtabelle:
        raise ZuordnungFehlt(f"{ort}: lesart farben braucht ein RGB-Raster oder ein Band mit Farbtabelle.")
    nach_wert = {int(w): nach_farbe.get(_farbe_hex(rgba)) for w, rgba in farbtabelle.items()}
    band = np.ma.filled(daten[0], 0).astype(np.int64)
    maske = np.ma.getmaskarray(daten[0])
    _pruefe_abdeckung(band, maske, nach_wert, ort, hinweise, bereich=bereich)
    return _nachschlagen(band, maske, nach_wert)


def _wirkraum_maske_aus_vektor(klassen: np.ndarray, transform, crs, melde) -> tuple[np.ndarray, str | None]:
    """Bei reinen Temperaturrastern: Kaltluftproduktion und Wasser aus dem GeoPackage ausschließen."""
    if not laden.vorhanden(VEKTOR_ID):
        return klassen, ("Temperaturraster ohne Abgrenzung des Wirkraums: Grün- und Freiflächen sind eingerechnet. "
                         f"Mit {VEKTOR_ID} lassen sie sich ausschließen.")
    from rasterio.features import geometry_mask

    gpkg = vektordatei(VEKTOR_ID)
    ausschluss = [name for name, _ in pyogrio.list_layers(gpkg) if any(t in norm(name) for t in ("produktion", "wasser"))]
    if not ausschluss:
        return klassen, "Im GeoPackage keine Layer für Kaltluftproduktion oder Wasser gefunden; Wirkraum nicht abgegrenzt."
    ergebnis = klassen.copy()
    for layer in ausschluss:
        flaechen = lies_im_stadtgebiet(gpkg, layer=layer).to_crs(crs)
        if flaechen.empty:
            continue
        innen = ~geometry_mask(flaechen.geometry, out_shape=klassen.shape, transform=transform, invert=False)
        ergebnis[innen] = 0
    melde(f"  Wirkraum: Flächen aus {', '.join(ausschluss)} ausgeschlossen")
    return ergebnis, f"Wirkraum näherungsweise abgegrenzt: ohne {', '.join(ausschluss)}."


def flaechen_raster(gebiete: gpd.GeoDataFrame, melde, szenario: str = SZENARIO_STANDARD,
                    raster: dict | None = None) -> tuple[pd.DataFrame, list[str], str]:
    """Fläche je Gebiet und Klasse aus dem Nachtraster. Ist `raster` ein dict, landen dort klassen, transform
    und crs (für die Schätzung der Einwohner)."""
    from rasterio.features import geometry_mask

    pfad = _rasterdatei(szenario)
    melde(f"  Raster: {pfad.name}")
    daten, transform, crs, farbtabelle, dtypes = lies_raster_fenster(pfad, gebiete)
    bereich = ~geometry_mask(gebiete.to_crs(crs).geometry, out_shape=daten.shape[1:], transform=transform)
    klassen, herkunft, hinweise = _klassen_aus_raster(daten, farbtabelle, dtypes, pfad.name, melde, bereich)
    melde(f"  Klassen gelesen über: {herkunft}")
    zuordnung = lade_zuordnung() or {}
    if zuordnung.get("wirkraum") == "fehlwerte":
        hinweise.append("Wirkraum aus dem Raster: Zellen mit Wert sind Siedlungsfläche, Fehlwerte Grün- und Freiflächen.")
    elif herkunft.startswith("Temperatur") or herkunft.endswith("(Temperatur)"):
        klassen, hinweis = _wirkraum_maske_aus_vektor(klassen, transform, crs, melde)
        if hinweis:
            hinweise.append(hinweis)
    flaechen = kennzahlen.flaechen_nach_klasse_raster(gebiete, klassen, transform, crs, list(KLASSEN))
    if raster is not None:
        raster.update(klassen=klassen, transform=transform, crs=crs)
    return flaechen, hinweise, herkunft


# -------------------------------------------------------------------- Vektor

def _textspalten(probe: gpd.GeoDataFrame) -> list[tuple[float, str]]:
    """Spalten, deren Werte wie Klassennamen der Nachtsituation aussehen (nur so wird selbst gewählt)."""
    ergebnisse = []
    for spalte in probe.columns:
        if spalte == probe.geometry.name:
            continue
        werte = probe[spalte].dropna()
        if werte.empty or pd.api.types.is_numeric_dtype(werte):
            continue
        treffer = float(werte.map(klasse_aus_text).notna().mean())
        if treffer > 0:
            ergebnisse.append((treffer, spalte))
    return sorted(ergebnisse, reverse=True)


def flaechen_vektor(gebiete: gpd.GeoDataFrame, parameter: dict, melde) -> tuple[pd.DataFrame, list[str], str]:
    """Klassen aus einem Flächenlayer. Selbst gewählt werden nur Textfelder mit Klassennamen;
    Zahlencodes und Temperaturfelder brauchen feld und lesart von Hand (E-009)."""
    gpkg = vektordatei(VEKTOR_ID)
    layer_wahl, feld_wahl = parameter.get("layer") or None, parameter.get("feld") or None
    lesart_wahl = None if parameter.get("lesart") in (None, "", "auto") else parameter["lesart"]
    if lesart_wahl in ("code", "temperatur") and not feld_wahl:
        raise ZuordnungFehlt(f"Für lesart={lesart_wahl} bitte auch feld (und am besten layer) angeben.")
    kandidaten = []
    for name, geometrie in pyogrio.list_layers(gpkg):
        if (layer_wahl and name != layer_wahl) or not geometrie or "polygon" not in str(geometrie).lower():
            continue
        probe = lies_im_stadtgebiet(gpkg, layer=name, max_features=5000)
        if probe.empty:
            continue
        if feld_wahl:
            if feld_wahl not in probe.columns:
                continue
            art = lesart_wahl or ("text" if any(s == feld_wahl for _, s in _textspalten(probe)) else None)
            if art is None:
                raise ZuordnungFehlt(f"Feld {feld_wahl} in {name} enthält keine Klassennamen. Bitte lesart=code oder "
                                     "lesart=temperatur angeben, wenn die Bedeutung belegt ist.")
            kandidaten.append((9.0, name, feld_wahl, art))
            continue
        for punkte, spalte in _textspalten(probe):
            kandidaten.append((punkte, name, spalte, "text"))
    if not kandidaten:
        raise ZuordnungFehlt(
            f"In {gpkg.name} gibt es keinen Flächenlayer mit Klassennamen der Nachtsituation. Die Klassen stecken "
            "vermutlich im Raster: quelle=raster nehmen. Ein Zahlenfeld nur mit feld, lesart und Beleg verwenden."
        )
    kandidaten.sort(key=lambda k: k[0], reverse=True)
    _, layer, feld, art = kandidaten[0]
    melde(f"  Layer {layer}, Feld {feld}, gelesen als {art}")
    spalten = [feld]
    filter_text = parameter.get("filter") or ""
    if filter_text:
        filter_spalte, _, filter_wert = filter_text.partition("=")
        spalten.append(filter_spalte)
    flaechen = lies_im_stadtgebiet(gpkg, layer=layer, columns=sorted(set(spalten)))
    if filter_text:
        if filter_spalte not in flaechen.columns:
            raise ZuordnungFehlt(f"Die Filterspalte {filter_spalte} gibt es im Layer {layer} nicht.")
        flaechen = flaechen[flaechen[filter_spalte].astype(str).map(norm).str.contains(norm(filter_wert), regex=False)]
    flaechen["klasse"] = flaechen[feld].map(KLASSIERER[art])
    flaechen = flaechen.dropna(subset=["klasse"]).astype({"klasse": int})
    if flaechen.empty:
        raise ZuordnungFehlt("Keine Fläche ließ sich einer Klasse zuordnen. Layer, Feld und Lesart prüfen.")
    hinweise = []
    if art == "temperatur":
        hinweise.append("Ein Temperaturfeld kann auch Grünflächen abdecken. Bei Bedarf mit filter auf den Wirkraum begrenzen.")
    if art == "code":
        hinweise.append("Zahlencodes 1 bis 8 in der Reihenfolge von Tabelle 6 gelesen, wie von Hand angegeben.")
    return kennzahlen.flaechen_nach_klasse(gebiete, flaechen, list(KLASSEN)), hinweise, f"Vektor {layer}.{feld} ({art})"


# -------------------------------------------------------------------- Ablauf

def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    stadtteile = lade_stadtteile(kontext.katalog)
    melde(f"Stadtteile: {stadtteile.anzahl} Flächen, Name aus {stadtteile.name_feld}"
          + (f", Nummer aus {stadtteile.nummer_feld}" if stadtteile.nummer_feld else ", ohne Nummer"))
    gebiete = stadtteile.gdf
    quelle = "vektor" if p["quelle"] == "vektor" else "raster"  # auto = Raster, kein stiller Wechsel (E-009)
    melde(f"Klassen aus: {quelle}")
    szenario = p.get("szenario") or SZENARIO_STANDARD
    if szenario not in SZENARIEN:
        raise ValueError(f"Unbekanntes Szenario „{szenario}“ ({', '.join(SZENARIEN)}).")
    if quelle == "raster":
        melde(f"Szenario: {SZENARIEN[szenario]}")
        raster = {}
        flaechen, hinweise, herkunft = flaechen_raster(gebiete, melde, szenario, raster)
        hinweise.append(f"Szenario der Klimaanalyse: {SZENARIEN[szenario]}.")
        quellen = [stadtteile.datensatz, RASTER_ID] + [k for k in (BESCHREIBUNG_ID, VEKTOR_ID) if laden.vorhanden(k)]
    else:
        if not laden.vorhanden(VEKTOR_ID):
            raise DatenFehlen([VEKTOR_ID])
        flaechen, hinweise, herkunft = flaechen_vektor(gebiete, p, melde)
        quellen = [stadtteile.datensatz, VEKTOR_ID]
    hinweise = stadtteile.hinweise + hinweise

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    wirkraum = flaechen.sum(axis=1)
    tabelle["wirkraum_ha"] = (wirkraum / 1e4).reindex(tabelle.index).fillna(0.0)
    tabelle["anteil_wirkraum_pct"] = 100 * tabelle["wirkraum_ha"] / tabelle["flaeche_ha"]
    anteile = kennzahlen.anteile(flaechen).reindex(tabelle.index)
    tabelle["anteil_ueber_20c_pct"] = anteile[[k for k in KLASSEN if k >= AB_STARK]].sum(axis=1, min_count=1)
    tabelle["anteil_ueber_21_5c_pct"] = anteile[[k for k in KLASSEN if k >= AB_SEHR_STARK]].sum(axis=1, min_count=1)
    for klasse in KLASSEN:
        tabelle[f"klasse_{klasse}_pct"] = anteile[klasse]
    minimum = float(p["min_wirkraum_ha"])
    anteil_spalten = [c for c in tabelle.columns if c.startswith(("anteil_ueber", "klasse_"))]
    tabelle = kennzahlen.mindestbezug(tabelle, "wirkraum_ha", minimum, anteil_spalten,
                                      f"unter {minimum:g} ha bebaut, Anteil nicht ausgewiesen")
    tabelle = tabelle.reset_index()
    runden = {c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha"))}
    tabelle = tabelle.round(runden)

    if quelle == "raster" and einwohner.vorhanden():
        melde("Schätze die Einwohner in Zellen über 20 °C (Zensus-Gitter) …")
        heiss = raster["klassen"] >= AB_STARK
        tabelle, satz = einwohner.ergaenze(
            tabelle, einwohner.in_rastermaske(gebiete, heiss, raster["transform"], raster["crs"]))
        hinweise.append(f"{satz[:-1]} wohnen in Fläche, die nachts über 20 °C liegt. {einwohner.HINWEIS}")
    mit_anteil = tabelle.dropna(subset=["anteil_ueber_20c_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_anteil["anteil_ueber_20c_pct"], mit_anteil["wirkraum_ha"])
    text = ("Kein Stadtteil mit genug bebauter Fläche." if stadtweit is None else
            f"Stadtweit liegen {zahl(stadtweit)} % der bebauten Fläche nachts über 20 °C"
            + (f" ({SZENARIEN[szenario]})." if quelle == "raster" else "."))
    melde(text)
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise + [f"Klassen gelesen über: {herkunft}."],
        quellen=quellen,
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="hitze-nacht",
    verwandt=("planungshinweise", "klimatope", "betroffenheit"),
    gewicht="wirkraum_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Nächtliche Überwärmung je Stadtteil",
    frage="Welcher Anteil der bebauten Fläche ist um 4 Uhr nachts wärmer als 20 °C?",
    themen=("klima",),
    benoetigt=("stadtteile", RASTER_ID),
    optional=(BESCHREIBUNG_ID, VEKTOR_ID, einwohner.DATENSATZ),
    daten_fuer=lambda p: ("stadtteile", VEKTOR_ID) if p.get("quelle") == "vektor" else ("stadtteile", RASTER_ID),
    rechne=rechne,
    kennzahl="anteil_ueber_20c_pct",
    kennzahl_titel="Anteil der bebauten Fläche über 20 °C",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_ueber_20c_pct", "über 20 °C", "prozent", balken=True),
        Spalte("anteil_ueber_21_5c_pct", "über 21,5 °C", "prozent"),
        Spalte("anteil_einwohner_pct", "Einwohner über 20 °C", "prozent"),
        Spalte("wirkraum_ha", "bebaut, ha", "zahl"),
    ),
    parameter=(
        Parameter("quelle", "Datengrundlage", "auto",
                  "automatisch und Raster nehmen das Temperaturraster der Klimaanalyse. Vektordaten nur, wenn ein "
                  "Layer Klassen enthält.", ("auto", "raster", "vektor"), "wahl",
                  beschriftungen={"auto": "automatisch (Raster)", "raster": "Temperaturraster",
                                  "vektor": "Vektordaten mit Klassen"}, selten=True),
        Parameter("szenario", "Wie heiß ist die Nacht?", SZENARIO_STANDARD,
                  "Die Klimaanalyse des Landes rechnet zwei Wetterlagen: einen typischen und einen extrem heißen "
                  "Sommertag mit der Nacht danach. Die extreme Lage zeigt, wie es in Hitzewellen aussieht.",
                  tuple(SZENARIEN), "wahl", beschriftungen={"extrem": "extremer Sommertag (Standard)", "typisch": "typischer Sommertag"}),
        Parameter("min_wirkraum_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken könnte.", typ="zahl",
                  selten=True),
        Parameter("layer", "Layer (nur Vektordaten)", "", "leer = selbst suchen", selten=True),
        Parameter("feld", "Feld (nur Vektordaten)", "", "leer = selbst suchen", selten=True),
        Parameter("lesart", "Lesart des Feldes (nur Vektordaten)", "auto", "Wie die Werte des Feldes zu lesen sind.",
                  ("auto", "text", "temperatur", "code"), "wahl", selten=True),
        Parameter("filter", "Filter SPALTE=WERT (nur Vektordaten)", "", "nur Objekte, deren SPALTE den WERT enthält",
                  selten=True),
    ),
    methodik="methodik/hitze-nacht.md",
    thema_titel="Hitze in der Nacht",
    kurz="Wie viel der bebauten Fläche kühlt in einer heißen Sommernacht kaum ab und ist um 4 Uhr noch wärmer als 20 °C?",
    richtung="hoch_schlecht",
    lesehilfe="Jeder Stadtteil ist nach dem Anteil seiner bebauten Fläche gefärbt, der nachts wärmer als 20 °C bleibt. Je dunkler, desto mehr Fläche bleibt warm. Warme Nächte stören den Schlaf und belasten vor allem ältere Menschen. Parks, Wald und Felder zählen hier nicht mit.",
    grenzen_kurz=(
        "Modellrechnung des Landes NRW für einen sehr heißen Sommertag, keine Messung.",
        "Bezug ist die bebaute Fläche, nicht die Zahl der Menschen.",
        "Innerhalb eines Stadtteils kann es große Unterschiede geben.",
    ),
)
