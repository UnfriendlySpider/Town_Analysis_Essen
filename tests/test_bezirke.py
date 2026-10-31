"""Werte je Stadtbezirk (E-018): gewichtet wie der stadtweite Wert, Zuordnung aus der Stadtteildatei."""

import dataclasses
from pathlib import Path

import geopandas as gpd
import pytest

from essen import analysen, bezirke, kennzahlen, steckbrief
from essen.geo import vektordatei

APP = Path(__file__).resolve().parents[1] / "src" / "essen" / "app"


def test_name_roemisch():
    assert bezirke.name(1) == "Stadtbezirk I" and bezirke.name(9) == "Stadtbezirk IX"


def test_bekannte_loesung_und_gegenprobe(kopie_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "versiegelung", melde=lambda m: None)
    roh = gpd.read_file(vektordatei("stadtteile"))
    zuordnung = dict(zip(roh["STADTT"].astype(int).astype(str), roh["STADTBEZ"].astype(int), strict=True))
    assert bezirke.zuordnung(katalog) == zuordnung
    t = ergebnis.tabelle.assign(bezirk=ergebnis.tabelle["gebiet_id"].map(zuordnung)).dropna(subset=["anteil_versiegelt_pct"])
    erwartet = {b: (g["anteil_versiegelt_pct"] * g["bewertet_ha"]).sum() / g["bewertet_ha"].sum()
                for b, g in t.groupby("bezirk")}
    je_bezirk = bezirke.je_bezirk(katalog, "versiegelung")
    assert set(je_bezirk["bezirk"]) == set(erwartet)
    for zeile in je_bezirk.itertuples():
        assert zeile.wert == pytest.approx(erwartet[zeile.bezirk])
    # Summe/Summe über die Bezirke ergibt wieder den Wert für ganz Essen
    assert kennzahlen.gewichtetes_mittel(je_bezirk["wert"], je_bezirk["gewicht"]) == pytest.approx(
        ergebnis.kennzahl_stadt, abs=0.01)


def test_ohne_gewicht_keine_bezirkswerte(kopie_testdaten, katalog):
    for kennung in ("hitze-nacht", "laerm", "starkregen"):
        analysen.ausfuehren(katalog, kennung, melde=lambda m: None)
    analysen.ausfuehren(katalog, "mehrfachbelastung", melde=lambda m: None)
    assert bezirke.je_bezirk(katalog, "mehrfachbelastung").empty  # Zählung von Themen, nicht zusammenfassbar (E-008)
    assert not bezirke.je_bezirk(katalog, "starkregen").empty


def test_ohne_feld_im_katalog_keine_bezirke(kopie_testdaten, katalog):
    ds = katalog.datensatz("stadtteile")
    katalog.datensaetze["stadtteile"] = dataclasses.replace(ds, felder={k: v for k, v in ds.felder.items()
                                                                         if k != "bezirk"})
    try:
        assert bezirke.zuordnung(katalog) == {}
        analysen.ausfuehren(katalog, "versiegelung", melde=lambda m: None)
        assert bezirke.je_bezirk(katalog, "versiegelung").empty
    finally:
        katalog.datensaetze["stadtteile"] = ds


def test_steckbrief_und_seite_mit_bezirk(kopie_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    analysen.ausfuehren(katalog, "versiegelung", melde=lambda m: None)
    gebiet = steckbrief.tabelle()["gebiet_id"].iloc[0]
    zeilen = steckbrief.stadtteil(gebiet, katalog)
    assert zeilen["bezirk"].notna().all()
    # die Kopie der Testdaten enthält auch Ergebnisse anderer Tests; geprüft wird das hier gerechnete
    zeile = zeilen.set_index("analyse_id").loc["versiegelung"]
    werte = bezirke.je_bezirk(katalog, "versiegelung").set_index("bezirk")["wert"]
    assert zeile["wert_bezirk"] == pytest.approx(werte[zeile["bezirk"]])
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/stadtteil.py")
    at.query_params["stadtteil"] = gebiet
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("gehört zum" in m.value and "Stadtbezirk" in m.value for m in at.markdown)
