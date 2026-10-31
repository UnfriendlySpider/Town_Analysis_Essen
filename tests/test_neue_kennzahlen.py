"""Jungbäume, kühle Orte und Umweltzone je Stadtteil: bekannte Lösungen mit kleinen erfundenen Daten."""

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

from essen import analysen, laden, pfade
from essen.geo import DatenFehlen


def test_alle_drei_mit_testdaten(mit_testdaten, katalog):
    for kennung in ("jungbaeume", "kuehlorte", "umweltzone"):
        analyse = analysen.hole(kennung)
        ergebnis = analysen.ausfuehren(katalog, kennung, melde=lambda m: None, speichern=False)
        werte = ergebnis.tabelle[analyse.kennzahl]
        assert len(ergebnis.tabelle) == 12 and werte.notna().all(), kennung
        assert {"gebiet_id", "stadtteil", "stadtteil_nr"} <= set(ergebnis.tabelle.columns)
        assert ergebnis.kennzahl_stadt is not None and ergebnis.geometrie is not None


def test_jungbaeume_zaehlen_alle_und_ab_jahr(mit_testdaten, katalog):
    alle = analysen.ausfuehren(katalog, "jungbaeume", melde=lambda m: None, speichern=False)
    assert alle.tabelle["anzahl_baeume"].sum() == 300  # alle erfundenen Bäume liegen im Umriss
    flaeche_km2 = alle.tabelle["flaeche_ha"].sum() / 100
    assert alle.kennzahl_stadt == pytest.approx(300 / flaeche_km2)
    spaet = analysen.ausfuehren(katalog, "jungbaeume", {"ab_jahr": 2020}, melde=lambda m: None, speichern=False)
    assert 0 < spaet.tabelle["anzahl_baeume"].sum() < 300



def test_jungbaeume_ueber_die_jahre(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "jungbaeume", melde=lambda m: None, speichern=False)
    jahre = ergebnis.jahreswerte
    assert jahre["gepflanzt"].sum() == 300 and sorted(jahre["jahr"].unique()) == list(range(2008, 2026))
    for _, teil in jahre.groupby("gebiet_id"):  # Bestand wächst nur, letzter Stand = Kennzahl der Tabelle
        assert teil.sort_values("jahr")["baeume_je_km2"].is_monotonic_increasing
    letztes = jahre[jahre["jahr"] == 2025].set_index("gebiet_id")["baeume_je_km2"]
    tabelle = ergebnis.tabelle.set_index("gebiet_id")["baeume_je_km2"]
    assert letztes.reindex(tabelle.index).round(1).tolist() == tabelle.tolist()
    abgerufen = int(laden.lese_abruf("stadtbaeume").zeit[:4])
    assert not jahre[jahre["jahr"] >= abgerufen]["vollstaendig"].any()
    assert any("gefällte" in h for h in ergebnis.hinweise)


def _ein_gebiet(ordner, kante=1000.0):
    """Ein quadratischer Stadtteil (1 km²) in der Mitte des Rechtecks um Essen."""
    gebiet = box(361000, 5702000, 361000 + kante, 5702000 + kante)
    gdf = gpd.GeoDataFrame({"STADTTEILE": ["Quadrat"], "STADTT": [1]}, geometry=[gebiet], crs="EPSG:25832")
    ziel = pfade.roh("stadtteile")
    ziel.mkdir(parents=True, exist_ok=True)
    for alt in ziel.iterdir():
        alt.unlink()
    gdf.to_crs("EPSG:4326").to_file(ziel / "Stadtteile_WGS84.geojson", driver="GeoJSON")
    from essen.testdaten import _abruf

    _abruf("stadtteile", ["Stadtteile_WGS84.geojson"], "dl-de-by-2.0", "essen-opendata")
    return gebiet


def _punkte(kennung, datei, punkte, felder):
    ziel = pfade.roh(kennung)
    for alt in ziel.iterdir():
        alt.unlink()
    gpd.GeoDataFrame(felder, geometry=punkte, crs="EPSG:25832").to_crs("EPSG:4326").to_file(ziel / datei,
                                                                                         driver="GeoJSON")
    from essen.testdaten import _abruf

    _abruf(kennung, [datei], "dl-de-by-2.0", "essen-opendata")


def test_kuehlorte_bekannte_flaeche(kopie_testdaten, katalog):
    gebiet = _ein_gebiet(kopie_testdaten)
    mitte = gebiet.centroid
    # ein Ort in der Mitte: Kreis mit 300 m Radius liegt ganz im Quadrat → π·0,09 km² von 1 km²
    _punkte("kuehlorte", "Kuehle_Orte.geojson", [Point(mitte.x, mitte.y), Point(mitte.x + 100, mitte.y)],
            {"ORT": ["Außen", "Innen"], "NAME": ["a", "b"]})
    ergebnis = analysen.ausfuehren(katalog, "kuehlorte", {"orte": "draussen"}, melde=lambda m: None, speichern=False)
    assert ergebnis.tabelle.loc[0, "anteil_nah_pct"] == pytest.approx(100 * 3.14159 * 0.09, abs=0.3)
    beide = analysen.ausfuehren(katalog, "kuehlorte", melde=lambda m: None, speichern=False)
    assert beide.tabelle.loc[0, "anzahl_orte"] == 2
    assert beide.tabelle.loc[0, "anteil_nah_pct"] > ergebnis.tabelle.loc[0, "anteil_nah_pct"]  # Vereinigung, nicht doppelt
    assert beide.tabelle.loc[0, "anteil_nah_pct"] < 2 * ergebnis.tabelle.loc[0, "anteil_nah_pct"]


def test_umweltzone_loecher_zaehlen_nicht(kopie_testdaten, katalog):
    gebiet = _ein_gebiet(kopie_testdaten)
    zone = gebiet.difference(gebiet.centroid.buffer(200))  # Quadrat mit Loch
    ziel = pfade.roh("umweltzone")
    for alt in ziel.iterdir():
        alt.unlink()
    gpd.GeoDataFrame({"OBJECTID": [1]}, geometry=[zone], crs="EPSG:25832").to_crs("EPSG:4326").to_file(
        ziel / "Umweltzone_Essen_0.geojson", driver="GeoJSON")
    from essen.testdaten import _abruf

    _abruf("umweltzone", ["Umweltzone_Essen_0.geojson"], "dl-de-by-2.0", "essen-opendata")
    ergebnis = analysen.ausfuehren(katalog, "umweltzone", melde=lambda m: None, speichern=False)
    assert ergebnis.tabelle.loc[0, "anteil_zone_pct"] == pytest.approx(100 * (1 - 3.14159 * 0.04), abs=0.3)


@pytest.mark.parametrize("kennung, datensatz", [("jungbaeume", "stadtbaeume"), ("kuehlorte", "kuehlorte"),
                                                ("umweltzone", "umweltzone")])
def test_fehlende_daten(kennung, datensatz, kopie_testdaten, katalog):
    (laden.ordner(datensatz) / laden.ABRUF_DATEI).unlink()
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, kennung, melde=lambda m: None, speichern=False)
