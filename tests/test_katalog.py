from essen import analysen, pfade
from essen.katalog import AUTOMATISCH, als_markdown, quellenangabe


def test_katalog_hat_keine_fehler(katalog):
    fehler, _ = katalog.pruefe()
    assert fehler == []


def test_jeder_datensatz_hat_quelle_lizenz_und_seite(katalog):
    for ds in katalog.datensaetze.values():
        assert ds.quelle in katalog.quellen
        assert ds.lizenz in katalog.lizenzen
        assert ds.seite.startswith("https://")


def test_analysen_und_katalog_passen_zusammen(katalog):
    for analyse in analysen.ALLE.values():
        for kennung in (*analyse.benoetigt, *analyse.optional):
            assert kennung in katalog.datensaetze, f"{analyse.id} braucht {kennung}, der fehlt im Katalog"
    for ds in katalog.datensaetze.values():
        for analyse_id in ds.analysen:
            assert analyse_id in analysen.ALLE, f"{ds.id} nennt unbekannte Analyse {analyse_id}"


def test_automatische_downloads_haben_ein_ziel(katalog):
    for ds in katalog.datensaetze.values():
        if ds.download.art in AUTOMATISCH:
            assert ds.download.url or ds.download.urls or (ds.download.ordner and ds.download.muster)


def test_quellenangabe_bei_namensnennung_mit_aenderungsvermerk(katalog):
    text = quellenangabe(katalog, katalog.datensatz("stadtteile"), "2026-10-10")
    assert "DL-DE BY 2.0" in text and "Daten geändert" in text and "10.10.2026" in text


def test_quellenangabe_mit_vorgegebenem_wortlaut(katalog):
    text = quellenangabe(katalog, katalog.datensatz("basemap-de"), "2026-10-10", geaendert=False)
    assert text.startswith("© GeoBasis-DE / BKG (2026) CC BY 4.0")


def test_uebersicht_nennt_alle_datensaetze(katalog):
    text = als_markdown(katalog)
    for ds in katalog.datensaetze.values():
        assert ds.titel in text


def test_doku_der_datenquellen_ist_aktuell(katalog):
    """docs/datenquellen.md muss nach jeder Katalogänderung neu erzeugt werden: uv run essen katalog --doku"""
    gespeichert = (pfade.docs() / "datenquellen.md").read_text(encoding="utf-8")
    ohne_datum = lambda text: [z for z in text.splitlines() if not z.startswith("Stand:")]  # noqa: E731
    assert ohne_datum(gespeichert) == ohne_datum(als_markdown(katalog))


def test_domains_fuer_netzwerkfreigabe(katalog):
    domains = katalog.domains()
    assert "www.opengeodata.nrw.de" in domains and "opendata.essen.de" in domains


def test_erklaerung_fuer_jeden_genutzten_datensatz(katalog):
    """Jeder Datensatz, mit dem ein Thema rechnet, hat alle vier Abschnitte für „Daten erklärt“."""
    from essen import analysen
    from essen.katalog import Erklaerung

    for ds in katalog.datensaetze.values():
        if analysen.nutzer(ds.id):
            assert ds.erklaerung is not None, ds.id
            assert len(ds.erklaerung.abschnitte()) == len(Erklaerung.ABSCHNITTE), ds.id


def test_erklaerung_unbekanntes_feld_ist_ein_fehler(tmp_path):
    import shutil

    import pytest

    from essen.katalog import KatalogFehler, lade

    for datei in pfade.katalog().glob("*.yaml"):
        shutil.copy(datei, tmp_path / datei.name)
    pfad = tmp_path / "datensaetze.yaml"
    text = pfad.read_text(encoding="utf-8")
    assert "  erklaerung:\n    herkunft:" in text
    pfad.write_text(text.replace("  erklaerung:\n    herkunft:", "  erklaerung:\n    quatsch: x\n    herkunft:", 1),
                    encoding="utf-8")
    with pytest.raises(KatalogFehler):
        lade(tmp_path)


def test_lizenz_in_einem_satz(katalog):
    from essen.datenerklaerung import lizenz_satz

    assert "ohne Quellenangabe" in lizenz_satz(katalog.lizenzen["dl-de-zero-2.0"])
    assert "Quelle und Lizenz" in lizenz_satz(katalog.lizenzen["dl-de-by-2.0"])


def test_doku_daten_erklaert_ist_aktuell(katalog):
    """docs/daten-erklaert.md nach jeder Katalogänderung neu erzeugen: uv run essen katalog --doku"""
    from essen.datenerklaerung import als_markdown as erklaert

    gespeichert = (pfade.docs() / "daten-erklaert.md").read_text(encoding="utf-8")
    ohne_datum = lambda text: [z for z in text.splitlines() if not z.startswith("Stand:")]  # noqa: E731
    assert ohne_datum(gespeichert) == ohne_datum(erklaert(katalog))
