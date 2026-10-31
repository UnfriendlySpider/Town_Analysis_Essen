import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, box

from essen import kennzahlen

CRS = "EPSG:25832"


@pytest.fixture
def gebiete():
    return gpd.GeoDataFrame({"gebiet_id": ["a", "b"]},
                            geometry=[box(0, 0, 1000, 1000), box(1000, 0, 2000, 1000)], crs=CRS)


def test_flaechen_nach_klasse_vektor(gebiete):
    flaechen = gpd.GeoDataFrame({"klasse": [1, 2, 2]},
                                geometry=[box(0, 0, 500, 1000), box(500, 0, 1500, 1000), box(1500, 0, 1600, 100)], crs=CRS)
    tabelle = kennzahlen.flaechen_nach_klasse(gebiete, flaechen, [1, 2, 3])
    assert tabelle.loc["a", 1] == pytest.approx(500_000)
    assert tabelle.loc["a", 2] == pytest.approx(500_000)
    assert tabelle.loc["b", 2] == pytest.approx(500_000 + 10_000)
    assert tabelle.loc["b", 3] == 0


def test_flaechen_nach_klasse_raster(gebiete):
    # 20 x 10 Zellen à 100 m: linke Hälfte Klasse 1, rechte Klasse 2, eine Zelle ohne Klasse
    werte = np.ones((10, 20), dtype=np.int16)
    werte[:, 10:] = 2
    werte[0, 0] = 0
    tabelle = kennzahlen.flaechen_nach_klasse_raster(gebiete, werte, from_origin(0, 1000, 100, 100), CRS, [1, 2])
    assert tabelle.loc["a", 1] == pytest.approx(99 * 10_000)
    assert tabelle.loc["b", 2] == pytest.approx(100 * 10_000)
    assert tabelle.loc["a", 2] == 0


def test_anteile_und_mindestbezug():
    flaechen = pd.DataFrame({1: [30.0, 0.0], 2: [70.0, 0.0]}, index=["a", "b"])
    anteile = kennzahlen.anteile(flaechen)
    assert anteile.loc["a", 2] == pytest.approx(70)
    assert anteile.loc["b"].isna().all()
    tabelle = pd.DataFrame({"bezug": [10.0, 2.0], "wert": [50.0, 60.0]})
    ergebnis = kennzahlen.mindestbezug(tabelle, "bezug", 5, ["wert"], "zu klein")
    assert ergebnis["wert"].isna().tolist() == [False, True]
    assert ergebnis["hinweis"].tolist() == ["", "zu klein"]


def test_punkte_flaechenanteil_und_laenge(gebiete):
    punkte = gpd.GeoDataFrame(geometry=[Point(100, 100), Point(200, 200), Point(1500, 500)], crs=CRS)
    assert kennzahlen.punkte_je_gebiet(gebiete, punkte).tolist() == [2, 1]
    flaechen = gpd.GeoDataFrame(geometry=[box(0, 0, 500, 1000), box(250, 0, 750, 1000)], crs=CRS)
    anteil = kennzahlen.flaechenanteil_je_gebiet(gebiete, flaechen)
    assert anteil.loc["a", "anteil_pct"] == pytest.approx(75)
    linien = gpd.GeoDataFrame(geometry=[LineString([(0, 500), (2000, 500)])], crs=CRS)
    assert kennzahlen.laenge_je_gebiet(gebiete, linien).tolist() == pytest.approx([1000, 1000])


def test_gewichtetes_mittel():
    assert kennzahlen.gewichtetes_mittel(pd.Series([10.0, 30.0, None]), pd.Series([1.0, 3.0, 5.0])) == pytest.approx(25)
    assert kennzahlen.gewichtetes_mittel(pd.Series([None]), pd.Series([1.0])) is None


def test_flaechen_nach_klasse_innen_und_ueber_der_grenze():
    """Flächen ganz in einem Gebiet zählen direkt, Flächen über der Grenze werden geteilt."""
    import geopandas as gpd
    from shapely.geometry import box

    from essen import kennzahlen

    gebiete = gpd.GeoDataFrame({"gebiet_id": ["a", "b"]}, geometry=[box(0, 0, 100, 100), box(100, 0, 200, 100)],
                               crs="EPSG:25832")
    flaechen = gpd.GeoDataFrame({"klasse": [1, 1, 2]},
                                geometry=[box(10, 10, 20, 20), box(90, 0, 110, 10), box(150, 50, 300, 60)],
                                crs="EPSG:25832")
    tabelle = kennzahlen.flaechen_nach_klasse(gebiete, flaechen, [1, 2, 3])
    assert tabelle.loc["a", 1] == 100 + 100 and tabelle.loc["b", 1] == 100
    assert tabelle.loc["b", 2] == 500 and tabelle.loc["a", 2] == 0 and (tabelle[3] == 0).all()
