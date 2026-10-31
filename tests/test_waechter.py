import yaml

from essen import waechter


def test_festschreiben_und_pruefen(kopie_testdaten, katalog, tmp_path, monkeypatch):
    datei = tmp_path / "referenz.yaml"
    referenzen = waechter.festschreiben(katalog, ["versiegelung", "laerm"], melde=lambda m: None, pfad=datei)
    assert set(referenzen) == {"versiegelung", "laerm"} and referenzen["laerm"]["testdaten"] is True
    ergebnisse = {e.analyse_id: e for e in waechter.pruefe(katalog, melde=lambda m: None, pfad=datei)}
    assert {e.zustand for e in ergebnisse.values()} == {"gleich"}

    daten = yaml.safe_load(datei.read_text(encoding="utf-8"))
    daten["analysen"]["laerm"]["kennzahl_stadt"] += 5
    datei.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    ergebnisse = {e.analyse_id: e for e in waechter.pruefe(katalog, melde=lambda m: None, pfad=datei)}
    assert ergebnisse["laerm"].zustand == "abweichend" and abs(ergebnisse["laerm"].abweichung + 5) < 1e-2
    assert ergebnisse["versiegelung"].zustand == "gleich"


def test_echte_referenzen_nicht_mit_testdaten(mit_testdaten, katalog, tmp_path):
    datei = tmp_path / "referenz.yaml"
    datei.write_text(yaml.safe_dump({"analysen": {"laerm": {"kennzahl_stadt": 18.4, "testdaten": False}}}),
                     encoding="utf-8")
    (e,) = waechter.pruefe(katalog, melde=lambda m: None, pfad=datei)
    assert e.zustand == "testdaten"


def test_fehlende_daten_werden_gemeldet(kopie_testdaten, katalog, tmp_path):
    from essen import laden

    laden.entferne("laermkarte-essen")
    datei = tmp_path / "referenz.yaml"
    datei.write_text(yaml.safe_dump({"analysen": {"laerm": {"kennzahl_stadt": 1.0, "testdaten": True}}}),
                     encoding="utf-8")
    (e,) = waechter.pruefe(katalog, melde=lambda m: None, pfad=datei)
    assert e.zustand == "daten_fehlen"


def test_toleranz():
    assert waechter.toleranz(1.0) == waechter.TOLERANZ_ABSOLUT
    assert waechter.toleranz(1000.0) == 10.0
