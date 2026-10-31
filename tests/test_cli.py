"""Die Befehle der Kommandozeile mit Testdaten und dem lokalen Testserver (ohne Internet)."""

import os
import shutil

import pytest
import yaml
from hilfen import datensatz, mini_katalog

from essen import cli, laden, pfade
from essen.katalog import Dienst, Download


def _aufruf(argumente, capsys) -> tuple[int | str | None, str]:
    """Führt einen Befehl aus; gibt (Exit-Code oder None, Ausgabe) zurück."""
    try:
        cli.main(argumente)
        code = None
    except SystemExit as ende:
        code = ende.code
    return code, capsys.readouterr().out


@pytest.fixture
def mini(monkeypatch):
    """Ersetzt den Katalog der Kommandozeile durch einen kleinen Katalog mit den übergebenen Datensätzen."""
    def setzen(*datensaetze):
        katalog = mini_katalog(*datensaetze)
        monkeypatch.setattr(cli, "_katalog", lambda: katalog)
        return katalog
    return setzen


@pytest.fixture
def docs_ordner(tmp_path, monkeypatch):
    """docs/ in einen temporären Ordner umlenken, damit Tests die echte Doku nicht überschreiben."""
    ziel = tmp_path / "docs"
    ziel.mkdir()
    monkeypatch.setattr(pfade, "docs", lambda: ziel)
    return ziel


# ------------------------------------------------------------------- Katalog

def test_ohne_befehl_zeigt_hilfe(capsys):
    code, text = _aufruf([], capsys)
    assert code is None and "Beispiele:" in text and "katalog" in text


def test_katalog_liste_nach_thema(mit_testdaten, capsys):
    code, text = _aufruf(["katalog", "--thema", "klima"], capsys)
    assert code is None
    assert "klimaanalyse-nacht-raster" in text and "●" in text  # in den Testdaten geladen
    assert "stadtteile " not in text  # anderes Thema


def test_katalog_suche_und_domains(capsys):
    _, text = _aufruf(["katalog", "Starkregen"], capsys)
    assert "starkregen-essen" in text and "zensus-2022-gitter" not in text
    _, text = _aufruf(["katalog", "--domains"], capsys)
    assert "opendata.essen.de" in text.splitlines()


def test_katalog_doku_schreibt_beide_seiten(docs_ordner, capsys):
    from essen import datenerklaerung, katalog as kat

    code, text = _aufruf(["katalog", "--doku"], capsys)
    assert code is None and text.count("Geschrieben:") == 2
    katalog = kat.lade()
    assert (docs_ordner / "datenquellen.md").read_text(encoding="utf-8") == kat.als_markdown(katalog)
    assert (docs_ordner / "daten-erklaert.md").read_text(encoding="utf-8") == datenerklaerung.als_markdown(katalog)


def test_info_nennt_lizenz_abruf_und_quellenangabe(mit_testdaten, capsys):
    code, text = _aufruf(["info", "stadtteile"], capsys)
    assert code is None
    for teil in ("Lizenz:", "Download:", "Geladen am", "Quellenangabe:"):
        assert teil in text, teil


# ------------------------------------------------------------- Laden, Status

def test_laden_ueber_den_testserver(server, leerer_datenordner, mini, capsys):
    basis, _ = server
    mini(datensatz("stadtteile", Download(art="datei", url=basis + "stadtteile.geojson")))
    code, text = _aufruf(["laden", "stadtteile"], capsys)
    assert code == 0 and "fertig: stadtteile.geojson" in text
    code, text = _aufruf(["laden", "stadtteile"], capsys)
    assert code == 0 and "schon geladen" in text and "--neu" in text
    code, text = _aufruf(["laden", "stadtteile", "--neu"], capsys)
    assert code == 0 and "fertig" in text


def test_laden_meldet_fehler_mit_exit_code(server, leerer_datenordner, mini, capsys):
    basis, _ = server
    mini(datensatz("beide", Download(art="verzeichnis", ordner=basis + "ogd/", muster="*GeoPackage*.zip")),
         datensatz("fehlt", Download(art="datei", url=basis + "gibt-es-nicht.csv")))
    code, text = _aufruf(["laden", "beide"], capsys)
    assert code == 1 and "Daten_Nacht_2026_GeoPackage.zip" in text and "--datei NAME" in text
    code, text = _aufruf(["laden", "fehlt"], capsys)
    assert code == 1 and "404" in text
    code, text = _aufruf(["laden", "gibt-es-gar-nicht"], capsys)
    assert code == 1 and "gibt-es-gar-nicht" in text
    code, text = _aufruf(["laden", "beide", "--datei", "Daten_Tag_2026_GeoPackage.zip"], capsys)
    assert code == 0 and "fertig: Daten_Tag_2026_GeoPackage.zip" in text


