"""Helfer, die aus den App-Seiten ins Paket gewandert sind (Logik ins Paket, AGENTS.md)."""

import pandas as pd

from essen import einordnung, katalog as kat, laden, vorschau, zeitreihen
from essen.analysen.basis import Ergebnis


def test_einwohner_satz_und_richtung():
    satz = einordnung.einwohner_satz(3912, 20000)
    assert "etwa 3.900 Menschen" in satz and "20 % der Einwohner" in satz
    assert "von etwa 20.000 Menschen im Stadtteil" in einordnung.einwohner_satz(3912, 20000, im_stadtteil=True)
    assert einordnung.richtung_wort(0.4) == "mehr" and einordnung.richtung_wort(-0.1) == "weniger"


def test_stellen_der_zeitreihen():
    assert zeitreihen.stellen("hitzetage-raster", "°C") == 2
    assert zeitreihen.stellen("hitzetage-raster", "Tage") == 1
    assert zeitreihen.stellen("luft-station", "µg/m³") == 1


def test_stempel_auch_im_zip(tmp_path):
    archiv = tmp_path / "daten.zip"
    archiv.write_bytes(b"PK")
    assert vorschau.stempel(f"/vsizip/{archiv}/innen/datei.shp") == archiv.stat().st_mtime
    assert vorschau.stempel(str(tmp_path / "fehlt.csv")) == 0.0


def test_einlesen_bytes_ohne_pfadteile(leerer_datenordner, katalog):
    ds = katalog.datensatz("stadtteile")
    abruf = laden.einlesen_bytes(ds, "../../boese/Stadtteile.geojson", b'{"type": "FeatureCollection", "features": []}')
    assert abruf.dateien == ["Stadtteile.geojson"]
    assert (laden.ordner(ds) / "Stadtteile.geojson").exists()
    assert not (leerer_datenordner.parent / "boese").exists()


def test_tabellen_fuer_die_app(katalog):
    lizenzen = kat.lizenz_tabelle(katalog)
    assert sum(z["Datensätze"] for z in lizenzen) == len(katalog.datensaetze)
    alle = kat.quellen_filtern(katalog)
    assert len(alle) == len(katalog.quellen)
    nur_stadt = kat.quellen_filtern(katalog, ebenen=["stadt"])
    assert nur_stadt and all(q.ebene == "stadt" for q in nur_stadt)
    zeilen = kat.quellen_tabelle(katalog, nur_stadt)
    assert {"Quelle", "Lizenz", "Datensätze"} <= set(zeilen[0])
    ds = katalog.datensatz("stadtteile")
    assert kat.anbieter(katalog, ds) == ds.bereitsteller


def test_stufen_der_schnellanalyse():
    from essen.analysen import schnell

    ergebnis = Ergebnis(analyse_id="schnell-x", tabelle=pd.DataFrame({"stadtteil": list("abcdef"),
                                                                       "je_km2": [1, 2, 3, 4, 5, None]}),
                        kennzahl_text="", quellen=[], parameter={"kennzahl": "je_km2"})
    stufen = schnell.stufen_fuer(ergebnis)
    assert list(stufen.grenzen) == sorted(stufen.grenzen) and len(stufen.farben) == len(stufen.grenzen)
    assert schnell.spalten_fuer(ergebnis)[1].titel == "Anzahl je km²"
