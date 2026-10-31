"""VORLAGE: Tests für eine neue Analyse. Kopieren nach tests/test_<thema>.py und anpassen.

Die Tests laufen ohne Internet. Daten mit bekannter Lösung im Test bauen oder die
Fixtures aus tests/conftest.py nutzen (mit_testdaten, kopie_testdaten).
"""

import geopandas as gpd
import pytest
from shapely.geometry import box

from essen import analysen, laden
from essen.geo import DatenFehlen

ANALYSE_ID = "mein-thema"            # ANPASSEN
DATENSATZ = "osm-gruenflaechen"      # ANPASSEN


def _lege_daten_an(stadtteile_pfad):
    """Eine Fläche, die genau die westliche Hälfte des Stadtgebiets bedeckt."""
    stadtteile = gpd.read_file(stadtteile_pfad).to_crs("EPSG:25832")
    x1, y1, x2, y2 = stadtteile.total_bounds
    flaechen = gpd.GeoDataFrame({"art": ["park"]}, geometry=[box(x1, y1, (x1 + x2) / 2, y2)], crs="EPSG:25832")
    ordner = laden.ordner(DATENSATZ)
    ordner.mkdir(parents=True, exist_ok=True)
    datei = ordner / "flaechen.gpkg"
    flaechen.to_file(datei, layer="flaechen", driver="GPKG")
    laden.schreibe_abruf(laden.Abruf(datensatz=DATENSATZ, dateien=[datei.name], url="test",
                                     zeit="2026-10-10T00:00:00", bytes=datei.stat().st_size, testdaten=True))


@pytest.mark.skip(reason="Vorlage: nach dem Anpassen entfernen")
def test_bekannte_loesung(kopie_testdaten, katalog):
    _lege_daten_an(next(laden.ordner("stadtteile").glob("*.geojson")))
    ergebnis = analysen.ausfuehren(katalog, ANALYSE_ID, melde=lambda t: None)
    assert 40 < ergebnis.kennzahl_stadt < 60  # etwa die Hälfte der Fläche


@pytest.mark.skip(reason="Vorlage: nach dem Anpassen entfernen")
def test_fehlende_daten(kopie_testdaten, katalog):
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, ANALYSE_ID, melde=lambda t: None)
