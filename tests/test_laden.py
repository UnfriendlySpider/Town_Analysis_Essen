import hashlib
import zipfile

import pytest
from hilfen import datensatz as _ds, mini_katalog as _katalog

from essen import laden
from essen.katalog import Download


def test_datei_laden_schreibt_protokoll(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("stadtteile", Download(art="datei", url=basis + "stadtteile.geojson"))
    meldungen = []
    abruf = laden.hole(_katalog(ds), ds, fortschritt=lambda *a: meldungen.append(a))
    pfad = laden.ordner(ds) / "stadtteile.geojson"
    assert pfad.exists() and abruf.dateien == ["stadtteile.geojson"]
    assert abruf.sha256["stadtteile.geojson"] == hashlib.sha256(pfad.read_bytes()).hexdigest()
    assert laden.lese_abruf(ds).url == basis + "stadtteile.geojson"
    zeilen = (leerer_datenordner / "abrufe.csv").read_text(encoding="utf-8").splitlines()
    assert len(zeilen) == 2 and zeilen[1].split(",")[1] == "stadtteile"
    assert meldungen and meldungen[-1][2] == "Fertig"


def test_vorhandene_daten_werden_nicht_neu_geladen(server, leerer_datenordner):
    basis, zaehler = server
    ds = _ds("einmal", Download(art="datei", url=basis + "stadtteile.geojson"))
    k = _katalog(ds)
    laden.hole(k, ds)
    vorher = zaehler["anfragen"]
    laden.hole(k, ds)
    assert zaehler["anfragen"] == vorher
    laden.hole(k, ds, erzwingen=True)
    assert zaehler["anfragen"] == vorher + 1


def test_verzeichnis_ueber_index_json(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("nacht", Download(art="verzeichnis", ordner=basis + "ogd/", muster="*Nacht*GeoPackage*.zip"))
    abruf = laden.hole(_katalog(ds), ds)
    assert abruf.dateien == ["Daten_Nacht_2026_GeoPackage.zip"]
    assert abruf.stand_quelle == "2026-04-08T12:03:23"


def test_verzeichnis_mit_mehreren_treffern_fragt_nach(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("beide", Download(art="verzeichnis", ordner=basis + "ogd/", muster="*GeoPackage*.zip"))
    with pytest.raises(laden.MehrereDateien) as fehler:
        laden.hole(_katalog(ds), ds)
    assert len(fehler.value.kandidaten) == 2
    abruf = laden.hole(_katalog(ds), ds, datei="Daten_Tag_2026_GeoPackage.zip")
    assert abruf.dateien == ["Daten_Tag_2026_GeoPackage.zip"]


def test_verzeichnis_ueber_linkliste(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("dwd", Download(art="verzeichnis", ordner=basis + "liste/", muster="tageswerte_KL_01303_akt.zip"))
    assert laden.hole(_katalog(ds), ds).dateien == ["tageswerte_KL_01303_akt.zip"]


def test_kein_treffer_nennt_vorhandene_dateien(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("nichts", Download(art="verzeichnis", ordner=basis + "ogd/", muster="*TIFF*.zip"))
    with pytest.raises(laden.DownloadFehler, match="Daten_Nacht"):
        laden.hole(_katalog(ds), ds)


def test_404_gibt_verstaendliche_meldung(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("fehlt", Download(art="datei", url=basis + "gibt-es-nicht.csv"))
    with pytest.raises(laden.DownloadFehler, match="404"):
        laden.hole(_katalog(ds), ds)
    assert not laden.vorhanden(ds)


def test_api_prueft_json(server, leerer_datenordner):
    basis, _ = server
    gut = _ds("api", Download(art="api", url=basis + "api.json", datei="antwort.json"))
    assert laden.hole(_katalog(gut), gut).dateien == ["antwort.json"]
    kaputt = _ds("kaputt", Download(art="api", url=basis + "kaputt.json", datei="antwort.json"))
    with pytest.raises(laden.DownloadFehler, match="kein JSON"):
        laden.hole(_katalog(kaputt), kaputt)


def test_wfs_abfrage_fuer_das_stadtgebiet(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("wfs", Download(art="wfs", url=basis + "wfs", typname="app:baeume", format="application/json"))
    adresse = laden.wfs_adresse(ds)
    assert "REQUEST=GetFeature" in adresse and "TYPENAMES=app:baeume" in adresse and "BBOX=" in adresse
    assert laden.hole(_katalog(ds), ds).dateien == ["wfs.geojson"]


def test_manueller_datensatz_wird_nicht_geladen(leerer_datenordner):
    ds = _ds("hand", Download(art="manuell", hinweis="Von Hand laden"))
    with pytest.raises(laden.DownloadFehler, match="nicht automatisch"):
        laden.hole(_katalog(ds), ds)


def test_einlesen_und_entfernen(tmp_path, leerer_datenordner):
    ds = _ds("hand", Download(art="manuell", hinweis="Von Hand laden"))
    datei = tmp_path / "eigene.csv"
    datei.write_text("a;b\n1;2\n", encoding="utf-8")
    abruf = laden.einlesen(ds, datei)
    assert laden.vorhanden(ds) and abruf.url.startswith("von Hand")
    laden.entferne(ds)
    assert not laden.vorhanden(ds)


def test_entpacken_lehnt_pfade_ausserhalb_ab(tmp_path):
    archiv = tmp_path / "boese.zip"
    with zipfile.ZipFile(archiv, "w") as zf:
        zf.writestr("../ausserhalb.txt", "nein")
    with pytest.raises(laden.DownloadFehler, match="Unerwarteter Pfad"):
        laden.entpacke(archiv, tmp_path / "ziel")
    assert not (tmp_path / "ausserhalb.txt").exists()


def _abruf_aendern(ds, **felder):
    import dataclasses

    laden.schreibe_abruf(dataclasses.replace(laden.lese_abruf(ds), **felder))


def test_aktualitaet_datei_ueber_head(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("frisch", Download(art="datei", url=basis + "stadtteile.geojson"))
    laden.hole(_katalog(ds), ds)
    assert laden.pruefe_aktualitaet(ds).zustand == "aktuell"
    with open(laden.ordner(ds) / "stadtteile.geojson", "a", encoding="utf-8") as datei:
        datei.write(" ")
    stand = laden.pruefe_aktualitaet(ds)
    assert stand.zustand == "neu" and "Größe" in stand.text
    _abruf_aendern(ds, url=basis + "gibt-es-nicht.geojson")
    assert laden.pruefe_aktualitaet(ds).zustand == "fehler"


def test_aktualitaet_ordner_vergleicht_stand(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("nacht", Download(art="verzeichnis", ordner=basis + "ogd/", muster="*Nacht*GeoPackage*.zip"))
    laden.hole(_katalog(ds), ds)
    _abruf_aendern(ds, bytes=123)  # Größe laut index.json
    assert laden.pruefe_aktualitaet(ds).zustand == "aktuell"
    _abruf_aendern(ds, stand_quelle="2025-01-01T00:00:00")
    stand = laden.pruefe_aktualitaet(ds)
    assert stand.zustand == "neu" and "2026-04-08T12:03:23" in stand.text


def test_aktualitaet_ohne_vergleich(leerer_datenordner, tmp_path):
    hand = _ds("hand", Download(art="manuell", hinweis="Von Hand"))
    datei = tmp_path / "x.csv"
    datei.write_text("a\n1\n", encoding="utf-8")
    laden.einlesen(hand, datei)
    assert laden.pruefe_aktualitaet(hand).zustand == "hand"
    assert laden.pruefe_aktualitaet(_ds("fehlt", Download(art="datei", url="http://127.0.0.1:9/"))).zustand == "unbekannt"


def test_entpackte_ordner_nur_mit_zip(leerer_datenordner):
    basis = laden.ordner("zips")
    basis.mkdir(parents=True)
    with zipfile.ZipFile(basis / "daten.zip", "w") as zf:
        zf.writestr("a.txt", "12345")
    laden.entpackt("zips")
    (basis / "entpackt_ohne_zip").mkdir()
    gefunden = laden.entpackte_ordner("zips")
    assert [(p.name, n) for p, n in gefunden] == [("entpackt_daten", 5)]


def test_mehrere_dateien_laden(server, leerer_datenordner):
    basis, _ = server
    urls = (basis + "ogd/Daten_Nacht_2026_GeoPackage.zip", basis + "ogd/Daten_Tag_2026_GeoPackage.zip")
    ds = _ds("mehrere", Download(art="dateien", urls=urls))
    abruf = laden.hole(_katalog(ds), ds, datei="Daten_Tag_2026_GeoPackage.zip")
    assert abruf.dateien == ["Daten_Tag_2026_GeoPackage.zip"]
    assert laden.pruefe_aktualitaet(ds).zustand == "neu"  # eine Datei fehlt noch
    abruf = laden.hole(_katalog(ds), ds, datei="Daten_Nacht_2026_GeoPackage.zip")
    assert abruf.dateien == ["Daten_Nacht_2026_GeoPackage.zip", "Daten_Tag_2026_GeoPackage.zip"]
    assert set(abruf.sha256) == set(abruf.dateien) and laden.vorhanden(ds)
    assert laden.pruefe_aktualitaet(ds).zustand == "aktuell"
    assert len(laden.entpackt(ds)) == 2
    with pytest.raises(laden.DownloadFehler, match="steht nicht"):
        laden.hole(_katalog(ds), ds, datei="andere.zip")


def test_katalog_prueft_mehrere_dateien():
    ds = _ds("doppelt", Download(art="dateien", urls=("https://example.org/a.zip", "https://example.org/x/a.zip")))
    fehler, _ = _katalog(ds).pruefe()
    assert any("doppelt" in f for f in fehler)
    fehler, _ = _katalog(_ds("leer", Download(art="dateien"))).pruefe()
    assert any("urls fehlt" in f for f in fehler)


def test_mehrere_dateien_mit_eigenen_namen(server, leerer_datenordner):
    """Gleiche Adresse mit verschiedenen Abfragen (wie bei APIs): Namen kommen aus dem Katalog."""
    basis, _ = server
    ds = _ds("abfragen", Download(art="dateien", urls=(basis + "api.json?jahr=1", basis + "api.json?jahr=2"),
                                  namen=("jahr_1.json", "jahr_2.json"), format="JSON"))
    abruf = laden.hole(_katalog(ds), ds)
    assert abruf.dateien == ["jahr_1.json", "jahr_2.json"]
    ohne_namen = _ds("doppelt", Download(art="dateien", urls=(basis + "api.json?jahr=1", basis + "api.json?jahr=2")))
    fehler, _ = _katalog(ohne_namen).pruefe()
    assert any("doppelt" in f for f in fehler)
    kaputt = _ds("kaputt", Download(art="dateien", urls=(basis + "kaputt.json",), namen=("k.json",), format="JSON"))
    with pytest.raises(laden.DownloadFehler, match="kein JSON"):
        laden.hole(_katalog(kaputt), kaputt)


def test_zu_viele_anfragen_wartet_und_versucht_erneut(server, leerer_datenordner, monkeypatch):
    basis, zaehler = server
    monkeypatch.setattr(laden, "PAUSE_ZWISCHEN_DATEIEN", 0)
    ds = _ds("bremse", Download(art="dateien", urls=(basis + "bremse.json?a=1",), namen=("b.json",), format="JSON"))
    meldungen = []
    abruf = laden.hole(_katalog(ds), ds, fortschritt=lambda *a: meldungen.append(a[2]))
    assert abruf.dateien == ["b.json"] and zaehler["bremse"] == 2
    assert any("Pause" in m for m in meldungen)


def test_verzeichnis_alle_passenden_dateien(server, leerer_datenordner):
    basis, _ = server
    ds = _ds("jahre", Download(art="verzeichnis", ordner=basis + "ogd/", muster="*GeoPackage*.zip", alle=True))
    abruf = laden.hole(_katalog(ds), ds)
    assert abruf.dateien == ["Daten_Nacht_2026_GeoPackage.zip", "Daten_Tag_2026_GeoPackage.zip"]
    assert laden.vorhanden(ds) and abruf.stand_quelle == "2026-04-09T13:29:47"
    assert laden.pruefe_aktualitaet(ds).zustand == "aktuell"
    _abruf_aendern(ds, dateien=["Daten_Nacht_2026_GeoPackage.zip"])
    stand = laden.pruefe_aktualitaet(ds)
    assert stand.zustand == "neu" and "Daten_Tag_2026_GeoPackage.zip" in stand.text
