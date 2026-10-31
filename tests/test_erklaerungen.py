import pytest

from essen import analysen, begriffe, einordnung, hilfetexte


@pytest.mark.parametrize("analyse", analysen.ALLE.values(), ids=lambda a: a.id)
def test_jede_analyse_ist_erklaert(analyse):
    assert analyse.thema_titel and analyse.kurz and analyse.lesehilfe
    assert analyse.richtung in ("hoch_schlecht", "hoch_gut", "neutral")
    assert 1 <= len(analyse.grenzen_kurz) <= 3
    for p in analyse.parameter:
        assert p.hilfe, f"{analyse.id}.{p.name} ohne Hilfetext"
        if p.optionen and not p.selten:
            assert set(p.beschriftungen) >= set(p.optionen), f"{analyse.id}.{p.name}: Wahlwerte ohne Beschriftung"


def test_themen_titel_sind_eindeutig():
    titel = [a.thema_titel for a in analysen.ALLE.values()]
    assert len(titel) == len(set(titel))


def test_begriffe_der_hilfetexte_sind_erklaert():
    for seite, hilfe in hilfetexte.HILFE.items():
        assert hilfe.wozu and hilfe.schritte, seite
        for begriff in hilfe.begriffe:
            assert begriffe.erklaere(begriff), (seite, begriff)


def test_begriff_finden_und_suchen():
    assert "20 °C" in begriffe.erklaere("tropennacht")
    assert "Dezibel" in begriffe.erklaere("Dezibel")
    with pytest.raises(KeyError):
        begriffe.erklaere("gibt es nicht")
    assert "Korrelation" in begriffe.suche("zusammenhängen")


def test_einordnung_beachtet_die_richtung():
    hitze, gruen = analysen.hole("hitze-nacht"), analysen.hole("gruenanteil")
    oben = einordnung.einordnen(hitze, "A", 90.0, 2, 50, 56.8)
    assert oben.stufe == "deutlich_schlechter" and oben.farbe == "red"
    assert "mehr als im Mittel" in oben.satz and "1 von 50 Stadtteilen haben einen höheren Wert" in oben.satz
    assert einordnung.einordnen(gruen, "A", 90.0, 2, 50, 56.8).stufe == "deutlich_besser"
    assert einordnung.einordnen(gruen, "A", 10.0, 50, 50, 56.8).stufe == "deutlich_schlechter"
    assert einordnung.einordnen(hitze, "A", 56.9, 25, 50, 56.8).stufe == "mittel"
    assert "etwa so viel" in einordnung.einordnen(hitze, "A", 56.9, 25, 50, 56.8).satz
    assert "Kein anderer" in einordnung.einordnen(hitze, "A", 99.0, 1, 50, 56.8).satz
    assert einordnung.einordnen(hitze, "A", None, None, 50, 56.8) is None


def test_korrelation_in_worten():
    assert "sehr eng" in einordnung.korrelation_in_worten(-0.97) and "niedrigen" in einordnung.korrelation_in_worten(-0.97)
    assert "kaum" in einordnung.korrelation_in_worten(0.1)
    assert "deutlich" in einordnung.korrelation_in_worten(0.7)


def test_gleichstand_zaehlt_mit_mittlerem_rang():
    mehrfach = analysen.hole("mehrfachbelastung")
    # 8 Stadtteile mit 2 Themen, 15 mit 1: Rang 9 (min), mittlerer Rang 16 → kein „ungünstiger als die meisten“
    e = einordnung.einordnen(mehrfach, "A", 1.0, 9, 50, 0.62, rang_mitte=16.0)
    assert e.stufe == "schlechter" and "1 Thema," in e.satz
