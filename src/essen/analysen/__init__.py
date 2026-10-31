"""Alle Analysen des Projekts.

Neue Analyse: Modul in diesem Ordner mit einer Konstante ANALYSE anlegen und unten in
ALLE eintragen. App und Kommandozeile finden sie dann von selbst. Anleitung: Skill neue-analyse.
"""

from __future__ import annotations

from collections.abc import Callable

from ..katalog import Katalog
from . import (
    betroffenheit,
    gruenanteil,
    haushalte,
    hitze_nacht,
    hitze_tag,
    hitzetage_raster,
    hitzetage_station,
    jungbaeume,
    klimatope,
    kuehlorte,
    laerm,
    luft_station,
    mehrfachbelastung,
    planungshinweise,
    starkregen,
    umweltzone,
    versiegelung,
)
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen, pruefe_daten

ALLE: dict[str, Analyse] = {a.id: a for a in (hitze_nacht.ANALYSE, hitze_tag.ANALYSE, hitzetage_station.ANALYSE,
                                          hitzetage_raster.ANALYSE,
                                          versiegelung.ANALYSE, gruenanteil.ANALYSE, laerm.ANALYSE,
                                          starkregen.ANALYSE, mehrfachbelastung.ANALYSE, luft_station.ANALYSE,
                                          betroffenheit.ANALYSE, planungshinweise.ANALYSE, klimatope.ANALYSE,
                                          kuehlorte.ANALYSE, jungbaeume.ANALYSE,
                                          umweltzone.ANALYSE, haushalte.ANALYSE)}


def hole(kennung: str) -> Analyse:
    try:
        return ALLE[kennung]
    except KeyError:
        raise KeyError(f"Analyse „{kennung}“ gibt es nicht. Vorhanden: {', '.join(ALLE)}") from None


def nutzer(datensatz_id: str) -> list[Analyse]:
    """Analysen, die einen Datensatz brauchen oder optional nutzen."""
    return [a for a in ALLE.values() if datensatz_id in a.benoetigt or datensatz_id in a.optional]


def ausfuehren(katalog: Katalog, kennung: str, parameter: dict | None = None,
               melde: Callable[[str], None] = print, speichern: bool = True) -> Ergebnis:
    """Rechnet eine Analyse und speichert das Ergebnis unter data/processed/<id>/."""
    analyse = hole(kennung)
    werte = analyse.parameter_mit_standard(parameter)
    pruefe_daten(analyse, werte)
    ergebnis = analyse.rechne(Kontext(katalog=katalog, parameter=werte, melde=melde))
    if speichern:
        ergebnis.speichern()
    return ergebnis


__all__ = ["ALLE", "Analyse", "Ergebnis", "Kontext", "Parameter", "Spalte", "Stufen", "ausfuehren", "hole", "nutzer"]
