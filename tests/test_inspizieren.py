from essen import legenden
from essen.inspizieren import inspiziere_datensatz


def test_raster_bericht_wie_beim_lanuk(mit_testdaten, katalog):
    """Das echte ZIP: mehrere stetige Raster mit Fehlwert -999, keine Legende."""
    text = inspiziere_datensatz(katalog, "klimaanalyse-nacht-raster").als_markdown()
    for datei in ("PL_KY_NACHT_LT_EXT.tif", "PL_KY_NACHT_LT_TYP.tif", "PL_KY_NACHT_KVSD_EXT.tif"):
        assert f"Raster {datei}" in text
    assert "Stetige Werte" in text and "-999" in text and "float32" in text


def test_raster_bericht_zeigt_klassen_und_legende(kopie_testdaten, katalog):
    from essen import testdaten

    testdaten.klassenraster_mit_legende()
    bericht = inspiziere_datensatz(katalog, "klimaanalyse-nacht-raster")
    text = bericht.als_markdown()
    assert "Klassenraster" in text and "Farbtabelle" in text
    assert any(e.wert == "6" and "starke" in e.label for e in bericht.legende)
    werte = next(iter(bericht.rasterwerte.values()))["werte"]
    assert set(werte) <= set(range(1, 16))
    assert bericht.speichern("test-raster").exists()


def test_vektor_bericht_listet_layer_und_felder(mit_testdaten, katalog):
    text = inspiziere_datensatz(katalog, "klimaanalyse-nacht-vektor").als_markdown()
    for layer in ("PL_KY_Verkehr", "PL_KY_Wasser", "PL_KY_KL_Leitbahn", "PL_KY_KL_Austausch", "PL_KY_KL_Produktion"):
        assert f"Layer {layer}" in text
    assert "KT_R02_2" in text and "gridcode" in text


def test_tabelle_und_testdaten_hinweis(mit_testdaten, katalog):
    text = inspiziere_datensatz(katalog, "dwd-klima-essen-aktuell").als_markdown()
    assert "Tabelle" in text and "TXK" in text and "erfundene Testdaten" in text


SLD = """<?xml version="1.0"?><StyledLayerDescriptor xmlns="http://www.opengis.net/sld"><NamedLayer><UserStyle>
<FeatureTypeStyle><Rule><RasterSymbolizer><ColorMap>
<ColorMapEntry color="#FF0000" quantity="6" label="starke Überwärmung"/>
</ColorMap></RasterSymbolizer></Rule></FeatureTypeStyle></UserStyle></NamedLayer></StyledLayerDescriptor>"""

QML_RAMPE = """<qgis><pipe><rasterrenderer type="singlebandpseudocolor"><rastershader><colorrampshader>
<item value="20" color="#fdae61" label="20 °C" alpha="255"/><item value="22" color="215,25,28,255" label="22 °C"/>
</colorrampshader></rastershader></rasterrenderer></pipe></qgis>"""

LYRX = '{"renderer": {"groups": [{"classes": [{"label": "Klasse A", "values": [{"fieldValues": ["1"]}]}]}]}}'


def test_legenden_aus_sld_qml_und_lyrx(tmp_path):
    (tmp_path / "a.sld").write_text(SLD, encoding="utf-8")
    (tmp_path / "b.qml").write_text(QML_RAMPE, encoding="utf-8")
    (tmp_path / "c.lyrx").write_text(LYRX, encoding="utf-8")
    eintraege = legenden.aus_pfad(tmp_path)
    assert ("6", "starke Überwärmung", "#ff0000") in [(e.wert, e.label, e.farbe) for e in eintraege]
    assert ("22", "#d7191c") in [(e.wert, e.farbe) for e in eintraege]
    assert any(e.label == "Klasse A" for e in eintraege)


def test_file_geodatabase_als_vektorquelle(tmp_path):
    """Ein .gdb-Ordner erscheint mit Layern und Feldern, nicht als Liste von .gdbtable-Dateien."""
    import geopandas as gpd
    from shapely.geometry import box

    from essen.inspizieren import inspiziere_pfad

    gdb = tmp_path / "daten" / "Test.gdb"
    gdb.parent.mkdir()
    gpd.GeoDataFrame({"potenzial": [1.0, 2.5]}, geometry=[box(361000, 5702000, 361100, 5702100),
                                                       box(361200, 5702000, 361300, 5702100)],
                     crs="EPSG:25832").to_file(gdb, layer="dach", driver="OpenFileGDB")
    for ziel in (gdb, tmp_path / "daten"):
        text = inspiziere_pfad(ziel).als_markdown()
        assert "Vektordatei Test.gdb" in text and "Layer dach" in text and "potenzial" in text
        assert ".gdbtable" not in text
