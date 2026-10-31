"""Rauchtests: Kommandozeile und jede Seite der App laufen ohne Ausnahme."""

from pathlib import Path

import pytest

from essen import bericht, cli
from essen.analysen import ALLE, ausfuehren

APP = Path(__file__).resolve().parents[1] / "src" / "essen" / "app"


def test_katalog_pruefen_ueber_die_kommandozeile(capsys):
    with pytest.raises(SystemExit) as ende:
        cli.main(["katalog", "--pruefen"])
    assert ende.value.code == 0
    assert "0 Fehler" in capsys.readouterr().out


def test_analyse_liste(mit_testdaten, capsys):
    cli.main(["analyse"])
    ausgabe = capsys.readouterr().out
    for analyse_id in ALLE:
        assert analyse_id in ausgabe


def test_html_seite(mit_testdaten, katalog):
    ergebnis = ausfuehren(katalog, "hitze-nacht", melde=lambda t: None)
    seite = bericht.schreibe(katalog, ALLE["hitze-nacht"], ergebnis).read_text(encoding="utf-8")
    assert "Testlauf mit erfundenen Testdaten" in seite and "maplibregl.Map" in seite
    assert "__" not in seite.split("<script>")[0]  # alle Platzhalter ersetzt


@pytest.mark.parametrize("seite", sorted(p.name for p in (APP / "seiten").glob("*.py")))
def test_app_seite_laeuft(seite, mit_testdaten):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page(f"seiten/{seite}")
    at.run()
    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("analyse_id", sorted(ALLE))
