"""Legenden aus Stildateien lesen: QGIS (.qml), SLD (.sld, .xml) und ArcGIS Pro (.lyrx).

Viele Geodaten kommen mit einer Stildatei, die jedem Wert eine Farbe und eine Beschriftung gibt.
Daraus lässt sich ablesen, wie ein Raster kodiert ist, ohne die PDF-Beschreibung abzutippen.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

STIL_ENDUNGEN = (".qml", ".sld", ".lyrx", ".xml")


@dataclass(frozen=True)
class Eintrag:
    wert: str
    label: str
    farbe: str | None
    datei: str


def _ohne_namensraum(baum: ElementTree.Element) -> ElementTree.Element:
    for knoten in baum.iter():
        if isinstance(knoten.tag, str) and "}" in knoten.tag:
            knoten.tag = knoten.tag.split("}", 1)[1]
        for schluessel in list(knoten.attrib):
            if "}" in schluessel:
                knoten.attrib[schluessel.split("}", 1)[1]] = knoten.attrib.pop(schluessel)
    return baum


def _farbe(text: str | None) -> str | None:
    """QGIS schreibt Farben als '#rrggbb' oder 'r,g,b,a'."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("#") and len(text) in (7, 9):
        return text[:7].lower()
    teile = [t for t in text.replace(";", ",").split(",") if t.strip()]
    if len(teile) >= 3 and all(t.strip().isdigit() for t in teile[:3]):
        r, g, b = (int(t) for t in teile[:3])
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def aus_text(inhalt: str, dateiname: str) -> list[Eintrag]:
    """Liest Legendeneinträge aus dem Inhalt einer Stildatei."""
    if dateiname.lower().endswith(".lyrx"):
        return _aus_lyrx(inhalt, dateiname)
    try:
        baum = _ohne_namensraum(ElementTree.fromstring(inhalt))
    except ElementTree.ParseError:
        return []
    eintraege: list[Eintrag] = []
    # QGIS Raster: paletted renderer und colorrampshader
    for knoten in baum.iter("paletteEntry"):
        eintraege.append(Eintrag(knoten.get("value", ""), knoten.get("label", ""), _farbe(knoten.get("color")), dateiname))
    for knoten in baum.iter("item"):
        if knoten.get("value") is not None and knoten.get("color"):
            eintraege.append(Eintrag(knoten.get("value", ""), knoten.get("label", ""), _farbe(knoten.get("color")), dateiname))
    # QGIS Vektor: kategorisiert und abgestuft
    for knoten in baum.iter("category"):
        eintraege.append(Eintrag(knoten.get("value", ""), knoten.get("label", ""), None, dateiname))
    for knoten in baum.iter("range"):
        wert = f"{knoten.get('lower', '')}–{knoten.get('upper', '')}"
        eintraege.append(Eintrag(wert, knoten.get("label", ""), None, dateiname))
    # SLD
    for knoten in baum.iter("ColorMapEntry"):
        eintraege.append(Eintrag(knoten.get("quantity", ""), knoten.get("label", ""), _farbe(knoten.get("color")), dateiname))
    for regel in baum.iter("Rule"):
        titel = regel.findtext("Title") or regel.findtext("Name") or ""
        literal = regel.findtext(".//Literal")
        farbe = None
        for parameter in regel.iter("CssParameter"):
            if parameter.get("name") == "fill":
                farbe = _farbe(parameter.text)
        for parameter in regel.iter("SvgParameter"):
            if parameter.get("name") == "fill":
                farbe = _farbe(parameter.text)
        if titel or literal:
            eintraege.append(Eintrag(literal or "", titel, farbe, dateiname))
    return eintraege


def _aus_lyrx(inhalt: str, dateiname: str) -> list[Eintrag]:
    try:
        daten = json.loads(inhalt)
    except ValueError:
        return []
    eintraege: list[Eintrag] = []

    def besuche(knoten):
        if isinstance(knoten, dict):
            label = knoten.get("label")
            werte = knoten.get("values") or knoten.get("value")
            if isinstance(label, str) and werte is not None:
                if isinstance(werte, list):
                    werte = ", ".join(str(w.get("fieldValues", w)) if isinstance(w, dict) else str(w) for w in werte)
                eintraege.append(Eintrag(str(werte), label, None, dateiname))
            elif isinstance(label, str) and "upperBound" in knoten:
                eintraege.append(Eintrag(f"bis {knoten['upperBound']}", label, None, dateiname))
            for wert in knoten.values():
                besuche(wert)
        elif isinstance(knoten, list):
            for wert in knoten:
                besuche(wert)

    besuche(daten)
    return eintraege


def aus_pfad(pfad: Path) -> list[Eintrag]:
    """Liest Legenden aus einer Stildatei, einem Ordner oder einem ZIP (auch verschachtelt eine Ebene tief)."""
    pfad = Path(pfad)
    eintraege: list[Eintrag] = []
    if pfad.is_dir():
        for datei in sorted(pfad.rglob("*")):
            if datei.suffix.lower() in STIL_ENDUNGEN or datei.suffix.lower() == ".zip":
                eintraege += aus_pfad(datei)
        return eintraege
    if pfad.suffix.lower() == ".zip":
        with zipfile.ZipFile(pfad) as zf:
            for name in zf.namelist():
                endung = Path(name).suffix.lower()
                if endung in STIL_ENDUNGEN and zf.getinfo(name).file_size < 20_000_000:
                    inhalt = zf.read(name).decode("utf-8", errors="replace")
                    eintraege += aus_text(inhalt, f"{pfad.name}/{name}")
        return eintraege
    if pfad.suffix.lower() in STIL_ENDUNGEN:
        return aus_text(pfad.read_text(encoding="utf-8", errors="replace"), pfad.name)
    return []
