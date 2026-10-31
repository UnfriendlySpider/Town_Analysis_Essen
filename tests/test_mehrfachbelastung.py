import pandas as pd

from essen import analysen
from essen.analysen import mehrfachbelastung as m
from essen.analysen.basis import Ergebnis


def test_oberstes_fuenftel_mit_gleichstand_und_luecken():
    werte = pd.Series([1, 9, 5, 9, None, 3, 2, 8, 7, 6, 4, 0])
    oben = m.oberstes_fuenftel(werte)  # 11 Werte → 3 oben; Grenze 8, 9 kommt zweimal vor
    assert list(oben[oben.fillna(False)].index) == [1, 3, 7]
    assert pd.isna(oben[4])
    assert list(m.oberstes_fuenftel(pd.Series([5, 5, 5, 1, 1]))) == [True, True, True, False, False]


def test_bekannte_loesung(kopie_testdaten, katalog):
    meldungen = []
    ergebnis = analysen.ausfuehren(katalog, "mehrfachbelastung", melde=meldungen.append)
    t = ergebnis.tabelle.set_index("gebiet_id")
    erwartet = pd.Series(0, index=t.index)
    for analyse_id in m.THEMEN:
        einzel = Ergebnis.laden(analyse_id)  # von der Mehrfachbelastung mit Standard-Einstellungen gerechnet
        werte = einzel.tabelle.assign(gebiet_id=einzel.tabelle["gebiet_id"].astype(str)).set_index("gebiet_id")[
            analysen.hole(analyse_id).kennzahl]
        grenze = werte.dropna().sort_values(ascending=False).iloc[max(1, -(-len(werte.dropna()) // 5)) - 1]
        erwartet += (werte >= grenze).reindex(t.index).fillna(False).astype(int)
    assert (t["anzahl_belastungen"] == erwartet).all()
    assert ergebnis.kennzahl_stadt == (erwartet >= 2).sum()
    assert any("Rechne" in z for z in meldungen)
    # zweiter Lauf nutzt die gespeicherten Einzelergebnisse
    meldungen.clear()
    analysen.ausfuehren(katalog, "mehrfachbelastung", melde=meldungen.append)
    assert not any("Rechne" in z for z in meldungen)
    assert any("kein Grenzwert" in h for h in ergebnis.hinweise)
    assert t["einwohner"].sum() > 0 and any("wohnen geschätzt" in h for h in ergebnis.hinweise)


def test_einzelergebnis_mit_anderen_einstellungen_wird_neu_gerechnet(kopie_testdaten, katalog):
    analysen.ausfuehren(katalog, "laerm", {"zeitraum": "ganztags"}, melde=lambda z: None)
    meldungen = []
    analysen.ausfuehren(katalog, "mehrfachbelastung", melde=meldungen.append)
    assert any("Rechne Lärmbelastung" in z for z in meldungen)
    assert Ergebnis.laden("laerm").parameter["zeitraum"] == "nacht"
