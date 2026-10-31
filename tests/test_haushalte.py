"""Privathaushalte je Stadtteil: Lesen (Windows-Zeichensatz), Zuordnung über die Nummer, Anteile, Jahreswerte."""

import pytest

from essen import analysen, laden, zeitkarte
from essen.analysen import haushalte
from essen.geo import DatenFehlen


def test_haushalte_mit_testdaten(mit_testdaten, katalog):
    ergebnis = analysen.ausfuehren(katalog, "haushalte", melde=lambda m: None, speichern=False)
    tabelle = ergebnis.tabelle.set_index("stadtteil_nr")
    assert len(tabelle) == 12 and {"gebiet_id", "stadtteil", "stadtteil_nr"} <= set(ergebnis.tabelle.columns)
    # Gebiet 1 im Jahr 2025: 1.100 Haushalte, 100 + 10 × 18 = 280 mit Kindern
    assert tabelle.loc[1, "anteil_kinder_pct"] == pytest.approx(100 * 280 / 1100, abs=0.05)
    assert tabelle.loc[1, "anteil_kinder_aenderung"] == pytest.approx(100 * 280 / 1100 - 100 * 100 / 1100, abs=0.1)
    assert tabelle.loc[2, "personen_je_haushalt"] == pytest.approx((2 * 1200 - 100) / 1200, abs=0.005)
    # Die letzte Nummer fehlt in der Tabelle: kein Wert, aber ein Hinweis
    assert tabelle.loc[12, "anteil_kinder_pct"] != tabelle.loc[12, "anteil_kinder_pct"]
    assert any("Ohne Haushaltszahlen" in h for h in ergebnis.hinweise)

    jahre = ergebnis.jahreswerte
    assert sorted(jahre["jahr"].unique()) == list(range(2007, 2026)) and jahre["vollstaendig"].all()
    assert jahre[jahre["stadtteil"].str.contains("ö")].empty  # Namen kommen aus den Grenzen, nicht aus der CSV
    gebiet1 = jahre[jahre["gebiet_id"] == tabelle.loc[1, "gebiet_id"]].sort_values("jahr")
    assert gebiet1["anteil_kinder_pct"].is_monotonic_increasing

    stadt = 100 * sum((280 if nr == 1 else 150 + 5 * nr) for nr in range(1, 12)) / sum(1000 + 100 * nr for nr in range(1, 12))
    assert ergebnis.kennzahl_stadt == pytest.approx(stadt)

    werte = zeitkarte.verfuegbar(analysen.hole("haushalte"), ergebnis)
    assert [z.feld for z in werte] == ["anteil_kinder_pct", "anteil_einpersonen_pct"]
    assert [s["titel"] for s in zeitkarte.daten(ergebnis, werte[0])["schritte"]] == ["2007–2009", "2010er", "2020–2025"]


def test_lies_meldet_geaenderten_aufbau(tmp_path):
    pfad = tmp_path / "haushalte.csv"
    pfad.write_text("Stadtteil;Jahr;INSGESAMT\n1;2020;100\n", encoding="utf-8")
    with pytest.raises(ValueError, match="HH_EINE_PERSON"):
        haushalte.lies(pfad)


def test_haushalte_ohne_daten(kopie_testdaten, katalog):
    (laden.ordner("privathaushalte-stadtteile") / laden.ABRUF_DATEI).unlink()
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "haushalte", melde=lambda m: None, speichern=False)
