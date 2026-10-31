"""Originaldaten ansehen: Dateiliste ohne Entpacken, Proben aus Vektor, Raster, CSV und JSON (erfundene Testdaten)."""

import numpy as np
import pytest

from essen import laden, legenden, vorschau
from essen.geo import essen_bbox


def _dateien(katalog, kennung):
    return vorschau.dateiliste(katalog.datensatz(kennung))


def test_dateiliste_schaut_in_zips_ohne_zu_entpacken(kopie_testdaten, katalog):
    ordner = laden.ordner("klimaanalyse-nacht-vektor")
    for alt in ordner.glob("entpackt_*"):
        import shutil

        shutil.rmtree(alt)
    dateien = _dateien(katalog, "klimaanalyse-nacht-vektor")
    assert not list(ordner.glob("entpackt_*"))  # nichts entpackt
    im_zip = [d for d in dateien if d.im_archiv]
    assert im_zip and all(d.pfad.startswith("/vsizip/") for d in im_zip)
    gpkg = next(d for d in im_zip if d.name.endswith(".gpkg"))
    assert gpkg.art == "vektor" and gpkg.bytes > 0
    assert any(name == "PL_KY_Verkehr" for name, _ in vorschau.layer(gpkg.pfad))
    tabelle = vorschau.tabelle_dateien(dateien)
    assert list(tabelle.columns) == ["datei", "art", "bytes", "im_archiv"]


def test_vektor_probe_im_stadtgebiet_mit_feldern(mit_testdaten, katalog):
    datei = next(d for d in _dateien(katalog, "stadtteile") if d.art == "vektor")
    probe = vorschau.vektor_probe(datei.pfad)
    assert len(probe.daten) == probe.gesamt == 12 and not probe.begrenzt
    assert probe.geometrie and probe.nur_essen and probe.daten.crs is not None
    assert "Feld" in probe.felder.columns and len(probe.felder) == len(probe.daten.columns) - 1
    klein = vorschau.vektor_probe(datei.pfad, anzahl=5)
    assert len(klein.daten) == 5 and klein.begrenzt


def test_raster_vorschau_begrenzt_und_ohne_farben_neutral(mit_testdaten, katalog):
    datei = next(d for d in _dateien(katalog, "klimaanalyse-nacht-raster")
                 if d.art == "raster" and d.name.endswith("LT_EXT.tif"))
    bild = vorschau.raster_vorschau(datei.pfad, max_pixel=10_000)
    hoehe, breite, kanaele = bild.bild.shape
    assert kanaele == 4 and hoehe * breite <= 11_000 and bild.bild.dtype == np.uint8
    assert bild.art == "skala" and bild.stetig and "Beschreibung des Anbieters" in bild.hinweis
    assert (bild.bild[..., 3] == 0).any()  # Fehlwerte (-999) und Flächen außerhalb sind durchsichtig
    assert {"von", "bis", "zellen"} <= set(bild.werte.columns) and bild.werte["zellen"].sum() > 0
    west, sued, ost, nord = bild.grenzen
    assert west < 7.0 < ost and sued < 51.45 < nord


def test_raster_mit_farbtabelle(kopie_testdaten, katalog):
    from essen import testdaten

    testdaten.klassenraster_mit_legende()
    datei = next(d for d in _dateien(katalog, "klimaanalyse-nacht-raster") if d.art == "raster")
    bild = vorschau.raster_vorschau(datei.pfad)
    assert bild.art == "farbtabelle" and not bild.stetig and bild.legende
    assert set(bild.werte["wert"]) <= set(range(1, 16))


def _klassenraster(pfad, werte):
    import rasterio
    from rasterio.transform import from_origin

    x1, _, _, y2 = essen_bbox()
    with rasterio.open(pfad, "w", driver="GTiff", width=werte.shape[1], height=werte.shape[0], count=1,
                       dtype="uint8", crs="EPSG:25832", nodata=0,
                       transform=from_origin(x1 + 3000, y2 - 3000, 100, 100)) as ziel:
        ziel.write(werte.astype("uint8"), 1)


def test_raster_legende_nur_wenn_sie_die_werte_abdeckt(tmp_path):
    werte = np.ones((40, 40), dtype="uint8")
    werte[:, 20:] = 2
    pfad = tmp_path / "klassen.tif"
    _klassenraster(pfad, werte)
    passend = [legenden.Eintrag("1", "wenig", "#aaccee", "x.qml"), legenden.Eintrag("2", "viel", "#112233", "x.qml")]
    bild = vorschau.raster_vorschau(str(pfad), legende=passend)
    assert bild.art == "legende" and bild.legende == [("#aaccee", "wenig"), ("#112233", "viel")]
    sichtbar = bild.bild[bild.bild[..., 3] > 0][:, :3]
    assert {tuple(f) for f in sichtbar} == {(0xaa, 0xcc, 0xee), (0x11, 0x22, 0x33)}
    # Legende deckt nur die Hälfte der Zellen ab: nicht raten, neutrale Skala (E-009)
    halb = [legenden.Eintrag("1", "wenig", "#aaccee", "x.qml")]
    assert vorschau.raster_vorschau(str(pfad), legende=halb).art == "skala"


def test_tabelle_und_json(mit_testdaten, katalog):
    csv = next(d for d in _dateien(katalog, "zensus-2022-gitter") if d.name.endswith(".csv"))
    daten, trenner = vorschau.tabelle_probe(csv.pfad, anzahl=50)
    assert len(daten) <= 50 and len(daten.columns) >= 2 and trenner in ";,\t|"
    json_datei = next(d for d in _dateien(katalog, "uba-jahresbilanzen") if d.art == "json")
    inhalt = vorschau.json_vorschau(json_datei.pfad)
    assert inhalt.daten is not None and inhalt.bytes > 0
    assert vorschau.json_vorschau(json_datei.pfad, max_bytes=10).daten is None


@pytest.mark.parametrize("datensatz", ["klimaanalyse-nacht-raster", "uba-jahresbilanzen", "zensus-2022-gitter",
                                       "laermkarte-essen"])
def test_seite_originaldaten_zeigt_jede_art(datensatz, mit_testdaten):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    app = Path(__file__).resolve().parents[1] / "src" / "essen" / "app"
    at = AppTest.from_file(str(app / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/originaldaten.py")
    at.query_params["datensatz"] = datensatz
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
