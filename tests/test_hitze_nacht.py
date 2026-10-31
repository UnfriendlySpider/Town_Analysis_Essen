import io
import shutil
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from essen import analysen, laden, pfade, testdaten
from essen.analysen import hitze_nacht as h
from essen.analysen.basis import Ergebnis


@pytest.mark.parametrize("label, klasse", [
    ("Klasse 3: 15,5 bis 17 °C", 3),
    ("Lufttemperatur um 4 Uhr: 20 - 21,5 °C", 6),
    ("T(4 Uhr) > 23 °C", 8),
    ("keine Angabe zur Lufttemperatur", None),
    ("ab 20 °C", 6),
    ("> 20 - 21,5 °C starke nächtliche Überwärmung", 6),
    ("sehr starke nächtliche Überwärmung", 7),
    ("<= 14 °C sehr niedrige nächtliche Lufttemperaturen", 1),
    ("> 23 °C", 8),
    ("18,5 bis 20 °C", 5),
    ("Kaltluftvolumenstromdichte > 5 - 10 m³/(s·m)", h.AUSGLEICH),
    ("Gewerbegebiet", None),
])
def test_klasse_aus_label(label, klasse):
    assert h.klasse_aus_label(label) == klasse


def test_klassen_aus_temperatur_nach_tabelle_6():
    assert [h.klasse_aus_temperatur(t) for t in (13.9, 14.0, 14.1, 20.0, 20.01, 23.0, 24.4)] == [1, 1, 2, 5, 6, 7, 8]


@pytest.fixture
def ohne_katalog_zuordnung(monkeypatch):
    """Nur Zuordnungen im Datenordner gelten, nicht die geprüfte im Katalog."""
    monkeypatch.setattr(h, "zuordnung_ordner", lambda: [pfade.zuordnungen()])


@pytest.fixture
def klassenraster(kopie_testdaten, ohne_katalog_zuordnung):
    """Ein Klassenraster mit Farbtabelle und QGIS-Legende statt des LANUK-Aufbaus."""
    testdaten.klassenraster_mit_legende()
    return kopie_testdaten


def _vergleiche(ergebnis, erwartet, spalte="anteil_ueber_20c_pct"):
    vergleich = ergebnis.tabelle.merge(erwartet, on="stadtteil", suffixes=("", "_erwartet"))
    assert len(vergleich) == len(erwartet)
    assert (vergleich["wirkraum_ha"] - vergleich["wirkraum_ha_erwartet"]).abs().max() < 0.06
    mit_wert = vergleich.dropna(subset=["anteil_ueber_20c_pct"])
    assert len(mit_wert)
    assert (mit_wert["anteil_ueber_20c_pct"] - mit_wert[spalte]).abs().max() < 0.06


def test_zuordnung_im_katalog_ist_belegt():
    zuordnung = h.lade_zuordnung()
    assert zuordnung["geprueft"] is True and zuordnung["lesart"] == "temperatur"
    assert zuordnung["dateien"] == {"extrem": "PL_KY_NACHT_LT_EXT.tif", "typisch": "PL_KY_NACHT_LT_TYP.tif"}
    assert zuordnung["wirkraum"] == "fehlwerte" and zuordnung["quelle"] and zuordnung["vermerk"]


def test_raster_wie_beim_lanuk(mit_testdaten, katalog):
    """LT- und KVSD-Raster nebeneinander: gelesen wird LT_EXT, Wirkraum sind die Zellen mit Wert."""
    meldungen = []
    ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", melde=meldungen.append)
    assert any("PL_KY_NACHT_LT_EXT.tif" in m for m in meldungen)
    assert any("extremer Sommertag" in hinweis for hinweis in ergebnis.hinweise)
    assert any("Wirkraum aus dem Raster" in hinweis for hinweis in ergebnis.hinweise)
    _vergleiche(ergebnis, pd.read_csv(mit_testdaten["ordner"] / "erwartet_hitze.csv"))
    assert 0 < ergebnis.kennzahl_stadt < 100 and "extremer Sommertag" in ergebnis.kennzahl_text