def test_app_berechnet_jede_analyse(analyse_id, mit_testdaten):
    """Seite Analysen: Analyse wählen, Berechnen klicken, Ergebnis ohne Ausnahme anzeigen."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "start.py"), default_timeout=300)
    at.run()
    at.switch_page("seiten/analysen.py")
    at.run()
    next(s for s in at.selectbox if s.label == "Thema").select(analyse_id)
    at.run()
    next(b for b in at.button if b.label == "Berechnen").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def test_status_raeumt_entpackte_ordner_auf(kopie_testdaten, capsys):
    from essen import laden

    laden.entpackt("klimaanalyse-nacht-raster")
    assert laden.entpackte_ordner("klimaanalyse-nacht-raster")
    cli.main(["status"])
    assert "--aufraeumen" in capsys.readouterr().out
    cli.main(["status", "--aufraeumen", "--ja"])
    assert "frei" in capsys.readouterr().out
    assert not laden.entpackte_ordner("klimaanalyse-nacht-raster")
    assert laden.vorhanden("klimaanalyse-nacht-raster")


def test_veraltetes_ergebnis_wird_erkannt(kopie_testdaten, katalog):
    import dataclasses

    from essen import analysen, laden
    from essen.analysen.basis import veraltet

    analyse = analysen.hole("laerm")
    ergebnis = analysen.ausfuehren(katalog, "laerm", melde=lambda m: None)
    assert veraltet(analyse, ergebnis, {}) == []
    assert "Tageszeit" in veraltet(analyse, ergebnis, {"zeitraum": "ganztags"})[0]
    abruf = laden.lese_abruf("laermkarte-essen")
    laden.schreibe_abruf(dataclasses.replace(abruf, zeit="2999-01-01T00:00:00"))
    assert any("neu geladen" in g for g in veraltet(analyse, ergebnis))


def test_steckbrief_und_vergleich(kopie_testdaten, katalog):
    from essen import analysen, steckbrief

    for kennung in ("versiegelung", "gruenanteil", "laerm"):
        analysen.ausfuehren(katalog, kennung, melde=lambda m: None)
    assert {k.analyse_id for k in steckbrief.verfuegbare()} >= {"versiegelung", "gruenanteil", "laerm"}
    breit = steckbrief.tabelle()
    gebiet = breit["gebiet_id"].iloc[0]
    zeilen = steckbrief.stadtteil(gebiet).set_index("analyse_id")
    wert = breit.set_index("gebiet_id").loc[gebiet, "laerm"]
    assert zeilen.loc["laerm", "wert"] == wert
    assert zeilen.loc["laerm", "rang"] == 1 + (breit["laerm"] > wert).sum()
    paar, r = steckbrief.vergleich("versiegelung", "gruenanteil")
    assert len(paar) > 3 and -1 <= r <= 1
    assert abs(steckbrief.korrelationen().loc["laerm", "laerm"] - 1) < 1e-9


def test_steckbrief_seiten_mit_ergebnissen(kopie_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    from essen import analysen

    for kennung in ("versiegelung", "laerm"):
        analysen.ausfuehren(katalog, kennung, melde=lambda m: None)
    for seite in ("stadtteil.py", "vergleich.py"):
        at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
        at.run()
        at.switch_page(f"seiten/{seite}")
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        assert at.selectbox, seite


def test_zeitreihen_und_trend(kopie_testdaten, katalog):
    import pandas as pd
    from streamlit.testing.v1 import AppTest

    from essen import analysen, zeitreihen

    analysen.ausfuehren(katalog, "luft-station", melde=lambda m: None)
    analysen.ausfuehren(katalog, "hitzetage-station", melde=lambda m: None)
    reihe = zeitreihen.zeitreihe("luft-station")
    assert {"höchstes Jahresmittel", "Essen Teststraße (DENW901)"} <= set(reihe.daten["reihe"])
    assert reihe.vergleich and 40 in reihe.vergleich.values()
    # erfundene Reihe mit bekannter Steigung: +0,5 je Jahr = +5 je 10 Jahre
    test = pd.DataFrame({"jahr": range(2000, 2010), "reihe": "x", "wert": [0.5 * i for i in range(10)],
                         "vollstaendig": [True] * 9 + [False]})
    t = zeitreihen.trend(test)
    assert abs(t.loc[0, "je_10_jahre"] - 5) < 1e-9 and t.loc[0, "jahre"] == 9
    linie = zeitreihen.trendlinien(test)
    assert list(linie["jahr"]) == [2000, 2008] and abs(linie["wert"].iloc[1] - 4.0) < 1e-9
    mittel = zeitreihen.zeitraum_mittel(test, 2000, 2004, mindestens=5)
    assert abs(mittel.loc[0, "mittel"] - 1.0) < 1e-9 and mittel.loc[0, "jahre"] == 5
    assert zeitreihen.zeitraum_mittel(test, 2000, 2004, mindestens=6).empty
    assert 1965 in zeitreihen.zeitreihe("hitzetage-station").marken
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/zeitreihen.py")
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_zeitreihen_je_stadtteil_in_der_app(kopie_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    from essen import analysen, zeitreihen

    analysen.ausfuehren(katalog, "hitzetage-raster", melde=lambda m: None)
    analysen.ausfuehren(katalog, "hitzetage-station", melde=lambda m: None)
    gebiete = [g for g in zeitreihen.stadtteile() if g != "essen"]
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/zeitreihen.py")
    at.query_params["stadtteil"] = gebiete[2]
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key="zeitreihe-gebiet").value == gebiete[2]
    assert any("Früher und heute" in s.value for s in at.subheader)
    at.toggle(key="zeitreihe-station").set_value(True)
    at.segmented_control(key="zeitreihe-kennwert").set_value("jahresmittel_c")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("°C" in m.value for m in at.metric)


LESESEITEN = ["uebersicht.py", "stadtteil.py", "themen.py", "karte.py", "vergleich.py", "zeitreihen.py", "begriffe.py",
              "daten_erklaert.py"]


@pytest.mark.parametrize("seite", LESESEITEN)
def test_leseseiten_ohne_daten_verweisen_auf_vorbereiten(seite, leerer_datenordner):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page(f"seiten/{seite}")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    if seite not in ("begriffe.py", "daten_erklaert.py"):  # zeigen Texte, keine Ergebnisse
        texte = " ".join(i.value for i in at.info)
        assert "Alles vorbereiten" in texte, seite


@pytest.mark.parametrize("analyse_id", sorted(ALLE))
def test_themenseite_zeigt_jedes_thema(analyse_id, kopie_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    ausfuehren(katalog, analyse_id, melde=lambda t: None)
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.query_params["thema"] = analyse_id
    at.run()
    at.switch_page("seiten/themen.py")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    text = " ".join(m.value for m in at.markdown)
    assert ALLE[analyse_id].lesehilfe in text and "Was diese Zahl nicht sagt" in text


def test_leseseiten_ohne_pfade_und_kennungen():
    """Seiten für Einsteiger zeigen keine Dateipfade, YAML-Namen oder Datensatz-Kennungen in Backticks."""
    import re

    for seite in LESESEITEN:
        quelltext = (APP / "seiten" / seite).read_text(encoding="utf-8")
        texte = " ".join(re.findall(r'"([^"]{12,})"', quelltext))
        for verboten in ("data/", ".yaml", "katalog/", "data_test", "`"):
            assert verboten not in texte, f"{seite}: {verboten}"


def test_hilfe_auf_jeder_seite():
    for datei in (APP / "seiten").glob("*.py"):
        assert "seitenhilfe(" in datei.read_text(encoding="utf-8"), datei.name


def test_zeitreihen_waehlt_thema_aus_dem_link(kopie_testdaten, katalog):
    """Links von „Themen“ geben ?thema= mit; die Seite zeigt dann dieses Thema statt des ersten."""
    from streamlit.testing.v1 import AppTest

    from essen import analysen

    analysen.ausfuehren(katalog, "hitzetage-raster", melde=lambda m: None)
    analysen.ausfuehren(katalog, "luft-station", melde=lambda m: None)
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/zeitreihen.py")
    at.query_params["thema"] = "luft-station"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.segmented_control(key="zeitreihe-thema").value == "luft-station"
    assert at.query_params["thema"] == "luft-station"


def test_alles_vorbereiten_gesperrt_ohne_platz(leerer_datenordner, monkeypatch):
    from streamlit.testing.v1 import AppTest

    from essen import vorbereiten

    plan = vorbereiten.Plan(fehlend=["stadtteile"], von_hand=[], download_mb=2000, groesse_unbekannt=[], frei_gb=8,
                            zu_rechnen=[])
    assert not plan.genug_platz  # 10 × 2 GB nötig
    assert vorbereiten.Plan(**{**plan.__dict__, "frei_gb": 30}).genug_platz
    monkeypatch.setattr(vorbereiten, "plan", lambda k: plan)
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/vorbereiten.py")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    at.checkbox[0].check().run()
    assert next(b for b in at.button if b.label == "Alles vorbereiten").disabled


def test_themen_nach_abwahl_mit_hinweis(mit_testdaten):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/themen.py")
    at.run()
    at.pills(key="thema-wahl").set_value(None).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Thema wählen" in i.value for i in at.info)


def test_vergleich_und_neu_berechnen_lesen_den_link(kopie_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    from essen import analysen

    for kennung in ("versiegelung", "laerm", "gruenanteil"):
        analysen.ausfuehren(katalog, kennung, melde=lambda m: None)
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/vergleich.py")
    at.query_params["a"], at.query_params["b"] = "laerm", "versiegelung"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert (at.selectbox(key="vergleich-a").value, at.selectbox(key="vergleich-b").value) == ("laerm", "versiegelung")
    at.switch_page("seiten/analysen.py")
    at.query_params.clear()
    at.query_params["analyse"] = "laerm"  # alter Link
    at.run()
    assert next(s for s in at.selectbox if s.label == "Thema").value == "laerm"
    assert at.query_params["thema"] == "laerm"


def test_schnellanalyse_zeigt_gespeichertes_ergebnis(kopie_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    from essen.analysen import schnell
    from essen.geo import hat_vektordaten

    kennung = next(ds.id for ds in katalog.datensaetze.values() if ds.id != "stadtteile" and hat_vektordaten(ds.id))
    schnell.verteile(katalog, kennung, melde=lambda t: None).speichern()
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/schnellanalyse.py")
    at.query_params["datensatz"] = kennung
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Zuletzt verteilt" in c.value for c in at.caption)


def test_daten_erklaert_zeigt_datensatz_aus_dem_link(mit_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    at.switch_page("seiten/daten_erklaert.py")
    at.query_params["datensatz"] = "stadtteile"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key="daten-erklaert-wahl").value == "stadtteile"
    text = " ".join(m.value for m in at.markdown)
    assert "Woher kommen die Daten?" in text and "Auf einen Blick" in text
    at.text_input(key="daten-erklaert-suche").input("Wetterdienst").run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key="daten-erklaert-wahl").value != "stadtteile"  # die Suche filtert die Liste


def test_karte_und_start_mit_ergebnissen(kopie_testdaten, katalog):
    from streamlit.testing.v1 import AppTest

    from essen import analysen, punktebenen

    for kennung in ("hitze-nacht", "gruenanteil", "laerm"):
        analysen.ausfuehren(katalog, kennung, melde=lambda m: None)
    at = AppTest.from_file(str(APP / "start.py"), default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Essen in Zahlen" in s.value for s in at.subheader)
    at.switch_page("seiten/karte.py")
    at.query_params["thema"] = "laerm"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert next(s for s in at.selectbox if s.label == "Was möchten Sie sehen?").value == "laerm"
    ebenen = [e.id for e in punktebenen.verfuegbar()]
    if ebenen:
        at.multiselect(key="punktebenen").set_value(ebenen[:1]).run()
        assert not at.exception, [e.value for e in at.exception]
