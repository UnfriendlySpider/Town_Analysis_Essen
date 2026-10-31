"""Fälle aus dem Review: Schutz vor Datenverlust, stilles Raten, Einschleusen und Abstürze."""

import json
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from essen import analysen, bericht, cli, geo, laden, pfade, testdaten
from essen.analysen import hitze_nacht as h
from essen.analysen.basis import Ergebnis
from essen.inspizieren import inspiziere_pfad


def test_testdaten_loeschen_keine_fremden_ordner(tmp_path):
    fremd = tmp_path / "wichtig"
    fremd.mkdir()
    (fremd / "notizen.txt").write_text("bitte nicht löschen", encoding="utf-8")
    with pytest.raises(ValueError, match="kein Testdaten-Ordner"):
        testdaten.erzeuge(fremd, zellgroesse=200.0, anzahl_gebiete=6)
    assert (fremd / "notizen.txt").exists()


def test_ohne_raster_kein_stiller_wechsel_auf_das_geopackage(kopie_testdaten, katalog):
    laden.entferne("klimaanalyse-nacht-raster")
    with pytest.raises(geo.DatenFehlen) as fehler:
        analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    assert fehler.value.fehlend == ["klimaanalyse-nacht-raster"]


def test_zahlenfeld_wird_nicht_als_klasse_geraten(kopie_testdaten, katalog):
    """gridcode im echten GeoPackage ist ungeklärt und darf nicht automatisch als Klasse gelten."""
    with pytest.raises(h.ZuordnungFehlt, match="Klassennamen"):
        analysen.ausfuehren(katalog, "hitze-nacht", {"quelle": "vektor"}, melde=lambda t: None)
    with pytest.raises(h.ZuordnungFehlt, match="lesart"):
        analysen.ausfuehren(katalog, "hitze-nacht", {"quelle": "vektor", "feld": "gridcode"}, melde=lambda t: None)


def test_widerspruechliche_legende_fuehrt_zur_vorlage(kopie_testdaten, katalog, monkeypatch):
    """Eine Legende, die zu den Werten nicht passt, darf nicht durch „1 bis 8 = Klassen“ ersetzt werden."""
    import rasterio

    from essen import pfade, testdaten

    monkeypatch.setattr(h, "zuordnung_ordner", lambda: [pfade.zuordnungen()])  # ohne die Zuordnung im Katalog
    testdaten.klassenraster_mit_legende(mit_legende=False)

    ordner = laden.ordner("klimaanalyse-beschreibung")
    archiv = next(ordner.glob("*.zip"))
    qml = ('<qgis><pipe><rasterrenderer type="paletted"><colorPalette>'
           '<paletteEntry value="1" color="#ffffff" label="Kaltluftvolumenstromdichte gering"/>'
           '<paletteEntry value="2" color="#eeeeee" label="&gt; 14 - 15,5 °C niedrige nächtliche Lufttemperaturen"/>'
           '</colorPalette></rasterrenderer></pipe></qgis>')
    with zipfile.ZipFile(archiv, "w") as zf:
        zf.writestr("Legende_Nacht.qml", qml)
    for alt in ordner.glob("entpackt_*"):
        import shutil
        shutil.rmtree(alt)
    # Raster nur mit Werten 1 bis 8
    tif = next(p for p in laden.entpackt("klimaanalyse-nacht-raster") if p.suffix == ".tif")
    with rasterio.open(tif) as r:
        profil, werte = r.profile, r.read(1)
    werte = np.where(werte > 8, 1, werte).astype("uint8")
    with rasterio.open(tif, "w", **profil) as r:
        r.write(werte, 1)
    with pytest.raises(h.ZuordnungFehlt, match="Vorlage"):
        analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)


def test_index_json_mit_boesem_dateinamen(tmp_path):
    index = {"datasets": [{"name": "x", "files": [{"name": "../boese.zip"}, {"name": "/etc/passwd.zip"},
                                                   {"name": "gut_2026.zip", "size": "5"}]}]}
    namen = [d.name for d in laden._dateien_aus_index(index, "https://example.org/ordner/")]
    assert namen == ["gut_2026.zip"]
    with pytest.raises(laden.DownloadFehler):
        laden.sicherer_name("../boese.zip")


def test_exportseite_laesst_kein_script_einschleusen(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None, speichern=False)
    ergebnis.geometrie.loc[ergebnis.geometrie.index[0], "stadtteil"] = "</script><script>alert(1)</script>"
    seite = bericht.html_seite(katalog, analysen.ALLE["hitze-nacht"], ergebnis)
    assert "</script><script>alert(1)" not in seite
    assert seite.count("<script") == 2  # MapLibre und das eigene Skript


def test_unvollstaendiges_ergebnis_gilt_als_fehlend(kopie_testdaten, katalog):
    analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    (pfade.verarbeitet("hitze-nacht") / "tabelle.csv").unlink()
    with pytest.warns(UserWarning):
        assert Ergebnis.laden("hitze-nacht") is None


