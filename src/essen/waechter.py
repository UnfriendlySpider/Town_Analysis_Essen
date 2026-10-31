"""Ergebnis-Wächter: rechnet die Analysen mit Standard-Einstellungen neu und vergleicht die stadtweite Kennzahl
mit festgehaltenen Referenzwerten (docs/referenzwerte.yaml).

So fällt auf, wenn ein neuer Datenstand, eine geänderte Zuordnung oder eine Codeänderung ein Ergebnis
verschiebt. Die Referenzwerte sind Ergebnisse mit echten Daten und werden nur bewusst neu festgeschrieben.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import analysen, pfade
from .geo import DatenFehlen
from .katalog import Katalog

TOLERANZ_ABSOLUT = 0.2    # Prozentpunkte bzw. Einheiten der Kennzahl
TOLERANZ_RELATIV = 0.01   # 1 % des Referenzwerts, falls das mehr ist


def referenzdatei() -> Path:
    return pfade.docs() / "referenzwerte.yaml"


@dataclass
class Pruefung:
    analyse_id: str
    referenz: float | None
    neu: float | None
    zustand: str          # gleich | abweichend | neu | daten_fehlen | fehler | testdaten
    text: str = ""

    @property
    def abweichung(self) -> float | None:
        if self.referenz is None or self.neu is None:
            return None
        return self.neu - self.referenz


def lade_referenzen(pfad: Path | None = None) -> dict:
    pfad = pfad or referenzdatei()
    if not pfad.exists():
        return {}
    return (yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}).get("analysen", {})


def toleranz(referenz: float) -> float:
    return max(TOLERANZ_ABSOLUT, abs(referenz) * TOLERANZ_RELATIV)


def pruefe(katalog: Katalog, ids: list[str] | None = None, melde: Callable[[str], None] = print,
           pfad: Path | None = None, speichern: bool = False) -> list[Pruefung]:
    """Rechnet die gewählten Analysen (Standard: alle mit Referenzwert) und vergleicht."""
    referenzen = lade_referenzen(pfad)
    auswahl = ids or list(referenzen) or list(analysen.ALLE)
    ergebnisse = []
    for kennung in auswahl:
        ref = referenzen.get(kennung, {})
        wert = ref.get("kennzahl_stadt")
        melde(f"{kennung} …")
        if pfade.ist_testdaten() and not ref.get("testdaten"):
            ergebnisse.append(Pruefung(kennung, wert, None, "testdaten", "Referenzwerte gelten für echte Daten"))
            continue
        try:
            ergebnis = analysen.ausfuehren(katalog, kennung, ref.get("parameter") or {}, melde=lambda m: None,
                                           speichern=speichern)
        except DatenFehlen as fehler:
            ergebnisse.append(Pruefung(kennung, wert, None, "daten_fehlen", str(fehler)))
            continue
        except Exception as fehler:  # noqa: BLE001 - jede Analyse soll geprüft werden, auch wenn eine scheitert
            ergebnisse.append(Pruefung(kennung, wert, None, "fehler", f"{type(fehler).__name__}: {fehler}"))
            continue
        neu = ergebnis.kennzahl_stadt
        if wert is None:
            ergebnisse.append(Pruefung(kennung, None, neu, "neu", "noch kein Referenzwert"))
        elif neu is None or abs(neu - wert) > toleranz(wert):
            ergebnisse.append(Pruefung(kennung, wert, neu, "abweichend",
                                       f"Referenz vom {ref.get('datum', '?')}: {ref.get('text', '')}"))
        else:
            ergebnisse.append(Pruefung(kennung, wert, neu, "gleich"))
    return ergebnisse


def festschreiben(katalog: Katalog, ids: list[str] | None = None, melde: Callable[[str], None] = print,
                  pfad: Path | None = None) -> dict:
    """Rechnet die Analysen und schreibt ihre stadtweite Kennzahl als neuen Referenzwert."""
    pfad = pfad or referenzdatei()
    referenzen = lade_referenzen(pfad)
    for kennung in ids or list(analysen.ALLE):
        melde(f"{kennung} …")
        try:
            ergebnis = analysen.ausfuehren(katalog, kennung, referenzen.get(kennung, {}).get("parameter") or {},
                                           melde=lambda m: None)
        except DatenFehlen:
            melde("  übersprungen: Daten fehlen")
            continue
        referenzen[kennung] = {
            "kennzahl_stadt": None if ergebnis.kennzahl_stadt is None else round(float(ergebnis.kennzahl_stadt), 3),
            "text": ergebnis.kennzahl_text,
            "parameter": {k: v for k, v in (referenzen.get(kennung, {}).get("parameter") or {}).items()},
            "datum": dt.date.today().isoformat(),
            "testdaten": ergebnis.testdaten,
        }
    kopf = ("# Referenzwerte für den Ergebnis-Wächter (uv run essen pruefen-ergebnisse).\n"
            "# Stadtweite Kennzahl je Analyse mit Standard-Einstellungen, gerechnet mit echten Daten.\n"
            "# Neu festschreiben nur bewusst: uv run essen pruefen-ergebnisse --festschreiben [ID …]\n")
    pfad.write_text(kopf + yaml.safe_dump({"analysen": referenzen}, allow_unicode=True, sort_keys=True,
                                          width=120), encoding="utf-8")
    return referenzen
