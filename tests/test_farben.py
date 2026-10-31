"""Alle Farbstufen in essen/farben.py müssen die Prüfung aus dem Skill karte-gestalten bestehen."""

import importlib.util
from pathlib import Path

import pytest

from essen.farben import FARBSTUFEN, HINTERGRUND, KEINE_DATEN

SKRIPT = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "karte-gestalten" / "farben_pruefen.py"
spec = importlib.util.spec_from_file_location("farben_pruefen", SKRIPT)
farben_pruefen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(farben_pruefen)


@pytest.mark.parametrize("name", sorted(FARBSTUFEN))
def test_farbstufen_bestehen_die_pruefung(name):
    ergebnisse = farben_pruefen.pruefe(list(FARBSTUFEN[name]), HINTERGRUND, KEINE_DATEN)
    durchgefallen = [titel for titel, ok, _ in ergebnisse if not ok]
    assert not durchgefallen, durchgefallen


def test_pruefung_erkennt_schlechte_folge():
    ergebnisse = farben_pruefen.pruefe(["#ff0000", "#00ff00", "#0000ff"], HINTERGRUND, KEINE_DATEN)
    assert not all(ok for _, ok, _ in ergebnisse)