def test_json_ohne_geometrie_ist_keine_vektordatei(kopie_testdaten):
    ordner = laden.ordner("sensor-community-essen")
    ordner.mkdir(parents=True)
    (ordner / "sensoren_essen.json").write_text(json.dumps([{"id": 1}]), encoding="utf-8")
    laden.schreibe_abruf(laden.Abruf(datensatz="sensor-community-essen", dateien=["sensoren_essen.json"],
                                     url="test", zeit="2026-10-10T00:00:00", bytes=12, testdaten=True))
    assert not geo.hat_vektordaten("sensor-community-essen")
    assert geo.hat_vektordaten("klimaanalyse-nacht-vektor")  # gepackt, ohne zu entpacken


def test_nummernfeld_mit_buchstaben_stoert_nicht():
    gdf = gpd.GeoDataFrame({"NR": [str(i) for i in range(1, 20)] + ["20a"],
                            "NAME": [f"Gebiet {i}" for i in range(20)]},
                           geometry=[box(i, 0, i + 1, 1) for i in range(20)], crs="EPSG:25832")
    name, nummer, _ = geo.felder_erkennen(gdf)
    assert name == "NAME" and nummer is None


def test_zip_inspizieren(testdaten_ordner):
    archiv = next((testdaten_ordner["ordner"] / "raw" / "klimaanalyse-nacht-vektor").glob("*.zip"))
    text = inspiziere_pfad(archiv).als_markdown()
    assert "Layer PL_KY_KL_Produktion" in text and "nicht lesbar" not in text
    assert str(testdaten_ordner["ordner"]) not in text  # keine absoluten Pfade im Bericht


def test_kommandozeile_meldet_fehler_ohne_traceback(capsys, leerer_datenordner):
    for befehl in (["info", "gibt-es-nicht"], ["analyse", "hitze-nacht", "-p", "min_wirkraum_ha=abc"],
                   ["analyse", "hitze-nacht"], ["schnell", "klimaanalyse-nacht-vektor"]):
        with pytest.raises(SystemExit) as ende:
            cli.main(befehl)
        assert str(ende.value.code).startswith(("Fehler", "Diese Daten fehlen")), befehl


def test_mischgeometrien_in_der_schnellanalyse(kopie_testdaten, katalog):
    from shapely.geometry import LineString, Point

    from essen.analysen import schnell

    stadtteile = gpd.read_file(next(laden.ordner("stadtteile").glob("*.geojson"))).to_crs("EPSG:25832")
    x, y = stadtteile.union_all().representative_point().coords[0]
    gemischt = gpd.GeoDataFrame(geometry=[Point(x, y), Point(x + 10, y), LineString([(x, y), (x + 50, y)])],
                                crs="EPSG:25832")
    ordner = laden.ordner("osm-gruenflaechen")
    ordner.mkdir(parents=True)
    datei = ordner / "gemischt.geojson"
    datei.write_text(gemischt.to_crs("EPSG:4326").to_json(), encoding="utf-8")
    laden.schreibe_abruf(laden.Abruf(datensatz="osm-gruenflaechen", dateien=[datei.name], url="test",
                                     zeit="2026-10-10T00:00:00", bytes=datei.stat().st_size, testdaten=True))
    ergebnis = schnell.verteile(katalog, "osm-gruenflaechen", melde=lambda t: None)
    assert ergebnis.tabelle["anzahl"].sum() == 2
    assert any("übergangen" in hinweis for hinweis in ergebnis.hinweise)


def test_abdeckung_wird_geprueft():
    band = np.array([[1, 1, 2], [2, 9, 9]])
    maske = np.zeros_like(band, dtype=bool)
    hinweise = []
    with pytest.raises(h.ZuordnungFehlt, match="9"):
        h._pruefe_abdeckung(band, maske, {1: 6, 2: 7}, "Test", hinweise)
    h._pruefe_abdeckung(band, maske, {1: 6, 2: 7, 9: 0}, "Test", hinweise)
    assert hinweise == []


def test_temperatur_ausreisser_werden_fehlwerte():
    band = np.ma.MaskedArray(np.array([[21.0, -9999.0], [16.0, 60.0]]))
    hinweise = []
    klassen = h._klassen_aus_temperatur(band, hinweise)
    assert klassen.tolist() == [[6, 0], [3, 0]] and hinweise


def test_datenbedarf_haengt_vom_parameter_ab():
    analyse = analysen.ALLE["hitze-nacht"]
    assert "klimaanalyse-nacht-vektor" in analyse.benoetigt_bei({"quelle": "vektor"})
    assert "klimaanalyse-nacht-raster" in analyse.benoetigt_bei({"quelle": "auto"})
    assert isinstance(pd.Series(analyse.benoetigt_bei()), pd.Series)


