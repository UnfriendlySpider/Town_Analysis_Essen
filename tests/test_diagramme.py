"""Diagramme und Legende: richtige Daten, Hervorhebung, Zählung je Stufe (ohne Browser)."""

import numpy as np
import pandas as pd

from essen import diagramme, karte
from essen.analysen import hole


def _werte():
    return pd.DataFrame({"gebiet_id": ["1", "2", "3", "4", "5"], "stadtteil": ["Altstadt", "Borbeck", "Frohnhausen",
                                                                               "Kettwig", "Werden"],
                         "wert": [5.0, 25.0, 45.0, np.nan, 85.0]})


def _daten(spec: dict) -> list[dict]:
    """Alle eingebetteten Datenzeilen eines Diagramms."""
    return [zeile for werte in spec.get("datasets", {}).values() for zeile in werte]


def test_punktleiste_hebt_stadtteil_hervor_und_laesst_leere_weg():
    spec = diagramme.punktleiste(_werte(), "2", "%", 1, mittel=40.0).to_dict()
    zeilen = _daten(spec)
    assert {z["stadtteil"] for z in zeilen if "stadtteil" in z} == {"Altstadt", "Borbeck", "Frohnhausen", "Werden"}
    assert [z["stadtteil"] for z in zeilen if z.get("markiert")] == ["Borbeck"]
    assert any(z.get("wert") == 40.0 and "stadtteil" not in z for z in zeilen)  # Strich für das Mittel
    assert spec["config"]["locale"]["number"]["decimal"] == ","


def test_balken_in_kartenfarbe_und_sortiert():
    analyse = hole("hitze-nacht")
    tabelle = _werte().rename(columns={"wert": analyse.kennzahl})
    spec = diagramme.balken_sortiert(tabelle, analyse.kennzahl, analyse.stufen, "Anteil", "%", markiert="5").to_dict()
    balken = [z for z in _daten(spec) if "farbe" in z]
    assert {z["stadtteil"]: z["farbe"] for z in balken}["Werden"] == analyse.stufen.farbe(85.0)
    assert len(balken) == 4  # ohne Wert kein Balken
    y = next(e["encoding"]["y"] for e in spec["layer"] if "y" in e.get("encoding", {}))
    assert y["sort"] == ["Werden", "Frohnhausen", "Borbeck", "Altstadt"]
    assert any(p.get("name") == "stadtteil" for p in spec["params"])


def test_streudiagramm_beschriftet_felder_und_ausreisser():
    paar = pd.DataFrame({"gebiet_id": list("abcdef"), "stadtteil": list("ABCDEF"),
                         "x": [1, 2, 3, 4, 5, 20.0], "y": [2, 1, 4, 3, 5, 1.0]})
    spec = diagramme.streu_quadranten(paar, "x", "y", "X", "Y", ("beides hoch", "", "beides niedrig", ""), "b",
                                      anzahl_namen=1).to_dict()
    zeilen = _daten(spec)
    namen = {z["name"] for z in zeilen if z.get("name")}
    assert namen == {"F", "B"}  # weitester Punkt und der markierte
    assert {z["text"] for z in zeilen if z.get("text")} == {"beides hoch", "beides niedrig"}


def test_heatmap_hat_zahlen_mit_komma():
    matrix = pd.DataFrame([[1.0, -0.5], [-0.5, 1.0]], index=["Hitze", "Grün"], columns=["Hitze", "Grün"])
    zeilen = _daten(diagramme.korrelation_heatmap(matrix).to_dict())
    assert {z["text"] for z in zeilen} == {"1,00", "-0,50"}


def test_legende_zaehlt_stadtteile_je_stufe():
    analyse = hole("hitze-nacht")
    seite = karte.legende_html(analyse.stufen, "Anteil <b>", _werte()["wert"], "%", 1)
    assert "Anteil &lt;b&gt;" in seite  # Titel maskiert
    assert "Mittel der Stadtteile: <b>40,0 %</b>" in seite
    # vier Stadtteile in vier verschiedenen Stufen, eine Stufe leer, einer ohne Wert
    assert seite.count(">1</span>") == 5 and seite.count(">0</span>") == 1
    assert "Anzahl" not in karte.legende_html(analyse.stufen, "ohne Werte")


