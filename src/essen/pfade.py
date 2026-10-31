"""Wo das Projekt seine Dateien findet und ablegt.

Die Pfade werden bei jedem Aufruf neu bestimmt. So können Tests, die App und die
Kommandozeile über Umgebungsvariablen umschalten:

    ESSEN_PROJEKT  Projektordner (sonst automatisch gesucht)
    ESSEN_DATEN    Datenordner (sonst <Projekt>/data). Relative Angaben gelten ab dem Projektordner.

Aufbau des Datenordners:

    raw/<datensatz-id>/        geladene Originaldateien und _abruf.json
    processed/<analyse-id>/    Ergebnisse der Analysen
    inspektion/                Berichte von `essen inspizieren`
    zuordnungen/               Vorlagen für Wertezuordnungen (z. B. Rasterklassen)
    export/                    HTML-Seiten zum Ansehen und Weitergeben
    abrufe.csv                 Protokoll aller Downloads
"""

from __future__ import annotations

import os
from pathlib import Path

TESTDATEN_ORDNER = "data_test"
TESTDATEN_MARKE = ".testdaten"


def projekt() -> Path:
    gesetzt = os.environ.get("ESSEN_PROJEKT")
    if gesetzt:
        return Path(gesetzt).expanduser().resolve()
    start = Path.cwd().resolve()
    for ordner in (start, *start.parents):
        if (ordner / "katalog" / "datensaetze.yaml").is_file() and (ordner / "pyproject.toml").is_file():
            return ordner
    return Path(__file__).resolve().parents[2]


def katalog() -> Path:
    return projekt() / "katalog"


def docs() -> Path:
    return projekt() / "docs"


def daten() -> Path:
    gesetzt = os.environ.get("ESSEN_DATEN")
    if gesetzt:
        pfad = Path(gesetzt).expanduser()
        return (pfad if pfad.is_absolute() else projekt() / pfad).resolve()
    return projekt() / "data"


def roh(datensatz_id: str | None = None) -> Path:
    basis = daten() / "raw"
    return basis / datensatz_id if datensatz_id else basis


def verarbeitet(analyse_id: str | None = None) -> Path:
    basis = daten() / "processed"
    return basis / analyse_id if analyse_id else basis


def inspektion() -> Path:
    return daten() / "inspektion"


def zuordnungen() -> Path:
    return daten() / "zuordnungen"


def export() -> Path:
    return daten() / "export"


def abrufprotokoll() -> Path:
    return daten() / "abrufe.csv"


def ist_testdaten() -> bool:
    """True, wenn der aktive Datenordner erfundene Testdaten enthält."""
    return (daten() / TESTDATEN_MARKE).exists()


def relativ(pfad: Path) -> str:
    """Pfad für Meldungen: relativ zum Projektordner, wenn möglich."""
    try:
        return str(Path(pfad).resolve().relative_to(projekt()))
    except ValueError:
        return str(pfad)
