import pandas as pd
import pytest

from essen import analysen, laden
from essen.analysen import betroffenheit as b
from essen.geo import DatenFehlen


def test_zuordnung_im_katalog_ist_belegt():
    zuordnung = b._zuordnung()
    assert zuordnung["geprueft"] is True and zuordnung["quelle"] and zuordnung["vermerk"]
    assert zuordnung["klassen"][2]["text"] == "sensitiv" and zuordnung["ab_klasse"] == 2


def test_bekannte_loesung(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "betroffenheit", melde=lambda m: None)
    erwartet = pd.read_csv(mit_testdaten["ordner"] / "erwartet_betroffenheit.csv")
    vergleich = ergebnis.tabelle.merge(erwartet, on="stadtteil", suffixes=("", "_erwartet"))
    assert len(vergleich) == len(erwartet)
    assert (vergleich["baubloecke_ha"] - vergleich["baubloecke_ha_erwartet"]).abs().max() < 0.06
    mit_wert = vergleich.dropna(subset=["anteil_betroffen_pct"])
    for spalte in ("anteil_betroffen_pct", "anteil_sensitiv_pct"):
        assert (mit_wert[spalte] - mit_wert[f"{spalte}_erwartet"]).abs().max() < 0.06
    assert 0 < ergebnis.kennzahl_stadt < 100
    assert any("Vergleich innerhalb Essens" in h for h in ergebnis.hinweise)


def test_text_und_code_muessen_passen(kopie_testdaten, katalog):
    import geopandas as gpd

    pfad = b.vektordatei(b.DATENSATZ)
    layer = "PL_KY_BTA_Gesamtbetrachtung_komplett"
    flaechen = gpd.read_file(pfad, layer=layer)
    erste = flaechen.index[flaechen["gemeind"] == "Essen"][0]
    flaechen.loc[erste, "Betroffenheit"] = "sehr sensitiv"
    flaechen.to_file(pfad, layer=layer, driver="GPKG")
    with pytest.raises(b.ZuordnungFehlt, match="passen nicht"):
        analysen.ausfuehren(katalog, "betroffenheit", melde=lambda m: None)


def test_mindestbezug(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "betroffenheit", {"min_flaeche_ha": "100000"}, melde=lambda m: None)
    assert ergebnis.tabelle["anteil_betroffen_pct"].isna().all() and ergebnis.kennzahl_stadt is None


def test_fehlende_daten(kopie_testdaten, katalog):
    laden.entferne(b.DATENSATZ)
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "betroffenheit", melde=lambda m: None)
