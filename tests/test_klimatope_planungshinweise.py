"""Klimatope und Handlungsbedarf bei Hitze: bekannte Lösung aus erfundenen Daten, Zuordnung, Abbruch bei Unbekanntem."""

import geopandas as gpd
import pandas as pd
import pytest
import shapely

from essen import analysen, kennzahlen, laden
from essen.analysen import klimatope as kt, planungshinweise as ph
from essen.geo import DatenFehlen, vektordatei


def _vergleiche(ergebnis, datei, spalten):
    erwartet = pd.read_csv(datei)
    vergleich = ergebnis.tabelle.merge(erwartet, on="stadtteil", suffixes=("", "_erwartet"))
    assert len(vergleich) == len(erwartet)
    for spalte in spalten:
        mit_wert = vergleich.dropna(subset=[spalte])
        assert (mit_wert[spalte] - mit_wert[f"{spalte}_erwartet"]).abs().max() < 0.06, spalte


def test_zuordnungen_sind_belegt():
    for zuordnung in (kt._zuordnung(), ph._zuordnung()):
        assert zuordnung["geprueft"] is True and zuordnung["quelle"] and zuordnung["vermerk"]
    assert kt._zuordnung()["klassen"][8]["text"] == "Innenstadtklima"
    assert ph._zuordnung()["klassen"][2]["stufe"] == "dringend"


def test_klimatope_bekannte_loesung(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "klimatope", melde=lambda m: None)
    _vergleiche(ergebnis, mit_testdaten["ordner"] / "erwartet_klimatope.csv",
                ["bedeckt_ha", "anteil_dicht_pct", "anteil_locker_pct", "anteil_gruen_wasser_pct", "anteil_verkehr_pct"])
    summe = ergebnis.tabelle[["anteil_dicht_pct", "anteil_locker_pct", "anteil_gruen_wasser_pct",
                              "anteil_verkehr_pct"]].sum(axis=1)
    assert ((summe - 100).abs() < 0.3).all()  # die Gruppen ergeben zusammen die ganze Fläche
    assert 0 < ergebnis.kennzahl_stadt < 100


def test_planungshinweise_bekannte_loesung(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "planungshinweise", melde=lambda m: None)
    _vergleiche(ergebnis, mit_testdaten["ordner"] / "erwartet_planungshinweise.csv",
                ["wirkraum_ha", "anteil_dringend_pct", "anteil_kein_pct"])
    assert "Modell" in ergebnis.kennzahl_text and 0 < ergebnis.kennzahl_stadt < 100


def _aendere(kennung, layer, feld, wert):
    pfad = vektordatei(kennung)
    flaechen = gpd.read_file(pfad, layer=layer)
    flaechen.loc[flaechen.index[0], feld] = wert
    flaechen.to_file(pfad, layer=layer, driver="GPKG")


def test_unbekannter_klimatop_bricht_ab(kopie_testdaten, katalog):
    _aendere("klimaanalyse-klimatope", "PL_KY_KLIMATOP", "KT_R02_2", 42.0)
    with pytest.raises(kt.ZuordnungFehlt, match="ohne Beschreibung vor: 42"):
        analysen.ausfuehren(katalog, "klimatope", melde=lambda m: None)


def test_klimatop_text_muss_zur_zahl_passen(kopie_testdaten, katalog):
    _aendere("klimaanalyse-klimatope", "PL_KY_KLIMATOP", "Klimatoptyp", "Mondklima")
    with pytest.raises(kt.ZuordnungFehlt, match="passen nicht"):
        analysen.ausfuehren(katalog, "klimatope", melde=lambda m: None)


def test_planungshinweis_muss_zur_prioritaet_passen(kopie_testdaten, katalog):
    pfad = vektordatei("klimaanalyse-planungshinweise")
    flaechen = gpd.read_file(pfad, layer="PL_KY_PHK_HP")
    zeile = flaechen.index[flaechen["GN"] == "Essen"][0]
    flaechen.loc[zeile, "Handlungspriorität"] = "Handlungspriorität 1"
    flaechen.loc[zeile, "Planungshinweis"] = "Kein Handlungsbedarf: falsch"
    flaechen.to_file(pfad, layer="PL_KY_PHK_HP", driver="GPKG")
    with pytest.raises(ph.ZuordnungFehlt, match="passen nicht"):
        analysen.ausfuehren(katalog, "planungshinweise", melde=lambda m: None)


def test_fehlende_daten(kopie_testdaten, katalog):
    for kennung, analyse in (("klimaanalyse-klimatope", "klimatope"),
                             ("klimaanalyse-planungshinweise", "planungshinweise")):
        laden.entferne(kennung)
        with pytest.raises(DatenFehlen):
            analysen.ausfuehren(katalog, analyse, melde=lambda m: None)


def test_reparatur_behaelt_nur_flaechen():
    """Wie in der echten Planungshinweiskarte: eine Fläche, die bei der Reparatur zur Linie zusammenfällt."""
    flaeche = shapely.box(0, 0, 10, 10)
    linie = shapely.Polygon([(0, 0), (5, 0), (10, 0), (0, 0)])  # ohne Fläche
    reihe = gpd.GeoSeries([flaeche, linie], crs="EPSG:25832")
    ergebnis = kennzahlen.gueltig(reihe)
    assert set(ergebnis.geom_type) <= {"Polygon", "MultiPolygon"}
    assert ergebnis.iloc[0].area == 100 and ergebnis.iloc[1].is_empty


def test_themenseite_mit_zusammensetzung_und_dazu_passend(kopie_testdaten, katalog):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    app = Path(__file__).resolve().parents[1] / "src" / "essen" / "app"
    for kennung in ("klimatope", "planungshinweise", "hitze-nacht"):
        analysen.ausfuehren(katalog, kennung, melde=lambda m: None)
    at = AppTest.from_file(str(app / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/themen.py")
    at.query_params["thema"] = "klimatope"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    titel = [e.label for e in at.expander]
    assert titel.count("Wie sich die Fläche aufteilt") == 1 and titel.count("Nach Stadtbezirken") == 1
    at.query_params["thema"] = "hitze-nacht"
    at.pills(key="thema-wahl").set_value("hitze-nacht").run()
    assert any("Dazu passend" in m.value for m in at.markdown)
