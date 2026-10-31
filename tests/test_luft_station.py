import json

import pandas as pd
import pytest

from essen import analysen, laden
from essen.analysen import luft_station as l
from essen.geo import DatenFehlen


def test_nur_essener_stationen(mit_testdaten):
    stationen = l.stationen_in_essen()
    assert set(stationen["code"]) == {"DENW901", "DENW902", "DENW903"}


@pytest.mark.parametrize("schadstoff", ["no2", "pm10", "pm25"])
def test_bekannte_loesung(mit_testdaten, katalog, schadstoff):
    ergebnis = analysen.ausfuehren(katalog, "luft-station", {"schadstoff": schadstoff}, melde=lambda m: None)
    erwartet = pd.read_csv(mit_testdaten["ordner"] / "erwartet_luft.csv")
    erwartet = erwartet[erwartet["schadstoff"] == schadstoff]
    je_jahr = erwartet.groupby("jahr")["wert"]
    t = ergebnis.tabelle.set_index("jahr")
    assert (t["hoechstes_jahresmittel_ug_m3"] == je_jahr.max()).all()
    assert (t["stationen"] == je_jahr.size()).all()
    grenze = l.GRENZWERTE[schadstoff]["eu"]
    assert (t["stationen_ueber_eu"] == erwartet.assign(ueber=erwartet["wert"] > grenze).groupby("jahr")["ueber"].sum()).all()
    assert ergebnis.kennzahl_stadt == je_jahr.max().loc[2025]
    assert "wert_DENW904" not in t.columns  # Station außerhalb Essens


def test_spalten_nach_headers_nicht_nach_position(kopie_testdaten, katalog):
    pfad = laden.ordner(l.DATENSATZ) / "jahr_2025_no2.json"
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    daten["headers"] = {"1": daten["headers"]["2"], "2": daten["headers"]["1"]}
    daten["data"] = [[z[0], z[2], z[1]] for z in daten["data"]]
    pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    ergebnis = analysen.ausfuehren(katalog, "luft-station", melde=lambda m: None)
    erwartet = pd.read_csv(laden.pfade.daten() / "erwartet_luft.csv")
    hoechst = erwartet[(erwartet["schadstoff"] == "no2") & (erwartet["jahr"] == 2025)]["wert"].max()
    assert ergebnis.kennzahl_stadt == hoechst


def test_ohne_jahresmittel_bricht_ab(kopie_testdaten, katalog):
    pfad = laden.ordner(l.DATENSATZ) / "jahr_2024_no2.json"
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    daten["headers"] = {"1": "Median in µg/m³"}
    pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(l.ZuordnungFehlt, match="kein eindeutiges Jahresmittel"):
        analysen.ausfuehren(katalog, "luft-station", melde=lambda m: None)


def test_fehlende_daten(kopie_testdaten, katalog):
    laden.entferne(l.DATENSATZ)
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "luft-station", melde=lambda m: None)
