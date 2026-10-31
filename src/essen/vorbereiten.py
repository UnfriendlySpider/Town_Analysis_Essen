"""Alles vorbereiten: einmal alle Daten laden, die die Themen brauchen, und alle Analysen rechnen.

Für Menschen ohne Vorwissen: Danach zeigt die App überall Ergebnisse, ohne dass man einzelne Datensätze laden
oder „Berechnen“ drücken muss. Wird von der Seite „Alles vorbereiten“ und von `essen vorbereiten` benutzt.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field

from . import analysen, einwohner, laden, pfade
from .analysen import versiegelung
from .analysen.basis import Ergebnis, veraltet
from .katalog import Katalog

# optional, aber gewünscht: Einwohnerzahlen und der Verlauf der Versiegelung 2006 bis 2018 (10 MB)
ZUSATZ = (einwohner.DATENSATZ, versiegelung.SATELLIT)
ZULETZT = ("mehrfachbelastung",)  # braucht die Ergebnisse der anderen Analysen


@dataclass
class Plan:
    fehlend: list[str]                    # Datensätze, die noch geladen werden müssen
    von_hand: list[str]                   # fehlend, aber nicht automatisch ladbar
    download_mb: float                    # Summe der bekannten Größen (Katalog)
    groesse_unbekannt: list[str]          # fehlend ohne Größenangabe
    frei_gb: float
    zu_rechnen: list[str]                 # Analysen ohne Ergebnis oder mit veraltetem Ergebnis
    aktuell: list[str] = field(default_factory=list)

    @property
    def fertig(self) -> bool:
        return not self.fehlend and not self.zu_rechnen

    @property
    def genug_platz(self) -> bool:
        """Mindestens 5 GB frei und das Zehnfache des Downloads (entpackte Archive sind deutlich größer)."""
        return self.frei_gb > max(5.0, 10 * self.download_mb / 1000)


@dataclass
class Schritt:
    art: str        # laden | rechnen
    kennung: str
    ok: bool
    text: str = ""


def benoetigte_datensaetze() -> list[str]:
    kennungen = []
    for analyse in analysen.ALLE.values():
        for kennung in (*analyse.benoetigt, *ZUSATZ):
            if kennung not in kennungen:
                kennungen.append(kennung)
    return kennungen


def reihenfolge() -> list[str]:
    return [a for a in analysen.ALLE if a not in ZULETZT] + [a for a in ZULETZT if a in analysen.ALLE]


def plan(katalog: Katalog) -> Plan:
    fehlend = [k for k in benoetigte_datensaetze() if k in katalog.datensaetze and not laden.vorhanden(k)]
    von_hand = [k for k in fehlend if not katalog.datensatz(k).ladbar]
    groessen = {k: katalog.datensatz(k).download.groesse_mb for k in fehlend}
    pfade.daten().mkdir(parents=True, exist_ok=True)
    frei_gb = shutil.disk_usage(pfade.daten()).free / 1e9
    zu_rechnen, aktuell = [], []
    for kennung in reihenfolge():
        ergebnis = Ergebnis.laden(kennung)
        if ergebnis is None or veraltet(analysen.hole(kennung), ergebnis, {}):
            zu_rechnen.append(kennung)
        else:
            aktuell.append(kennung)
    return Plan(fehlend=fehlend, von_hand=von_hand, download_mb=sum(g for g in groessen.values() if g),
                groesse_unbekannt=[k for k, g in groessen.items() if not g], frei_gb=frei_gb,
                zu_rechnen=zu_rechnen, aktuell=aktuell)


def ausfuehren(katalog: Katalog, melde: Callable[[str], None] = print,
               fortschritt: laden.Fortschritt | None = None) -> list[Schritt]:
    """Lädt fehlende Daten und rechnet alle Analysen ohne aktuelles Ergebnis. Fehler stoppen nur ihren Schritt."""
    schritte = []
    vorher = plan(katalog)
    for kennung in vorher.fehlend:
        ds = katalog.datensatz(kennung)
        if not ds.ladbar:
            schritte.append(Schritt("laden", kennung, False, f"{ds.titel} lässt sich nicht automatisch laden. "
                                                             "Bitte auf der Seite „Daten laden“ von Hand übernehmen."))
            continue
        melde(f"Lade {ds.titel} …")
        try:
            laden.hole(katalog, ds, fortschritt=fortschritt)
            schritte.append(Schritt("laden", kennung, True))
        except laden.MehrereDateien as fehler:
            schritte.append(Schritt("laden", kennung, False, f"{ds.titel}: mehrere Dateien passen ({fehler}). "
                                                             "Bitte auf der Seite „Daten laden“ eine auswählen."))
        except laden.DownloadFehler as fehler:
            schritte.append(Schritt("laden", kennung, False, f"{ds.titel}: {fehler}"))
    for kennung in plan(katalog).zu_rechnen:
        analyse = analysen.hole(kennung)
        if analyse.fehlende_daten():
            schritte.append(Schritt("rechnen", kennung, False, f"{analyse.thema_titel or analyse.titel}: es fehlen "
                                                               f"noch Daten ({', '.join(analyse.fehlende_daten())})."))
            continue
        melde(f"Berechne {analyse.thema_titel or analyse.titel} …")
        try:
            analysen.ausfuehren(katalog, kennung, melde=lambda m: None)
            schritte.append(Schritt("rechnen", kennung, True))
        except Exception as fehler:  # noqa: BLE001 - die übrigen Themen sollen trotzdem fertig werden
            schritte.append(Schritt("rechnen", kennung, False,
                                    f"{analyse.thema_titel or analyse.titel}: {type(fehler).__name__}: {fehler}"))
    return schritte


def ist_vorbereitet() -> bool:
    """Gibt es für jede Analyse ein gespeichertes Ergebnis? Schnell: prüft nur, ob die Dateien da sind."""
    return all((pfade.verarbeitet(kennung) / "ergebnis.json").exists() for kennung in analysen.ALLE)
