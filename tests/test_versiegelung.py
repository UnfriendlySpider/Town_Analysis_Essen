import pandas as pd
import pytest

from essen import analysen, laden
from essen.analysen import versiegelung as v
from essen.geo import DatenFehlen


def test_bekannte_loesung(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "versiegelung", melde=lambda m: None)
    erwartet = pd.read_csv(mit_testdaten["ordner"] / "erwartet_versiegelung.csv")
    vergleich = ergebnis.tabelle.merge(erwartet, on="stadtteil", suffixes=("", "_erwartet"))
    assert len(vergleich) == len(erwartet)
    assert (vergleich["bewertet_ha"] - vergleich["bewertet_ha_erwartet"]).abs().max() < 0.06
    mit_wert = vergleich.dropna(subset=["anteil_versiegelt_pct"])
    assert (mit_wert["anteil_versiegelt_pct"] - mit_wert["anteil_versiegelt_pct_erwartet"]).abs().max() < 0.06
    assert 0 < ergebnis.kennzahl_stadt < 100


def test_streifen_aendern_nichts(mit_testdaten, katalog):
    """Das streifenweise Zählen liefert dasselbe wie ein Durchgang."""
    from essen import kennzahlen
    from essen.geo import lade_stadtteile

    gebiete = lade_stadtteile(katalog).gdf
    pfad = v._rasterdatei()
    klein = kennzahlen.flaechen_nach_wert_rasterdatei(gebiete, pfad, [0, 1], zeilen_je_streifen=7)
    gross = kennzahlen.flaechen_nach_wert_rasterdatei(gebiete, pfad, [0, 1], zeilen_je_streifen=100_000)
    pd.testing.assert_frame_equal(klein, gross)


def test_ohne_beleg_fuer_den_code_kein_raten(mit_testdaten, katalog, monkeypatch):
    ds = katalog.datensatz(v.DATENSATZ)
    monkeypatch.delitem(ds.felder, "versiegelt")
    with pytest.raises(v.ZuordnungFehlt, match=r"felder\.versiegelt"):
        analysen.ausfuehren(katalog, "versiegelung", melde=lambda m: None, speichern=False)


def test_mindestbezug(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "versiegelung", {"min_flaeche_ha": "100000"}, melde=lambda m: None)
    assert ergebnis.tabelle["anteil_versiegelt_pct"].isna().all() and ergebnis.kennzahl_stadt is None


def test_fehlende_daten(kopie_testdaten, katalog):
    laden.entferne(v.DATENSATZ)
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "versiegelung", melde=lambda m: None)


def _satellit(ordner_name: str = "VG_20m_2006_Essen.tif"):
    """Erfundene Satellitenraster wie im echten ZIP: 2006 in EPSG:3035 als float32 mit einem Block 254,
    2018 in EPSG:25832 als int8 mit Fehlwert −128. Überall 40 % bzw. 60 %."""
    import io
    import zipfile

    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds

    from essen import geo, pfade
    from essen.testdaten import _abruf

    def tif(werte, crs, dtype, nodata=None):
        x1, y1, x2, y2 = geo.essen_bbox(crs)
        puffer = io.BytesIO()
        with rasterio.MemoryFile() as speicher:
            with speicher.open(driver="GTiff", width=werte.shape[1], height=werte.shape[0], count=1, dtype=dtype,
                               crs=crs, transform=from_bounds(x1, y1, x2, y2, werte.shape[1], werte.shape[0]),
                               nodata=nodata) as ds:
                ds.write(werte.astype(dtype), 1)
            puffer.write(speicher.read())
        return puffer.getvalue()

    alt = np.full((400, 300), 40.0)
    alt[:20, :20] = 254  # kein Prozentwert, darf das Mittel nicht verschieben
    neu = np.full((800, 600), 60)
    neu[:5, :5] = -128
    import shutil

    ordner = pfade.roh(v.SATELLIT)
    shutil.rmtree(ordner, ignore_errors=True)  # auch schon Entpacktes aus den gemeinsamen Testdaten
    ordner.mkdir(parents=True)
    name = "bodenversiegelung-sat_Essen_05113000_2006-2018_EPSG25832_TIFF.zip"
    with zipfile.ZipFile(ordner / name, "w") as zf:
        zf.writestr(ordner_name, tif(alt, "EPSG:3035", "float32"))
        zf.writestr("VG_10m_2018_Essen.tif", tif(neu, "EPSG:25832", "int8", nodata=-128))
    _abruf(v.SATELLIT, [name], "dl-de-zero-2.0", "lanuk")


def test_verlauf_aus_satellitendaten(kopie_testdaten, katalog):
    _satellit()
    ergebnis = analysen.ausfuehren(katalog, "versiegelung", melde=lambda m: None, speichern=False)
    jahre = ergebnis.jahreswerte
    assert sorted(jahre["jahr"].unique()) == [2006, 2018]
    assert set(jahre[jahre["jahr"] == 2006]["zellgroesse_m"]) == {20}
    mit_wert = jahre.dropna(subset=["versiegelungsgrad_pct"])
    assert (mit_wert[mit_wert["jahr"] == 2006]["versiegelungsgrad_pct"] == 40.0).all()
    assert (mit_wert[mit_wert["jahr"] == 2018]["versiegelungsgrad_pct"] == 60.0).all()
    assert v.SATELLIT in ergebnis.quellen and any("feineren Auflösung" in h for h in ergebnis.hinweise)


def test_satellit_ohne_jahr_im_namen(kopie_testdaten, katalog):
    _satellit("Versiegelung_Essen.tif")
    with pytest.raises(v.ZuordnungFehlt, match="Jahr und Zellgröße"):
        analysen.ausfuehren(katalog, "versiegelung", melde=lambda m: None, speichern=False)