def test_szenario_typisch(mit_testdaten, katalog):
    meldungen = []
    typisch = analysen.ausfuehren(katalog, "hitze-nacht", {"szenario": "typisch"}, melde=meldungen.append)
    assert any("PL_KY_NACHT_LT_TYP.tif" in m for m in meldungen)
    _vergleiche(typisch, pd.read_csv(mit_testdaten["ordner"] / "erwartet_hitze.csv"), "anteil_ueber_20c_pct_typisch")
    extrem = analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    assert typisch.kennzahl_stadt < extrem.kennzahl_stadt


def test_stadtteilnummer_aus_stadtt(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    tabelle = ergebnis.tabelle
    assert (tabelle["stadtteil_nr"] == tabelle["stadtteil"].str[-2:].astype(int)).all()
    assert not any("geraten" in hinweis for hinweis in ergebnis.hinweise)


def test_mehrere_raster_ohne_dateien_brechen_ab(kopie_testdaten, katalog, ohne_katalog_zuordnung):
    """Ohne Angabe, welche Datei die Temperatur enthält, nicht die größte nehmen (das wäre KVSD)."""
    with pytest.raises(h.ZuordnungFehlt, match="dateien"):
        analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)


def test_raster_mit_legende(klassenraster, katalog):
    ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    assert any("Legende" in hinweis for hinweis in ergebnis.hinweise)
    assert 0 < ergebnis.kennzahl_stadt < 100


def test_ergebnis_wird_gespeichert_und_geladen(mit_testdaten, katalog):
    analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    geladen = Ergebnis.laden("hitze-nacht")
    assert geladen is not None and geladen.testdaten
    assert set(geladen.geometrie["gebiet_id"]) == set(geladen.tabelle["gebiet_id"])


