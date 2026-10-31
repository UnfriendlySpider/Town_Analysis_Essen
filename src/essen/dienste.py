"""Kartendienste befragen: Welche Ebenen (WMS) oder Objektarten (WFS) bietet ein Dienst?

Die Antwort (GetCapabilities) wird nur gelesen, nicht gespeichert. Die Namen braucht man,
um einen WMS in der Karte einzublenden oder einen WFS im Katalog als Download einzutragen.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree

import requests

from .laden import ZEITLIMIT, DownloadFehler, _kurz, sitzung


@dataclass(frozen=True)
class Ebene:
    name: str
    titel: str
    beschreibung: str = ""


def capabilities_adresse(url: str, dienst: str) -> str:
    if "request=getcapabilities" in url.lower():
        return url
    trenner = "&" if "?" in url else "?"
    return f"{url}{trenner}SERVICE={dienst.upper()}&REQUEST=GetCapabilities"


def _ohne_namensraum(text: bytes) -> ElementTree.Element:
    baum = ElementTree.fromstring(text)
    for knoten in baum.iter():
        if isinstance(knoten.tag, str) and "}" in knoten.tag:
            knoten.tag = knoten.tag.split("}", 1)[1]
    return baum


def ebenen_aus_xml(text: bytes, dienst: str) -> list[Ebene]:
    baum = _ohne_namensraum(text)
    if baum.tag in ("ServiceExceptionReport", "ExceptionReport"):
        raise DownloadFehler("Der Dienst meldet einen Fehler: " + " ".join(baum.itertext()).strip()[:300])
    ergebnis = []
    if dienst.lower() == "wms":
        for layer in baum.iter("Layer"):
            name = layer.findtext("Name")
            if name:  # nur Ebenen mit Namen lassen sich abrufen
                ergebnis.append(Ebene(name.strip(), (layer.findtext("Title") or "").strip(),
                                      (layer.findtext("Abstract") or "").strip()))
    else:
        for typ in baum.iter("FeatureType"):
            name = typ.findtext("Name")
            if name:
                ergebnis.append(Ebene(name.strip(), (typ.findtext("Title") or "").strip(),
                                      (typ.findtext("Abstract") or "").strip()))
    return ergebnis


def ebenen(url: str, dienst: str = "wms", s: requests.Session | None = None) -> list[Ebene]:
    s = s or sitzung()
    adresse = capabilities_adresse(url, dienst)
    try:
        antwort = s.get(adresse, timeout=ZEITLIMIT)
        antwort.raise_for_status()
    except requests.RequestException as fehler:
        raise DownloadFehler(f"Dienst nicht erreichbar: {_kurz(fehler)}. Adresse: {adresse}") from None
    try:
        return ebenen_aus_xml(antwort.content, dienst)
    except ElementTree.ParseError:
        raise DownloadFehler(f"Die Antwort des Dienstes ist kein gültiges XML: {antwort.text[:200]}") from None
