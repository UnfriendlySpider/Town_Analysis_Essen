"""Heiße Tage je Stadtteil aus DWD-Jahresrastern: Gitter lesen, Flächengewichte, Ergebnis, Zeitreihen."""

import gzip
import io
import zipfile

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from essen import analysen, einordnung, zeitreihen
from essen.analysen import hitzetage_raster as hr
from essen.analysen.basis import Ergebnis
from essen.geo import DatenFehlen

KOPF = "NCOLS 3\nNROWS 2\nXLLCORNER 1000\nYLLCORNER 2000\nCELLSIZE 1000\nNODATA_VALUE -999\n"
WERTE = "   1    2    3\n   4 -999    6\n"  # obere Zeile zuerst (Norden)


def _gitter(tmp_path, name="g_2020_17.asc.gz", kopf=KOPF, werte=WERTE, als_zip=False):
    pfad = tmp_path / name
    if als_zip:
        with zipfile.ZipFile(pfad, "w") as zf:
            zf.writestr("innen.asc", kopf + werte)
    else:
        pfad.write_bytes(gzip.compress((kopf + werte).encode("ascii")))
    return pfad


def test_kopf_mit_ecke_und_mitte():
    ecke = hr.lies_kopf(io.StringIO(KOPF))
    assert (ecke.spalten, ecke.zeilen, ecke.x_links, ecke.y_unten, ecke.y_oben) == (3, 2, 1000, 2000, 4000)
    mitte = hr.lies_kopf(io.StringIO(KOPF.replace("XLLCORNER 1000", "XLLCENTER 1500").replace("YLLCORNER", "YLLCENTER")))
    assert mitte.x_links == 1000 and mitte.y_unten == 1500


@pytest.mark.parametrize("als_zip", [False, True])
def test_ausschnitt_liest_gzip_und_getarntes_zip(tmp_path, als_zip):
    pfad = _gitter(tmp_path, als_zip=als_zip)
    werte, _kopf, z0, s0 = hr.lies_ausschnitt(pfad, (2100, 2100, 3900, 3900))  # mittlere und rechte Spalte
    assert (z0, s0) == (0, 1)
    assert werte.shape == (2, 2)
    assert werte[0].tolist() == [2, 3] and np.isnan(werte[1, 0]) and werte[1, 1] == 6


def test_ausschnitt_ausserhalb_meldet_fehler(tmp_path):
    with pytest.raises(ValueError, match="deckt das Stadtgebiet nicht ab"):
        hr.lies_ausschnitt(_gitter(tmp_path), (90000, 90000, 91000, 91000))


def test_jahr_aus_dateinamen():
    assert hr.jahr_aus_name("grids_germany_annual_hot_days_2025_17.asc.gz") == 2025
    assert hr.jahr_aus_name("grids_germany_annual_air_temp_mean_188117.asc.gz") == 1881
    assert hr.jahr_aus_name("BESCHREIBUNG.pdf") is None


def test_flaechengewichtetes_mittel_und_fehlwerte(tmp_path):
    werte, kopf, z0, s0 = hr.lies_ausschnitt(_gitter(tmp_path), (1000, 2000, 4000, 4000))
    # Gebiet A: halbe Zelle oben links (1) und ganze Zelle oben Mitte (2) → (0,5·1 + 1·2) / 1,5
    # Gebiet B: ganz in der Fehlwertzelle → kein Wert; Gebiet C: halb Fehlwert, halb 6 → 6
    gebiete = gpd.GeoDataFrame(geometry=[box(1500, 3000, 3000, 4000), box(2000, 2000, 3000, 3000),
                                         box(2500, 2000, 3500, 3000)], crs=hr.RASTER_CRS)
    matrix = hr.gewichte(gebiete, kopf, z0, s0, werte.shape)
    mittel = hr.gebietsmittel(werte, matrix)
    assert mittel[0] == pytest.approx(2.5 / 1.5)
    assert np.isnan(mittel[1])
    assert mittel[2] == pytest.approx(6.0)


