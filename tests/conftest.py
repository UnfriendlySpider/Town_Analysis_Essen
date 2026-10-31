"""Gemeinsame Vorbereitung: erfundene Testdaten in einem temporären Datenordner.

Die Tests greifen nie auf das Internet zu. Downloads werden gegen einen kleinen lokalen
HTTP-Server geprüft (Fixture `server`, Kataloge dazu in hilfen.py).
"""

import functools
import http.server
import json
import threading
import zipfile

import pytest

from essen import katalog as kat, testdaten


@pytest.fixture(scope="session")
def katalog():
    return kat.lade()


@pytest.fixture(scope="session")
def testdaten_ordner(tmp_path_factory):
    ordner = tmp_path_factory.mktemp("daten")
    import os

    alt = os.environ.get("ESSEN_DATEN")
    ergebnis = testdaten.erzeuge(ordner, zellgroesse=50.0, anzahl_gebiete=12, seed=3)
    if alt is not None:
        os.environ["ESSEN_DATEN"] = alt
    return ergebnis


@pytest.fixture
def mit_testdaten(testdaten_ordner, monkeypatch):
    monkeypatch.setenv("ESSEN_DATEN", str(testdaten_ordner["ordner"]))
    return testdaten_ordner


@pytest.fixture
def leerer_datenordner(tmp_path, monkeypatch):
    ordner = tmp_path / "daten"
    monkeypatch.setenv("ESSEN_DATEN", str(ordner))
    return ordner


@pytest.fixture
def kopie_testdaten(testdaten_ordner, tmp_path, monkeypatch):
    """Eigene Kopie der Testdaten, die ein Test verändern darf."""
    import shutil

    ziel = tmp_path / "kopie"
    shutil.copytree(testdaten_ordner["ordner"], ziel)
    monkeypatch.setenv("ESSEN_DATEN", str(ziel))
    return ziel


WMS_CAPABILITIES = """<?xml version="1.0"?>
<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms"><Capability><Layer><Title>Wurzel</Title>
<Layer><Name>nacht</Name><Title>Klimaanalysekarte Nacht</Title></Layer>
</Layer></Capability></WMS_Capabilities>"""


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """Kleiner HTTP-Server mit Dateien wie bei den echten Anbietern."""
    wurzel = tmp_path_factory.mktemp("server")
    (wurzel / "stadtteile.geojson").write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    ordner = wurzel / "ogd"
    ordner.mkdir()
    for name in ("Daten_Nacht_2026_GeoPackage.zip", "Daten_Tag_2026_GeoPackage.zip"):
        with zipfile.ZipFile(ordner / name, "w") as zf:
            zf.writestr("inhalt.txt", name)
    (ordner / "index.json").write_text(json.dumps({
        "metafiles": [{"name": "meta.zip", "size": "10", "timestamp": "2026-04-14T10:28:53"}],
        "datasets": [{"name": "daten", "title": "Daten", "files": [
            {"name": "Daten_Nacht_2026_GeoPackage.zip", "size": "123", "timestamp": "2026-04-08T12:03:23"},
            {"name": "Daten_Tag_2026_GeoPackage.zip", "size": "456", "timestamp": "2026-04-09T13:29:47"},
        ]}]}), encoding="utf-8")
    liste = wurzel / "liste"
    liste.mkdir()
    (liste / "tageswerte_KL_01303_akt.zip").write_bytes(b"PK-Test")
    (wurzel / "api.json").write_text('[{"station": "A"}]', encoding="utf-8")
    (wurzel / "kaputt.json").write_text("<html>Fehler</html>", encoding="utf-8")
    (wurzel / "wfs").write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    (wurzel / "wms").write_text(WMS_CAPABILITIES, encoding="utf-8")
    zaehler = {"anfragen": 0}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            zaehler["anfragen"] += 1
            if self.path.startswith("/bremse.json"):
                zaehler["bremse"] = zaehler.get("bremse", 0) + 1
                if zaehler["bremse"] == 1:
                    self.send_response(429)
                    self.send_header("Retry-After", "0")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.path = "/api.json"
            super().do_GET()

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(wurzel)))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/", zaehler
    httpd.shutdown()
