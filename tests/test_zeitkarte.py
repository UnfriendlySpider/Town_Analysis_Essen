"""Karte über die Jahre: Jahrzehnt-Mittel, SVG-Pfade, Daten für die Anzeige und die App-Ansicht."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import MultiPolygon, Polygon, box

from essen import analysen, zeitkarte
from essen.analysen.basis import Ergebnis

APP = Path(__file__).resolve().parents[1] / "src" / "essen" / "app"


def _jahre(von=1951, bis=2023, gebiete=("1", "2")) -> pd.DataFrame:
    zeilen = [{"gebiet_id": g, "jahr": j, "heisse_tage": float(j - 1950) + (5 if g == "2" else 0), "vollstaendig": True}
              for g in gebiete for j in range(von, bis + 1)]
    return pd.DataFrame(zeilen)


def test_jahrzehnte_mitteln_und_beschriften_angebrochene():
    schritte = zeitkarte.jahrzehnt_mittel(_jahre(), "heisse_tage")
    assert [s.titel for s in schritte] == ["1951–1959", "1960er", "1970er", "1980er", "1990er", "2000er", "2010er",
                                          "2020–2023"]
    sechziger = schritte[1]
    assert (sechziger.von, sechziger.bis, sechziger.jahre) == (1960, 1969, 10)
    assert sechziger.werte == {"1": pytest.approx(14.5), "2": pytest.approx(19.5)}


def test_unvollstaendige_jahre_und_kurze_jahrzehnte_fallen_weg():
    jahre = _jahre(bis=2021)
    jahre.loc[jahre["jahr"] == 2021, "vollstaendig"] = False
    titel = [s.titel for s in zeitkarte.jahrzehnt_mittel(jahre, "heisse_tage")]
    assert titel[-1] == "2010er"  # 2020 allein ist zu wenig für ein Mittel
    assert [s.titel for s in zeitkarte.einzeljahre(jahre, "heisse_tage")][-1] == "2020"


def test_svg_pfade_mit_loch_und_mehrteilig():
    ring = box(0, 0, 1000, 2000)
    mit_loch = Polygon(ring.exterior.coords, [box(200, 200, 400, 400).exterior.coords])
    zweiteilig = MultiPolygon([box(1000, 0, 1500, 500), box(1600, 0, 2000, 500)])
    gdf = gpd.GeoDataFrame({"gebiet_id": ["1", "2"], "stadtteil": ["A", "B"]}, geometry=[mit_loch, zweiteilig],
                           crs="EPSG:25832")
    pfade, hoehe = zeitkarte.svg_pfade(gdf, breite=200)
    assert hoehe == pytest.approx(200.0)
    assert [p["name"] for p in pfade] == ["A", "B"]
    assert pfade[0]["d"].count("M") == 2 and pfade[1]["d"].count("M") == 2
    # Norden oben: die Nordwestecke (0, 2000) liegt bei 0,0; das Loch (200–400 m) bei y = (2000 − 400) / 10 = 160
    assert "L0.0,0.0" in pfade[0]["d"] and "20.0,160.0" in pfade[0]["d"]


def test_daten_fuer_die_anzeige():
    analyse = analysen.hole("hitzetage-raster")
    gdf = gpd.GeoDataFrame({"gebiet_id": ["1", "2"], "stadtteil": ["A", "B"]},
                           geometry=[box(0, 0, 1000, 1000), box(1000, 0, 2000, 1000)], crs="EPSG:25832")
    jahre = pd.concat([_jahre(), _jahre(gebiete=("essen",))], ignore_index=True)  # „Essen gesamt“ ohne Fläche
    ergebnis = Ergebnis(analyse_id=analyse.id, tabelle=pd.DataFrame(), kennzahl_text="", quellen=[], parameter={},
                        geometrie=gdf, jahreswerte=jahre)
    werte = zeitkarte.verfuegbar(analyse, ergebnis)
    assert [z.feld for z in werte] == ["heisse_tage"]  # Sommertage und Jahresmittel fehlen in diesen Jahreswerten
    daten = zeitkarte.daten(ergebnis, werte[0])
    assert len(daten["pfade"]) == 2 and len(daten["schritte"]) == 8
    letzter = daten["schritte"][-1]
    assert letzter["texte"] == ["71,5 Tage", "76,5 Tage"]  # 2020–2023: 70 bis 73
    assert letzter["farben"] == [werte[0].stufen.farben[-1]] * 2
    assert daten["schritte"][0]["untertitel"] == "Mittel aus 9 Jahren (1951–1959)"
    assert len(daten["legende"]) == len(werte[0].stufen.farben)
    assert zeitkarte.verfuegbar(analyse, None) == []


def test_datenstand_nur_mit_jahreszahl(katalog):
    assert "2024" in zeitkarte.datenstand(katalog, analysen.hole("versiegelung"))
    assert zeitkarte.datenstand(katalog, analysen.hole("kuehlorte")) == ""  # „laut Datensatz“ hilft niemandem


def test_themenseite_zeigt_den_verlauf(kopie_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    analysen.ausfuehren(katalog, "hitzetage-raster", melde=lambda t: None)
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/themen.py")
    at.query_params["thema"] = "hitzetage-raster"
    at.run()
    next(s for s in at.segmented_control if s.key == "ansicht-hitzetage-raster").set_value("verlauf")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any(m.value.startswith("**Heiße Tage pro Jahr") for m in at.markdown)
    next(s for s in at.segmented_control if s.key == "themen-zk-hitzetage-raster-art").set_value("jahre")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
