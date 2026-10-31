import pandas as pd
import pytest

from essen import analysen, laden
from essen.analysen import laerm as l
from essen.geo import DatenFehlen


def test_zuordnung_im_katalog_ist_belegt():
    zuordnung = l._zuordnung()
    assert zuordnung["geprueft"] is True and zuordnung["quelle"] and zuordnung["vermerk"]
    assert set(zuordnung["quellen"]) == {"strasse", "schiene_db", "ruhrbahn", "industrie"}
    assert zuordnung["quellen"]["schiene_db"]["feld"] == "KLASSE"
    assert zuordnung["quellen"]["ruhrbahn"]["feld"] == "ISOV1"


def test_untergrenzen():
    werte = pd.Series([55.01, 55.0, "60.0", 74.999999])
    assert list(l.untergrenzen(werte)) == [55, 55, 60, 75]


@pytest.mark.parametrize("zeitraum", ["nacht", "ganztags"])
def test_bekannte_loesung(mit_testdaten, katalog, zeitraum):
    ergebnis = analysen.ausfuehren(katalog, "laerm", {"zeitraum": zeitraum}, melde=lambda m: None)
    erwartet = pd.read_csv(mit_testdaten["ordner"] / "erwartet_laerm.csv")
    spalte = "anteil_nacht_pct" if zeitraum == "nacht" else "anteil_24h_pct"
    vergleich = ergebnis.tabelle.merge(erwartet, on="stadtteil")
    assert len(vergleich) == len(erwartet)
    # Puffer werden als Polygone mit endlich vielen Ecken gespeichert, daher kleine Abweichungen
    assert (vergleich["anteil_laut_pct"] - vergleich[spalte]).abs().max() < 0.3
    assert ergebnis.parameter["schwelle_genutzt_db"] == (55 if zeitraum == "nacht" else 65)
    assert 0 < ergebnis.kennzahl_stadt < 100
    assert any("nicht addiert" in h for h in ergebnis.hinweise)
    assert any("Industrieanlagen" in h and "Untergrenze" in h for h in ergebnis.hinweise)


def test_hoehere_schwelle_gibt_weniger_flaeche(mit_testdaten, katalog):
    niedrig = analysen.ausfuehren(katalog, "laerm", {"schwelle_db": "55"}, melde=lambda m: None)
    hoch = analysen.ausfuehren(katalog, "laerm", {"schwelle_db": "70"}, melde=lambda m: None)
    assert hoch.kennzahl_stadt < niedrig.kennzahl_stadt
    with pytest.raises(ValueError, match="nicht erlaubt"):
        analysen.ausfuehren(katalog, "laerm", {"schwelle_db": "57"}, melde=lambda m: None)


def test_unerwarteter_pegel_bricht_ab(kopie_testdaten, katalog):
    """Ein Pegelwert außerhalb der 5-dB-Stufen wird nicht stillschweigend eingeordnet (E-009)."""
    import geopandas as gpd

    pfad = next(p for p in laden.entpackt(l.DATENSATZ) if p.name == "Laerm_DB_Nacht_2016.shp")
    flaechen = gpd.read_file(pfad)
    flaechen.loc[flaechen.index[0], "KLASSE"] = 3.0
    flaechen.to_file(pfad)
    with pytest.raises(l.ZuordnungFehlt, match="unerwartete Werte"):
        analysen.ausfuehren(katalog, "laerm", melde=lambda m: None)


def test_fehlende_datei(kopie_testdaten, katalog):
    for pfad in laden.entpackt(l.DATENSATZ):
        if pfad.stem == "Laerm_Ruhrbahn_24h_2016":
            pfad.unlink()
    with pytest.raises(l.ZuordnungFehlt, match=r"Laerm_Ruhrbahn_24h_2016\.shp fehlt"):
        analysen.ausfuehren(katalog, "laerm", {"zeitraum": "ganztags"}, melde=lambda m: None)


def test_fehlende_daten(kopie_testdaten, katalog):
    laden.entferne(l.DATENSATZ)
    with pytest.raises(DatenFehlen):
        analysen.ausfuehren(katalog, "laerm", melde=lambda m: None)
