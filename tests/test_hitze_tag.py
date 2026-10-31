import numpy as np
import pandas as pd
import pytest

from essen import analysen, laden
from essen.analysen import hitze_tag as t
from essen.geo import DatenFehlen


def test_klassen_nach_vdi_3787():
    werte = [10.0, 23.0, 23.01, 29.0, 35.0, 35.5, 41.0, 41.01, 47.0, np.nan]
    assert t.klasse_aus_pet(np.array(werte)).tolist() == [1, 1, 2, 2, 3, 4, 4, 5, 5, 0]


def test_zuordnung_im_katalog_ist_belegt():
    zuordnung = t.lade_zuordnung(t.RASTER_ID)
    assert zuordnung["geprueft"] is True and zuordnung["lesart"] == "temperatur"
    assert zuordnung["dateien"] == {"extrem": "PL_KY_TAG_EXT.tif", "typisch": "PL_KY_TAG_TYP.tif"}


def _vergleiche(ergebnis, erwartet, spalte):
    vergleich = ergebnis.tabelle.merge(erwartet, on="stadtteil", suffixes=("", "_erwartet"))
    assert len(vergleich) == len(erwartet)
    assert (vergleich["bewertet_ha"] - vergleich["bewertet_ha_erwartet"]).abs().max() < 0.06
    mit_wert = vergleich.dropna(subset=["anteil_ueber_41c_pct"])
    assert len(mit_wert)
    assert (mit_wert["anteil_ueber_41c_pct"] - mit_wert[spalte]).abs().max() < 0.06
    return mit_wert


def test_bekannte_loesung_extrem(mit_testdaten, katalog):
    meldungen = []
    ergebnis = analysen.ausfuehren(katalog, "hitze-tag", melde=meldungen.append)
    assert any("PL_KY_TAG_EXT.tif" in m for m in meldungen)
    erwartet = pd.read_csv(mit_testdaten["ordner"] / "erwartet_hitze_tag.csv")
    mit_wert = _vergleiche(ergebnis, erwartet, "anteil_ueber_41c_pct_erwartet")
    assert (mit_wert["pet_mittel_c"] - mit_wert["pet_mittel_c_erwartet"]).abs().max() < 0.06
    assert 0 < ergebnis.kennzahl_stadt < 100 and "extremer Sommertag" in ergebnis.kennzahl_text
    assert any("ganze Fläche" in h for h in ergebnis.hinweise)


def test_szenario_typisch(mit_testdaten, katalog):
    typisch = analysen.ausfuehren(katalog, "hitze-tag", {"szenario": "typisch"}, melde=lambda m: None)
    erwartet = pd.read_csv(mit_testdaten["ordner"] / "erwartet_hitze_tag.csv")
    _vergleiche(typisch, erwartet, "anteil_ueber_41c_pct_typisch")
    extrem = analysen.ausfuehren(katalog, "hitze-tag", melde=lambda m: None)
    assert typisch.kennzahl_stadt < extrem.kennzahl_stadt


def test_mindestbezug(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "hitze-tag", {"min_flaeche_ha": "100000"}, melde=lambda m: None)
    assert ergebnis.tabelle["anteil_ueber_41c_pct"].isna().all() and ergebnis.kennzahl_stadt is None


def test_fehlende_daten(kopie_testdaten, katalog):
    laden.entferne(t.RASTER_ID)
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "hitze-tag", melde=lambda m: None)


def test_ohne_dateiangabe_kein_raten(kopie_testdaten, katalog, monkeypatch):
    monkeypatch.setattr(t, "lade_zuordnung", lambda kennung: None)
    with pytest.raises(t.ZuordnungFehlt, match="dateien"):
        analysen.ausfuehren(katalog, "hitze-tag", melde=lambda m: None)