def test_mini_karte_uebergibt_flaechen_als_geojson(mit_testdaten, katalog):
    """Streamlit wandelt DataFrames in Tabellen um; die Flächen müssen als GeoJSON-Werte im Diagramm stehen."""
    from essen.analysen import ausfuehren

    ergebnis = ausfuehren(katalog, "hitze-nacht", melde=lambda t: None, speichern=False)
    analyse = hole("hitze-nacht")
    spec = diagramme.mini_karte(ergebnis.geometrie, analyse.kennzahl, analyse.stufen, "%").to_dict()
    merkmale = spec["data"]["values"]
    assert merkmale[0]["type"] == "Feature" and merkmale[0]["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert {m["properties"]["farbe"] for m in merkmale} <= set(analyse.stufen.farben) | {analyse.stufen.keine_daten}
    assert spec["width"] > 0 and spec["projection"]["type"] == "mercator"


def test_einwohner_und_alltag_runden():
    from essen import einordnung

    assert einordnung.menschen_ungefaehr(3912) == "etwa 3.900"
    assert einordnung.menschen_ungefaehr(583_411) == "etwa 583.000"
    assert einordnung.flaeche_alltag(90.6) == "etwa so groß wie 130 Fußballfelder"
    assert einordnung.flaeche_alltag(0.3) == ""


def test_legende_ohne_feste_schriftfarbe():
    """Die Legende steht in der App auf hellem und dunklem Grund: Schrift erbt die Farbe des Themas."""
    from essen import analysen, karte

    a = analysen.hole("gruenanteil")
    text = karte.legende_html(a.stufen, a.kennzahl_titel, [10.0, 50.0, None], a.einheit)
    assert "color:inherit" in text and "#46524c" not in text and "#6b7771" not in text


def test_tooltip_der_kennzahlkarte_ist_maskiert():
    """E-005: Werte aus fremden Daten landen im Tooltip als HTML und müssen maskiert sein."""
    import geopandas as gpd
    from shapely.geometry import box

    from essen.analysen.basis import Spalte

    a = hole("gruenanteil")
    gdf = gpd.GeoDataFrame({"gebiet_id": ["1"], "stadtteil": ["<script>alert(1)</script>"], a.kennzahl: [42.0]},
                           geometry=[box(360000, 5700000, 361000, 5701000)], crs="EPSG:25832")
    m = karte.neue_karte()
    karte.kennzahl_flaechen(m, gdf, a.kennzahl, a.stufen, (Spalte("stadtteil", "Stadtteil", "text"),
                                                          Spalte(a.kennzahl, "Grün", "prozent")))
    seite = karte.als_html(m)
    assert "<script>alert(1)" not in seite
    assert "\\u0026lt;script\\u0026gt;alert(1)" in seite  # maskiert, im JSON der Karte als \u0026lt; kodiert


def test_anteile_gestapelt_aus_einer_gemischten_zeile():
    """Mein Stadtteil übergibt eine einzelne Zeile (Spalten vom Typ object); die Anteile müssen Zahlen bleiben."""
    from essen.analysen.basis import Spalte

    zeile = pd.Series({"gebiet_id": "9", "stadtteil": "Testgebiet", "a_pct": 30.0, "b_pct": 70.0})
    diagramm = diagramme.anteile_gestapelt(zeile.to_frame().T, (Spalte("a_pct", "A"), Spalte("b_pct", "B")),
                                           markiert="9")
    daten = next(iter(diagramm.to_dict()["datasets"].values()))
    assert all(isinstance(d["anteil"], float) for d in daten)
    assert sum(d["anteil"] for d in daten) == 100
