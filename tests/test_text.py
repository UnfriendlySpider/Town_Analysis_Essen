"""Zahlen und Texte im deutschen Format (essen.text), wie die App sie zeigt."""

import math

import pandas as pd

from essen.text import anteil, datum, groesse, ist_leer, megabyte, mehrzahl, norm, prozent, zahl


def test_zahl_deutsch():
    assert zahl(1234.5, 1) == "1.234,5"
    assert zahl(1234567) == "1.234.567"
    assert zahl(-0.25, 2) == "-0,25"
    assert zahl(0) == "0"
    assert zahl(None) == "–" and zahl(math.nan) == "–"


def test_prozent_und_anteil():  # mit geschütztem Leerzeichen vor der Einheit
    assert prozent(12.345, 1) == "12,3\u00a0%"
    assert prozent(None) == "–"
    assert anteil(0.042) == "4,2\u00a0%"
    assert anteil(pd.NA) == "–" and anteil(None) == "–"


def test_groesse_in_dezimaleinheiten():
    assert groesse(999) == "999\u00a0B"
    assert groesse(1500) == "2\u00a0kB"
    assert groesse(2_500_000) == "2,5\u00a0MB"
    assert groesse(7_700_000_000) == "7,7\u00a0GB"
    assert groesse(None) == "–"


def test_datum_und_megabyte():
    assert datum("2026-10-11T12:00:00") == "11.10.2026"
    assert datum(None) == "–" and datum("2026") == "2026"
    assert megabyte(541.0) == "541 MB" and megabyte(62.6) == "62,6 MB" and megabyte(None) == "–"


def test_mehrzahl_norm_und_leer():
    assert mehrzahl(1, "Datei", "Dateien") == "1 Datei"
    assert mehrzahl(1200, "Datei", "Dateien") == "1.200 Dateien"
    assert norm("Grünfläche Straße") == "gruenflaeche strasse"
    assert ist_leer(None) and ist_leer(math.nan) and ist_leer(pd.NaT)
    assert not ist_leer("") and not ist_leer([]) and not ist_leer(0)
