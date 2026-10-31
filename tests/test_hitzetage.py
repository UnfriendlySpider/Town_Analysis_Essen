import datetime as dt

import pandas as pd

from essen import analysen
from essen.analysen import hitzetage_station as ht


def test_jahreswerte_zaehlen_nach_dwd_definition():
    tage = pd.DataFrame({
        "datum": pd.to_datetime(["2020-07-01", "2020-07-02", "2020-07-03", "2020-01-05", "2021-07-01"]),
        "TXK": [31.0, 25.0, 24.9, -1.0, 30.0],
        "TNK": [20.0, 19.9, 12.0, -5.0, 21.0],
        "TMK": [25.0, 22.0, 18.0, -3.0, 25.0],
        "RSK": [0.0, 1.0, 0.0, 2.0, 0.0],
    })
    tabelle = ht.jahreswerte(tage, heute=dt.date(2026, 1, 1)).set_index("jahr")
    assert tabelle.loc[2020, "sommertage"] == 2
    assert tabelle.loc[2020, "heisse_tage"] == 1
    assert tabelle.loc[2020, "tropennaechte"] == 1
    assert tabelle.loc[2020, "frosttage"] == 1 and tabelle.loc[2020, "eistage"] == 1
    assert not tabelle.loc[2020, "vollstaendig"]  # nur wenige Tage


def test_analyse_mit_testdaten(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "hitzetage-station", melde=lambda t: None)
    tabelle = ergebnis.tabelle
    assert tabelle["jahr"].min() == 1991
    assert tabelle.loc[tabelle["jahr"] == dt.date.today().year, "vollstaendig"].item() is False or \
        not tabelle.loc[tabelle["jahr"] == dt.date.today().year, "vollstaendig"].item()
    assert "Heiße Tage" in ergebnis.kennzahl_text
    assert set(ergebnis.quellen) == {"dwd-klima-essen-historisch", "dwd-klima-essen-aktuell"}


def test_historische_werte_haben_vorrang(mit_testdaten):
    tage, _, _ = ht.tageswerte()
    assert not tage["datum"].duplicated().any()
    ueberlappung = tage[(tage["datum"].dt.year == dt.date.today().year - 2) & (tage["datum"].dt.month >= 4)]
    assert (ueberlappung["herkunft"] == "dwd-klima-essen-historisch").all()


def test_unvollstaendiges_jahr_nicht_in_der_rangliste(mit_testdaten, capsys):
    from essen import cli

    cli.main(["analyse", "hitzetage-station"])
    ausgabe = capsys.readouterr().out
    rangliste = ausgabe.split("Höchste Werte", 1)[1].split("Gespeichert", 1)[0]
    assert "nur vollständige Jahre" in rangliste
    assert str(dt.date.today().year) not in rangliste
    assert "unvollständig" in ausgabe
