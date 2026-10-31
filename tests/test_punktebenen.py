"""Punktebenen für die Karte: Felder für Menschen, nur Essen, Fallen der echten Dateien (erfundene Testdaten)."""

import pytest

from essen import karte, punktebenen
from essen.geo import DatenFehlen


def test_alle_ebenen_lesen_ihre_testdaten(mit_testdaten):
    verfuegbar = {e.id for e in punktebenen.verfuegbar()}
    assert verfuegbar == set(punktebenen.PUNKTEBENEN)
    for kennung in verfuegbar:
        punkte = punktebenen.lade(kennung)
        assert len(punkte) > 0 and str(punkte.crs) == "EPSG:4326"
        assert punkte.geometry.geom_type.eq("Point").all()


def test_ladesaeulen_nur_kreisfreie_stadt_essen(mit_testdaten):
    punkte = punktebenen.lade("ladesaeulen")
    assert len(punkte) == 25  # nicht der Ort „Essen“ in Berlin, nicht Bochum
    assert punkte["Leistung (kW)"].eq("22").all() and punkte["in Betrieb seit"].eq("01.01.2024").all()


def test_pegel_nur_im_rechteck_um_essen(mit_testdaten):
    punkte = punktebenen.lade("pegel")
    assert set(punkte["Pegel"]) == {"TESTPEGEL RUHR", "TESTSCHLEUSE OW"}
    assert punkte["Wasserstand beim Abruf"].str.endswith(" cm").all()


def test_kuehlorte_und_baeume_mit_feldern_fuer_menschen(mit_testdaten):
    orte = punktebenen.lade("kuehlorte")
    assert {"Name", "Art", "Ort", "Kosten"} <= set(orte.columns)
    baeume = punktebenen.lade("jungbaeume")
    assert baeume["Pflanzjahr"].min() >= 2008


def test_karte_mit_punkten(mit_testdaten):
    m = karte.neue_karte(canvas=True)
    karte.objekte(m, punktebenen.lade("kuehlorte"), "Kühle Orte <b>", farbe="#2f73a6")
    seite = karte.als_html(m, mit_ebenenwahl=True)
    assert "Testort 1" in seite
    assert "hle Orte <b>" not in seite and "hle Orte \\u003cb\\u003e" not in seite  # Name maskiert
    assert "prefercanvas" in seite.lower()


def test_fehlende_daten(leerer_datenordner):
    assert punktebenen.verfuegbar() == []
    with pytest.raises(DatenFehlen):
        punktebenen.lade("kuehlorte")