def test_grosser_download_fragt_nach(server, leerer_datenordner, mini, monkeypatch, capsys):
    basis, _ = server
    mini(datensatz("gross", Download(art="datei", url=basis + "stadtteile.geojson", groesse_mb=800)))

    def ohne_terminal(_frage):
        raise EOFError

    monkeypatch.setattr("builtins.input", ohne_terminal)
    code, text = _aufruf(["laden", "gross"], capsys)
    assert code == 0 and "nicht geladen" in text and not laden.vorhanden("gross")
    code, text = _aufruf(["laden", "gross", "--ja"], capsys)
    assert code == 0 and laden.vorhanden("gross")


def test_einlesen_und_loeschen(tmp_path, leerer_datenordner, mini, capsys):
    mini(datensatz("hand", Download(art="manuell", hinweis="Von Hand laden")))
    datei = tmp_path / "export.csv"
    datei.write_text("a;b\n1;2\n", encoding="utf-8")
    code, text = _aufruf(["einlesen", "hand", str(datei)], capsys)
    assert code is None and "export.csv übernommen" in text and laden.vorhanden("hand")
    code, text = _aufruf(["loeschen", "hand"], capsys)
    assert code is None and "gelöscht" in text and not laden.vorhanden("hand")


def test_status_ohne_und_mit_daten(leerer_datenordner, mit_testdaten, monkeypatch, capsys):
    monkeypatch.setenv("ESSEN_DATEN", str(leerer_datenordner))
    _, text = _aufruf(["status"], capsys)
    assert "Noch nichts geladen" in text
    monkeypatch.setenv("ESSEN_DATEN", str(mit_testdaten["ordner"]))
    _, text = _aufruf(["status"], capsys)
    assert "(TESTDATEN)" in text and "stadtteile" in text and "Zusammen" in text


def test_aktualisieren(server, leerer_datenordner, mini, capsys):
    basis, _ = server
    ds = datensatz("frisch", Download(art="datei", url=basis + "stadtteile.geojson"))
    mini(ds)
    _, text = _aufruf(["aktualisieren"], capsys)
    assert "Noch nichts geladen" in text
    _aufruf(["laden", "frisch"], capsys)
    _, text = _aufruf(["aktualisieren"], capsys)
    assert "frisch" in text and "aktuell" in text and "Kein neuerer Stand" in text


def test_aktualisieren_meldet_neuen_stand(server, leerer_datenordner, mini, capsys):
    basis, _ = server
    urls = (basis + "ogd/Daten_Nacht_2026_GeoPackage.zip", basis + "ogd/Daten_Tag_2026_GeoPackage.zip")
    mini(datensatz("mehrere", Download(art="dateien", urls=urls)))
    _aufruf(["laden", "mehrere", "--datei", "Daten_Tag_2026_GeoPackage.zip"], capsys)
    _, text = _aufruf(["aktualisieren", "mehrere"], capsys)
    assert "! mehrere" in text and "uv run essen laden --neu mehrere" in text


# -------------------------------------------------- Inspizieren, Dienste

def test_inspizieren_datensatz_und_datei(kopie_testdaten, tmp_path, capsys):
    code, text = _aufruf(["inspizieren", "stadtteile"], capsys)
    assert code is None and "Bericht gespeichert" in text
    assert any(pfade.inspektion().glob("stadtteile*"))
    datei = next(laden.ordner("stadtteile").glob("*.geojson"))
    kopie = shutil.copy(datei, tmp_path / "eigene.geojson")
    code, text = _aufruf(["inspizieren", str(kopie)], capsys)
    assert code is None and "Bericht gespeichert" in text
    code, _ = _aufruf(["inspizieren", str(tmp_path / "gibt-es-nicht.gpkg")], capsys)
    assert "Weder Datensatz noch Datei" in str(code)


def test_dienst_listet_ebenen(server, leerer_datenordner, mini, capsys):
    basis, _ = server
    mini(datensatz("mit-dienst", Download(art="dienst"), dienste=(Dienst(art="wms", url=basis + "wms"),)),
         datensatz("ohne-dienst", Download(art="manuell", hinweis="Von Hand")))
    code, text = _aufruf(["dienst", "mit-dienst"], capsys)
    assert code is None and "nacht" in text and "Klimaanalysekarte Nacht" in text
    code, _ = _aufruf(["dienst", "ohne-dienst"], capsys)
    assert "keinen Kartendienst" in str(code)


# ---------------------------------------------------------------- Analysen