def test_geojson_mit_spaetem_typ(tmp_path):
    text = '{"features": [{"geometry": {"type": "Point", "coordinates": [7.0, 51.4]}, "properties": {"x": "' + "a" * 12000 + '"}, "type": "Feature"}], "type": "FeatureCollection"}'
    (tmp_path / "spaet.geojson").write_text(text, encoding="utf-8")
    (tmp_path / "spaet.json").write_text(text, encoding="utf-8")
    assert geo.ist_geojson(tmp_path / "spaet.geojson") and geo.ist_geojson(tmp_path / "spaet.json")
    (tmp_path / "liste.json").write_text('[{"type": "Sensor"}]', encoding="utf-8")
    assert not geo.ist_geojson(tmp_path / "liste.json")


def test_kaputte_geometrie_datei_gilt_als_fehlend(kopie_testdaten, katalog):
    analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    (pfade.verarbeitet("hitze-nacht") / "gebiete.geojson").write_text('{"type": "Feat', encoding="utf-8")
    with pytest.warns(UserWarning):
        assert Ergebnis.laden("hitze-nacht") is None


def test_parameterfehler_nennt_den_namen(katalog):
    with pytest.raises(ValueError, match="min_wirkraum_ha"):
        analysen.ALLE["hitze-nacht"].parameter_mit_standard({"min_wirkraum_ha": "abc"})


def test_schnellanalyse_mit_unbekanntem_layer(mit_testdaten, katalog):
    from essen.analysen import schnell

    with pytest.raises(ValueError, match="Vorhanden"):
        schnell.verteile(katalog, "klimaanalyse-nacht-vektor", "GIBTSNICHT", melde=lambda t: None)


def test_lange_listen_offener_farben_bleiben_kurz():
    band = np.arange(1000).reshape(10, 100)
    hinweise = []
    with pytest.raises(h.ZuordnungFehlt) as fehler:
        h._pruefe_abdeckung(band, np.zeros_like(band, dtype=bool), {}, "Test", hinweise, als_farbe=True)
    assert len(str(fehler.value)) < 400 and "#" in str(fehler.value) and "weitere" in str(fehler.value)


def test_index_json_mit_komma_am_ende():
    """So liefert OpenGeodata.NRW den Ordner umgebungslaerm2022 aus (Komma vor der schließenden Klammer)."""
    text = '{"datasets": [{"name": "x", "files": [{"name": "laerm_2022.zip", "size": "5"}]},\n\t]\n}'
    namen = [d.name for d in laden._dateien_aus_index(laden.lies_index_json(text), "https://example.org/ordner/")]
    assert namen == ["laerm_2022.zip"]


def test_gespeichertes_ergebnis_wird_gemerkt_und_bei_aenderung_neu_gelesen(kopie_testdaten):
    erstes = Ergebnis(analyse_id="probe", tabelle=pd.DataFrame({"gebiet_id": ["1"], "wert": [1.0]}),
                      kennzahl_text="", quellen=[], parameter={})
    erstes.speichern()
    gelesen = Ergebnis.laden("probe")
    gelesen.tabelle.loc[0, "wert"] = 99.0  # Änderung an der Kopie wirkt nicht auf den gemerkten Stand
    assert Ergebnis.laden("probe").tabelle.loc[0, "wert"] == 1.0
    zweites = Ergebnis(analyse_id="probe", tabelle=pd.DataFrame({"gebiet_id": ["1"], "wert": [2.0]}),
                      kennzahl_text="", quellen=[], parameter={})
    zweites.speichern()  # sofort danach, also womöglich mit derselben Dateizeit
    assert Ergebnis.laden("probe").tabelle.loc[0, "wert"] == 2.0
    (pfade.verarbeitet("probe") / "ergebnis.json").unlink()
    assert Ergebnis.laden("probe") is None


def test_vektor_mit_vier_koordinaten_im_nebenthread(tmp_path):
    """Erfundene Fläche im Aufbau der Stadtteilgrenzen der Stadt: Punkte mit vier Werten [x, y, 0, 0].

    Streamlit liest im Nebenthread; dort darf nichts abbrechen, und die Fläche kommt zweidimensional an."""
    import threading

    ring = [[7.0, 51.4, 0, 0], [7.01, 51.4, 0, 0], [7.01, 51.41, 0, 0], [7.0, 51.4, 0, 0]]
    pfad = tmp_path / "flaeche.geojson"
    pfad.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "erfunden"},
         "geometry": {"type": "Polygon", "coordinates": [ring]}}]}), encoding="utf-8")
    gelesen = {}
    faden = threading.Thread(target=lambda: gelesen.update(gdf=geo.lies_vektor(pfad)))
    faden.start()
    faden.join()
    assert not gelesen["gdf"].geometry.has_z.any()
    assert gelesen["gdf"].geometry.iloc[0].area > 0
