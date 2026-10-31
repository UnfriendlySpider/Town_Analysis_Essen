import geopandas as gpd
import numpy as np
import pytest
import shapely
from rasterio.transform import from_origin

from essen import analysen, einwohner, laden
from essen.geo import lade_stadtteile


@pytest.fixture
def gebiete(mit_testdaten, katalog):
    return lade_stadtteile(katalog).gdf


def test_zellen_wie_im_original(gebiete):
    z = einwohner.zellen()
    assert z.crs.to_epsg() == 3035 and len(z) > 100
    assert np.allclose(z.area, 100 * 100)
    assert z["gitter_id"].str.startswith("CRS3035RES100mN").all()
    je_gebiet = einwohner.zellen_je_gebiet(gebiete)
    assert je_gebiet["gitter_id"].is_unique and set(je_gebiet["gebiet_id"]) <= set(gebiete["gebiet_id"])


def test_ganze_und_keine_flaeche(gebiete):
    alles = shapely.box(*gebiete.to_crs("EPSG:25832").total_bounds).buffer(1000)
    voll = einwohner.in_flaeche(gebiete, alles)
    assert (voll["einwohner"] == voll["einwohner_belastet"]).all()
    assert voll["einwohner"].sum() == einwohner.zellen_je_gebiet(gebiete)["einwohner"].sum()
    leer = einwohner.in_flaeche(gebiete, None)
    assert (leer["einwohner_belastet"] == 0).all()


def test_halbe_flaeche_unabhaengig_nachgerechnet(gebiete):
    """Westhälfte belastet: erwartet je Zelle Einwohner × Anteil der Zellfläche westlich der Linie."""
    x1, y1, x2, y2 = gebiete.to_crs("EPSG:25832").total_bounds
    westen = shapely.box(x1 - 1000, y1 - 1000, (x1 + x2) / 2, y2 + 1000)
    ergebnis = einwohner.in_flaeche(gebiete, westen)
    z = einwohner.zellen_je_gebiet(gebiete)
    erwartet = sum(e * g.intersection(westen).area / g.area for e, g in zip(z["einwohner"], z.geometry, strict=True))
    assert abs(ergebnis["einwohner_belastet"].sum() - erwartet) <= len(ergebnis)  # Rundung je Gebiet
    als_tabelle = einwohner.in_flaeche(gebiete, gpd.GeoDataFrame(geometry=[westen], crs="EPSG:25832"))
    assert (als_tabelle["einwohner_belastet"] - ergebnis["einwohner_belastet"]).abs().max() <= 1
    anteile = ergebnis["anteil_einwohner_pct"].dropna()
    assert ((anteile >= 0) & (anteile <= 100)).all()


def test_rastermaske_wie_flaeche(gebiete):
    """Ein 25-m-Raster, dessen Westhälfte belastet ist, ergibt fast dasselbe wie die Fläche."""
    x1, y1, x2, y2 = gebiete.to_crs("EPSG:25832").total_bounds
    x1, y1, x2, y2 = x1 - 500, y1 - 500, x2 + 500, y2 + 500
    breite, hoehe = int((x2 - x1) // 25), int((y2 - y1) // 25)
    transform = from_origin(x1, y1 + hoehe * 25, 25, 25)
    maske = np.zeros((hoehe, breite), dtype=bool)
    maske[:, : breite // 2] = True
    raster = einwohner.in_rastermaske(gebiete, maske, transform, "EPSG:25832")
    flaeche = einwohner.in_flaeche(gebiete, shapely.box(x1, y1, x1 + breite // 2 * 25, y2 + 100))
    gesamt = raster["einwohner"].sum()
    assert abs(raster["einwohner_belastet"].sum() - flaeche["einwohner_belastet"].sum()) < 0.02 * gesamt


def test_mindestzahl(gebiete, monkeypatch):
    monkeypatch.setattr(einwohner, "MIN_EINWOHNER", 10**9)
    ergebnis = einwohner.in_flaeche(gebiete, None)
    assert ergebnis["anteil_einwohner_pct"].isna().all()


@pytest.mark.parametrize("analyse_id", ["hitze-nacht", "laerm", "starkregen"])
def test_analysen_ergaenzen_einwohner(mit_testdaten, katalog, analyse_id):
    ergebnis = analysen.ausfuehren(katalog, analyse_id, melde=lambda m: None, speichern=False)
    t = ergebnis.tabelle
    assert {"einwohner", "einwohner_belastet", "anteil_einwohner_pct"} <= set(t.columns)
    assert (t["einwohner_belastet"] <= t["einwohner"]).all()
    assert any(h.startswith("Geschätzt") and "Zensus 2022" in h for h in ergebnis.hinweise)


def test_ohne_zensus_keine_einwohner(kopie_testdaten, katalog):
    laden.entferne(einwohner.DATENSATZ)
    ergebnis = analysen.ausfuehren(katalog, "laerm", melde=lambda m: None, speichern=False)
    assert "einwohner" not in ergebnis.tabelle.columns
