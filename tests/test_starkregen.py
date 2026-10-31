import pandas as pd
import pytest

from essen import analysen, laden
from essen.analysen import starkregen as s
from essen.geo import DatenFehlen


def test_zuordnung_im_katalog_ist_belegt():
    zuordnung = s._zuordnung()
    assert zuordnung["geprueft"] is True and zuordnung["quelle"] and zuordnung["vermerk"]
    assert zuordnung["feld"] == "gridcode" and zuordnung["klassen"][3]["text"] == ">= 0,25"


def _vergleiche(ergebnis, datei, spalten=("tief_ha",)):
    erwartet = pd.read_csv(datei)
    vergleich = ergebnis.tabelle.merge(erwartet, on="stadtteil", suffixes=("", "_erwartet"))
    assert len(vergleich) == len(erwartet)
    for spalte in spalten:
        assert (vergleich[spalte] - vergleich[f"{spalte}_erwartet"]).abs().max() < 0.06, spalte
    mit_wert = vergleich.dropna(subset=["anteil_ueber_25cm_pct"])
    for spalte in ("anteil_ueber_25cm_pct", "anteil_ueber_5cm_pct"):
        assert (mit_wert[spalte] - mit_wert[f"{spalte}_erwartet"]).abs().max() < 0.06, spalte


def test_bekannte_loesung(mit_testdaten, katalog):
    """Standard (E-017): Gewässer der Landbedeckung abgezogen, Anteil an der Landfläche."""
    ergebnis = analysen.ausfuehren(katalog, "starkregen", melde=lambda m: None)
    _vergleiche(ergebnis, mit_testdaten["ordner"] / "erwartet_starkregen.csv", ("tief_ha", "land_ha"))
    assert "landbedeckung-nrw" in ergebnis.quellen and "Landfläche" in ergebnis.kennzahl_text
    assert (ergebnis.tabelle["gewaesser_ha"] >= 0).all() and ergebnis.tabelle["tief_gewaesser_ha"].sum() > 0
    assert any("abgezogen" in h for h in ergebnis.hinweise)
    assert 0 < ergebnis.kennzahl_stadt < 100
    assert any("nicht modelliert" in h for h in ergebnis.hinweise)  # Lücken wie im Original
    assert any("ohne Wirkung der Kanalisation" in h for h in ergebnis.hinweise)


def _aendere(feld, wert):
    import geopandas as gpd

    pfad = s.vektordatei(s.DATENSATZ)
    flaechen = gpd.read_file(pfad)
    flaechen.loc[flaechen.index[0], feld] = wert
    flaechen.to_file(pfad)


def test_unbekannter_code_bricht_ab(kopie_testdaten, katalog):
    _aendere("gridcode", 7)
    with pytest.raises(s.ZuordnungFehlt, match="ohne Beschreibung vor: 7"):
        analysen.ausfuehren(katalog, "starkregen", melde=lambda m: None)


def test_code_und_text_muessen_passen(kopie_testdaten, katalog):
    _aendere("Einstautie", ">= 0,50")
    with pytest.raises(s.ZuordnungFehlt, match="passen nicht"):
        analysen.ausfuehren(katalog, "starkregen", melde=lambda m: None)


def test_mindestbezug(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "starkregen", {"min_flaeche_ha": "100000"}, melde=lambda m: None)
    assert ergebnis.tabelle["anteil_ueber_25cm_pct"].isna().all() and ergebnis.kennzahl_stadt is None


def test_fehlende_daten(kopie_testdaten, katalog):
    laden.entferne(s.DATENSATZ)
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "starkregen", melde=lambda m: None)


def test_gewaesser_mitzaehlen(mit_testdaten, katalog):
    """Einstellung wie vor E-017: Gewässer zählen mit, Bezug ist die ganze Fläche."""
    ergebnis = analysen.ausfuehren(katalog, "starkregen", {"gewaesser": "mitzaehlen"}, melde=lambda m: None,
                                   speichern=False)
    _vergleiche(ergebnis, mit_testdaten["ordner"] / "erwartet_starkregen_mit_gewaesser.csv")
    assert "land_ha" not in ergebnis.tabelle.columns and "landbedeckung-nrw" not in ergebnis.quellen


def test_ohne_landbedeckung_wie_bisher(kopie_testdaten, katalog):
    laden.entferne("landbedeckung-nrw")
    ergebnis = analysen.ausfuehren(katalog, "starkregen", melde=lambda m: None, speichern=False)
    _vergleiche(ergebnis, kopie_testdaten / "erwartet_starkregen_mit_gewaesser.csv")
    assert any("Landbedeckung NRW laden" in h for h in ergebnis.hinweise)
