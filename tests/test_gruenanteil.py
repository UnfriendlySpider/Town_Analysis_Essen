import pandas as pd
import pytest

from essen import analysen, laden
from essen.analysen import gruenanteil as g
from essen.geo import DatenFehlen


def test_zuordnung_im_katalog_ist_belegt():
    zuordnung = g._zuordnung()
    assert zuordnung["geprueft"] is True and zuordnung["quelle"] and zuordnung["vermerk"]
    holzig = zuordnung["gruppen"]["lb_holzigevegetation"]
    assert holzig["feld"] == "vegetationsmerkmal" and holzig["werte"]["4000"] == "baeume"
    assert set(zuordnung["gruen"]) == {"gras", "kraut_sonstige", "baeume", "gehoelz"}


def test_bekannte_loesung(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "gruenanteil", melde=lambda m: None)
    erwartet = pd.read_csv(mit_testdaten["ordner"] / "erwartet_gruenanteil.csv")
    vergleich = ergebnis.tabelle.merge(erwartet, on="stadtteil", suffixes=("", "_erwartet"))
    assert len(vergleich) == len(erwartet)
    assert (vergleich["bedeckt_ha"] - vergleich["bedeckt_ha_erwartet"]).abs().max() < 0.06
    mit_wert = vergleich.dropna(subset=["anteil_gruen_pct"])
    for spalte in ("anteil_gruen_pct", "anteil_baeume_pct"):
        assert (mit_wert[spalte] - mit_wert[f"{spalte}_erwartet"]).abs().max() < 0.06
    assert 0 < ergebnis.kennzahl_stadt < 100
    assert any("Copernicus" in h for h in ergebnis.hinweise)


def test_unbekannter_code_bricht_ab(kopie_testdaten, katalog):
    """Ein Code, der nicht in der Zuordnung steht, wird nicht stillschweigend übergangen (E-009)."""
    import geopandas as gpd

    pfad = g.vektordatei(g.DATENSATZ)
    flaechen = gpd.read_file(pfad, layer="lb_krautigevegetation")
    flaechen.loc[flaechen.index[0], "vegetationsmerkmal"] = "9999"
    flaechen.to_file(pfad, layer="lb_krautigevegetation", driver="GPKG")
    with pytest.raises(g.ZuordnungFehlt, match="9999"):
        analysen.ausfuehren(katalog, "gruenanteil", melde=lambda m: None)


def test_mindestbezug(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "gruenanteil", {"min_flaeche_ha": "100000"}, melde=lambda m: None)
    assert ergebnis.tabelle["anteil_gruen_pct"].isna().all() and ergebnis.kennzahl_stadt is None


def test_fehlende_daten(kopie_testdaten, katalog):
    laden.entferne(g.DATENSATZ)
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "gruenanteil", melde=lambda m: None)