def test_analyse_mit_parameter_und_export(kopie_testdaten, capsys):
    code, text = _aufruf(["analyse", "starkregen", "-p", "gewaesser=mitzaehlen", "--export"], capsys)
    assert code is None
    assert "Höchste Werte" in text and "Gespeichert in" in text and "HTML-Seite:" in text
    assert (pfade.export() / "starkregen.html").exists()
    from essen.analysen.basis import Ergebnis

    assert Ergebnis.laden("starkregen").parameter["gewaesser"] == "mitzaehlen"


def test_analyse_liste_nennt_fehlende_daten(leerer_datenordner, capsys):
    _, text = _aufruf(["analyse"], capsys)
    assert "hitze-nacht" in text and "es fehlt:" in text and "-p " in text


def test_analyse_station_ohne_kartenseite(kopie_testdaten, capsys):
    code, text = _aufruf(["analyse", "hitzetage-station", "--export"], capsys)
    assert code is None and "nur vollständige Jahre" in text and "keine Kartenseite" in text


def test_schnellanalyse(kopie_testdaten, capsys):
    code, text = _aufruf(["schnell", "klimaanalyse-nacht-vektor"], capsys)
    assert code is None and "Gespeichert in" in text and "stadtteil" in text


def test_vorbereiten_rechnet_alles_und_dann_nichts_mehr(kopie_testdaten, capsys):
    shutil.rmtree(pfade.verarbeitet(), ignore_errors=True)
    code, text = _aufruf(["vorbereiten", "--ja"], capsys)
    assert code is None and "Zu berechnen:" in text and "ohne Fehler" in text
    code, text = _aufruf(["vorbereiten"], capsys)
    assert code is None and "Alles vorbereitet" in text


def test_vorbereiten_fragt_vor_grossem_download(leerer_datenordner, monkeypatch, capsys):
    from essen import vorbereiten

    def nicht_laden(*args, **kwargs):
        raise AssertionError("Ohne Zustimmung darf nichts geladen werden")

    monkeypatch.setattr(vorbereiten, "ausfuehren", nicht_laden)
    monkeypatch.setattr("builtins.input", lambda _frage: "n")
    code, text = _aufruf(["vorbereiten"], capsys)
    assert code is None and "Zu laden:" in text and "Nichts geladen." in text


def test_pruefen_ergebnisse_festschreiben_und_abweichung(kopie_testdaten, docs_ordner, capsys):
    code, text = _aufruf(["pruefen-ergebnisse", "--festschreiben", "versiegelung"], capsys)
    assert code is None and "Referenzwerte geschrieben" in text
    code, text = _aufruf(["pruefen-ergebnisse", "versiegelung"], capsys)
    assert code is None and "gleich" in text and "stimmen mit den Referenzwerten überein" in text

    datei = docs_ordner / "referenzwerte.yaml"
    daten = yaml.safe_load(datei.read_text(encoding="utf-8"))
    daten["analysen"]["versiegelung"]["kennzahl_stadt"] += 5
    datei.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    code, text = _aufruf(["pruefen-ergebnisse", "versiegelung"], capsys)
    assert code == 1 and "abweichend" in text and "--festschreiben ID" in text


# ------------------------------------------------------------ Testdaten, App

def test_testdaten_in_eigenen_ordner(tmp_path, monkeypatch, capsys):
    from essen import testdaten

    echt = testdaten.erzeuge
    monkeypatch.setattr(testdaten, "erzeuge", lambda ziel: echt(ziel, zellgroesse=100.0, anzahl_gebiete=4, seed=1))
    monkeypatch.setenv("ESSEN_DATEN", str(tmp_path / "vorher"))  # erzeuge setzt ESSEN_DATEN; so wird es zurückgesetzt
    ziel = tmp_path / "td"
    code, text = _aufruf(["testdaten", "--ziel", str(ziel)], capsys)
    assert code is None and "4 Testgebiete" in text
    assert (ziel / pfade.TESTDATEN_MARKE).exists() and (ziel / "raw" / "stadtteile").is_dir()


def test_app_startet_nur_lokal_und_ohne_telemetrie(monkeypatch, capsys):
    aufgerufen = {}
    monkeypatch.chdir(pfade.projekt())  # der Befehl wechselt in den Projektordner; danach zurück
    monkeypatch.setenv("ESSEN_DATEN", "data")
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(os, "execv", lambda programm, befehl: aufgerufen.update(befehl=befehl))
    code, text = _aufruf(["app", "--ohne-browser", "--port", "8642", "--testdaten"], capsys)
    befehl = aufgerufen["befehl"]
    assert code is None and "http://localhost:8642" in text
    werte = dict(zip(befehl[5::2], befehl[6::2], strict=True))
    assert werte["--server.address"] == "localhost" and werte["--server.port"] == "8642"
    assert werte["--browser.gatherUsageStats"] == "false" and werte["--server.headless"] == "true"
    assert os.environ["ESSEN_DATEN"] == pfade.TESTDATEN_ORDNER