def test_kleine_stadtteile_ohne_anteil(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", {"min_wirkraum_ha": "100000"}, melde=lambda t: None)
    assert ergebnis.tabelle["anteil_ueber_20c_pct"].isna().all()
    assert ergebnis.kennzahl_stadt is None


def test_zuordnung_im_datenordner_hat_vorrang(klassenraster, katalog):
    zuordnung = pfade.zuordnungen() / "klimaanalyse-nacht-raster.yaml"
    zuordnung.parent.mkdir(parents=True, exist_ok=True)
    zeilen = ["datensatz: klimaanalyse-nacht-raster", "lesart: werte", "geprueft: true", "werte:"]
    zeilen += [f"  {w}: 6" for w in range(1, 9)] + [f"  {w}: ausgleich" for w in range(11, 16)]
    zuordnung.write_text("\n".join(zeilen), encoding="utf-8")
    ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    werte = ergebnis.tabelle["anteil_ueber_20c_pct"].dropna()
    assert len(werte) and (werte == 100).all()


def test_ohne_legende_entsteht_eine_vorlage(klassenraster, katalog):
    laden.entferne("klimaanalyse-beschreibung")
    with pytest.raises(h.ZuordnungFehlt, match="Vorlage"):
        analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    vorlage_pfad = pfade.zuordnungen() / "klimaanalyse-nacht-raster.vorlage.yaml"
    vorlage = vorlage_pfad.read_text(encoding="utf-8")
    assert '  11: "?"' in vorlage and "lesart: werte" in vorlage
    import yaml

    assert yaml.safe_load(vorlage)["werte"][11] == "?"  # die Vorlage ist gültiges YAML


def test_halb_ausgefuellte_vorlage_nennt_fehlende_werte(klassenraster, katalog):
    laden.entferne("klimaanalyse-beschreibung")
    with pytest.raises(h.ZuordnungFehlt):
        analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    vorlage = pfade.zuordnungen() / "klimaanalyse-nacht-raster.vorlage.yaml"
    zeilen = []
    for zeile in vorlage.read_text(encoding="utf-8").splitlines():
        for wert in range(1, 9):
            if zeile.startswith(f"  {wert}: "):
                zeile = f"  {wert}: {wert}"
        for wert in range(11, 15):
            if zeile.startswith(f"  {wert}: "):
                zeile = f"  {wert}: ausgleich"
        zeilen.append(zeile)  # 15 bleibt "?"
    (pfade.zuordnungen() / "klimaanalyse-nacht-raster.yaml").write_text("\n".join(zeilen), encoding="utf-8")
    try:
        ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    except h.ZuordnungFehlt as fehler:
        assert "15" in str(fehler)  # mehr als 1 % der Zellen offen: Abbruch mit Nennung
    else:
        assert any("ohne Zuordnung" in hinweis for hinweis in ergebnis.hinweise)


def _tif():
    return next(p for p in laden.entpackt("klimaanalyse-nacht-raster") if p.suffix.lower() == ".tif")


def _ersetze_raster(daten: np.ndarray, dtype: str, nodata=None):
    """Schreibt ein anderes Raster an die Stelle des Testrasters (gleiche Lage)."""
    import rasterio

    ordner = laden.ordner("klimaanalyse-nacht-raster")
    tif = _tif()
    with rasterio.open(tif) as r:
        profil = r.profile
    profil.update(dtype=dtype, nodata=nodata)
    puffer = io.BytesIO()
    with rasterio.MemoryFile() as speicher:
        with speicher.open(**profil) as ds:
            ds.write(daten.astype(dtype), 1)
        puffer.write(speicher.read())
    shutil.rmtree(tif.parent)
    with zipfile.ZipFile(ordner / "Klimaanalyse-Karte-Nacht_2026_EPSG25832_TIFF.zip", "w") as zf:
        zf.writestr("Klimaanalyse-Karte-Nacht_2026_EPSG25832.tif", puffer.getvalue())
    return profil


def test_temperaturraster_wird_eingeteilt(klassenraster, katalog):
    import rasterio

    with rasterio.open(_tif()) as r:
        hoehe, breite = r.height, r.width
    temperatur = np.full((hoehe, breite), 21.0)  # überall Klasse 6
    _ersetze_raster(temperatur, "float32", nodata=-9999.0)
    laden.entferne("klimaanalyse-nacht-vektor")  # ohne Abgrenzung des Wirkraums
    ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    assert any("Temperatur" in hinweis for hinweis in ergebnis.hinweise)
    assert (ergebnis.tabelle["anteil_ueber_20c_pct"].dropna() == 100).all()
    assert (ergebnis.tabelle["anteil_ueber_21_5c_pct"].dropna() == 0).all()


def test_vektor_mit_klassenfeld(kopie_testdaten, katalog):
    """Falls ein GeoPackage doch einen Layer mit Klassen hat: Erkennung über den Klassentext."""
    stadtteile = gpd.read_file(next(laden.ordner("stadtteile").glob("*.geojson"))).to_crs("EPSG:25832")
    x1, y1, x2, y2 = stadtteile.total_bounds
    mitte = (x1 + x2) / 2
    flaechen = gpd.GeoDataFrame(
        {"Kategorie": [h.KLASSEN[6], h.KLASSEN[3], "Kaltluftvolumenstromdichte > 10 m³/(s·m)"]},
        geometry=[box(x1, y1, mitte, y2), box(mitte, y1, x2, y2), box(x1, y1, x2, y1 + 100)], crs="EPSG:25832")
    ordner = laden.ordner("klimaanalyse-nacht-vektor")
    shutil.rmtree(ordner)
    ordner.mkdir()
    gpkg = ordner / "nacht.gpkg"
    flaechen.to_file(gpkg, layer="Klimaanalysekarte_Nacht", driver="GPKG")
    laden.schreibe_abruf(laden.Abruf(datensatz="klimaanalyse-nacht-vektor", dateien=["nacht.gpkg"], url="test",
                                     zeit="2026-10-10T00:00:00", bytes=gpkg.stat().st_size, testdaten=True))
    ergebnis = analysen.ausfuehren(katalog, "hitze-nacht", {"quelle": "vektor"}, melde=lambda t: None)
    assert any("Vektor" in hinweis for hinweis in ergebnis.hinweise)
    werte = ergebnis.tabelle.set_index("stadtteil")["anteil_ueber_20c_pct"].dropna()
    assert werte.between(0, 100).all() and werte.max() > 90 and werte.min() < 10