def test_rechnen_mit_testdaten(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "hitzetage-raster", melde=lambda m: None, speichern=False)
    t = ergebnis.tabelle
    assert {"gebiet_id", "stadtteil", "stadtteil_nr", "heisse_tage_bezug", "heisse_tage_zuletzt",
            "heisse_tage_aenderung", "sommertage_zuletzt", "jahresmittel_zuletzt_c"} <= set(t.columns)
    assert t["heisse_tage_zuletzt"].notna().all()
    assert (t["heisse_tage_aenderung"] > 0).all()  # die Testdaten werden über die Jahre wärmer
    j = ergebnis.jahreswerte
    assert set(j["gebiet_id"]) == set(t["gebiet_id"]) | {hr.ESSEN_ID}
    assert j["jahr"].min() == 1951
    # Jahresmittel in 1/10 °C gespeichert, als °C ausgegeben; die ZIP-Datei von 1951 wurde gelesen
    essen = j[j["gebiet_id"] == hr.ESSEN_ID].set_index("jahr")
    # Die erfundenen Werte schwanken je Jahr stark (und je nach Datum des Testlaufs); geprüft wird die Einheit:
    # Zehntelgrad ungeteilt wären rund 90.
    assert -10 < essen.loc[1951, "jahresmittel_c"] < 30
    assert 5 < essen["jahresmittel_c"].mean() < 20
    assert ergebnis.kennzahl_stadt == pytest.approx(essen["heisse_tage"].tail(10).mean())


def test_ohne_heisse_tage_fehlen_daten(leerer_datenordner, katalog):
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "hitzetage-raster", melde=lambda m: None, speichern=False)


def test_jahreswerte_werden_gespeichert_und_geladen(kopie_testdaten, katalog):
    analysen.ausfuehren(katalog, "hitzetage-raster", melde=lambda m: None)
    geladen = Ergebnis.laden("hitzetage-raster")
    assert geladen.jahreswerte is not None
    assert "1" in set(geladen.jahreswerte["gebiet_id"])  # Kennungen bleiben Text wie in der Tabelle
    assert Ergebnis.laden("hitzetage-station") is None or Ergebnis.laden("hitzetage-station").jahreswerte is None


def test_zeitreihe_je_stadtteil(kopie_testdaten, katalog):
    analysen.ausfuehren(katalog, "hitzetage-raster", melde=lambda m: None)
    analysen.ausfuehren(katalog, "hitzetage-station", melde=lambda m: None)
    gebiete = zeitreihen.stadtteile()
    erstes, essen = next(g for g in gebiete if g != hr.ESSEN_ID), hr.ESSEN_ID
    assert next(iter(gebiete)) == essen
    reihe = zeitreihen.stadtteil_reihe("heisse_tage", [erstes, essen], station=True)
    assert list(dict.fromkeys(reihe.daten["reihe"])) == [gebiete[erstes], "Essen gesamt", zeitreihen.STATION_NAME]
    assert reihe.einheit == "Tage" and 1965 in reihe.marken
    assert zeitreihen.stadtteil_reihe("jahresmittel_c", [essen]).einheit == "°C"
    vergleich, letzte = zeitreihen.frueher_heute(reihe.daten)
    assert letzte is not None and (vergleich["differenz"] > 0).all()
    assert not zeitreihen.trend(reihe.daten).empty


def test_satz_frueher_und_heute():
    satz = einordnung.frueher_heute_satz("Rüttenscheid", "heiße Tage", 4.0, 10.0, 1961, 1990, 2025)
    assert satz.startswith("2016–2025 gab es in Rüttenscheid im Schnitt 10,0 heiße Tage")
    assert "zweieinhalbmal" in satz
    assert "Grad wärmer" in einordnung.frueher_heute_satz("Essen gesamt", "°C", 9.5, 11.5, 1961, 1990, 2025)


def test_ansehen_ohne_kopie_laden_mit_kopie(kopie_testdaten, katalog):
    from essen.analysen import ausfuehren
    from essen.analysen.basis import Ergebnis

    ausfuehren(katalog, "hitzetage-raster", melde=lambda t: None)
    assert Ergebnis.ansehen("hitzetage-raster") is Ergebnis.ansehen("hitzetage-raster")
    kopie = Ergebnis.laden("hitzetage-raster")
    kopie.tabelle["nur_in_der_kopie"] = 1
    assert "nur_in_der_kopie" not in Ergebnis.ansehen("hitzetage-raster").tabelle.columns
    assert Ergebnis.ansehen("gibt-es-nicht") is None
