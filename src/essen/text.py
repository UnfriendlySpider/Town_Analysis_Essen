"""Kleine Helfer für Texte und Zahlen im deutschen Format."""

from __future__ import annotations

import math


def norm(wert) -> str:
    """Kleinschreibung, Umlaute als ae/oe/ue/ss. Für robuste Textvergleiche."""
    text = str(wert).lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(alt, neu)
    return text


def ist_leer(wert) -> bool:
    """None, NaN, NaT und pd.NA gelten als leer; Listen und Texte nie."""
    if wert is None:
        return True
    if isinstance(wert, (str, bytes, list, tuple, dict, set)):
        return False
    try:
        import pandas as pd

        return bool(pd.isna(wert))
    except (TypeError, ValueError):
        return False


def zahl(wert, stellen: int = 0) -> str:
    """1234.5 -> '1.234,5'. Leere Werte werden zu '–'."""
    if wert is None or (isinstance(wert, float) and math.isnan(wert)):
        return "–"
    text = f"{float(wert):,.{stellen}f}"
    return text.replace(",", " ").replace(".", ",").replace(" ", ".")


def prozent(wert, stellen: int = 0) -> str:
    return "–" if wert is None or (isinstance(wert, float) and math.isnan(wert)) else f"{zahl(wert, stellen)} %"


def groesse(anzahl_bytes) -> str:
    """Dateigröße in Dezimaleinheiten, wie sie Anbieter angeben."""
    if anzahl_bytes is None:
        return "–"
    wert = float(anzahl_bytes)
    for einheit in ("B", "kB", "MB", "GB", "TB"):
        if wert < 1000 or einheit == "TB":
            return f"{zahl(wert, 0 if einheit in ('B', 'kB') else 1)} {einheit}"
        wert /= 1000
    return "–"


def datum(iso: str | None) -> str:
    """'2026-10-10T12:00:00' -> '10.10.2026'."""
    if not iso:
        return "–"
    teile = str(iso)[:10].split("-")
    return ".".join(reversed(teile)) if len(teile) == 3 else str(iso)


def megabyte(wert) -> str:
    """Größenangabe aus dem Katalog (in MB) im deutschen Format."""
    return "–" if wert is None else f"{float(wert):g}".replace(".", ",") + "\u00a0MB"


def anteil(wert, stellen: int = 1) -> str:
    """0.042 -> '4,2 %'."""
    return "–" if ist_leer(wert) else prozent(100 * float(wert), stellen)


def mehrzahl(anzahl: int, einzahl: str, mehrzahl_form: str) -> str:
    return f"{zahl(anzahl)} {einzahl if anzahl == 1 else mehrzahl_form}"
