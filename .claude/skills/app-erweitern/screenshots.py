"""Screenshots aller App-Seiten mit Testdaten.

Aufruf aus dem Projektordner (braucht Playwright mit Chromium):
    uv run python .claude/skills/app-erweitern/screenshots.py [--breite 1440] [--seiten datenkatalog analysen] [--dunkel]

Startet `uv run essen app --testdaten` auf einem freien Port, besucht die Seiten und speichert PNGs nach
data_test/screenshots/. Mit `--breite 390` entsteht die Ansicht für Handys (Bilder mit Endung -390). Zeigt eine
Seite eine Ausnahme oder Fehlermeldung oder rechnet sie zu lange, steht sie am Ende in einer Liste und das Skript
endet mit Code 1. Ist das CDN gesperrt, kommt Leaflet aus einer lokalen Kopie (npm pack), die
Hintergrundkarte wird dann durch graue Kacheln ersetzt.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
import zlib
from pathlib import Path

PROJEKT = Path(__file__).resolve().parents[3]
LEAFLET = "https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/"
SEITEN = {
    "start": "/", "stadtteil": "/stadtteil", "themen": "/themen?thema=hitze-nacht",
    "themen-station": "/themen?thema=luft-station",
    "themen-kuehlorte": "/themen?thema=kuehlorte", "themen-klimatope": "/themen?thema=klimatope",
    "themen-planung": "/themen?thema=planungshinweise", "karte": "/karte", "karte-orte": "/karte?thema=hitze-nacht", "vergleich": "/vergleich",
    "zeitreihen": "/zeitreihen", "zeitreihen-stadtteil": "/zeitreihen?stadtteil=10",
    "zeitreihen-station": "/zeitreihen?stadtteil=10", "themen-raster": "/themen?thema=hitzetage-raster",
    "zeitreihen-karte": "/zeitreihen?stadtteil=10", "themen-verlauf": "/themen?thema=hitzetage-raster",
    "menue": "/", "verlauf-versiegelung": "/themen?thema=versiegelung&ansicht=verlauf",
    "verlauf-jungbaeume": "/themen?thema=jungbaeume&ansicht=verlauf",
    "verlauf-haushalte": "/themen?thema=haushalte&ansicht=verlauf",
    "begriffe": "/begriffe", "daten-erklaert": "/daten_erklaert?datensatz=klimaanalyse-nacht-raster",
    "vorbereiten": "/vorbereiten",
    "daten-laden": "/datenkatalog", "neu-berechnen": "/analysen?thema=laerm", "untersuchen": "/inspektion",
    "schnellanalyse": "/schnellanalyse",
    "originaldaten": "/originaldaten?datensatz=stadtteile",
    "originaldaten-raster": "/originaldaten?datensatz=klimaanalyse-nacht-raster", "quellen": "/quellen", "methodik": "/hintergrund",
}


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def graue_kachel() -> bytes:
    zeilen = b"".join(b"\x00" + bytes((233, 236, 231)) * 256 for _ in range(256))
    def block(art, daten):
        return struct.pack(">I", len(daten)) + art + daten + struct.pack(">I", zlib.crc32(art + daten) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + block(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 2, 0, 0, 0))
            + block(b"IDAT", zlib.compress(zeilen)) + block(b"IEND", b""))


def erreichbar(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as antwort:
            return antwort.status == 200
    except Exception:  # noqa: BLE001 - nicht erreichbar, egal warum
        return False


def leaflet_lokal(ordner: Path) -> Path | None:
    if not shutil.which("npm"):
        return None
    try:
        subprocess.run(["npm", "pack", "leaflet@1.9.3", "--silent"], cwd=ordner, check=True, capture_output=True, timeout=120)
        archiv = next(ordner.glob("leaflet-*.tgz"))
        subprocess.run(["tar", "xzf", archiv.name], cwd=ordner, check=True)
        return ordner / "package" / "dist"
    except Exception:  # noqa: BLE001 - ohne npm geht es auch ohne Leaflet-Kopie
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--breite", type=int, default=1440)
    parser.add_argument("--hoehe", type=int, default=1800)
    parser.add_argument("--seiten", nargs="*", default=list(SEITEN))
    parser.add_argument("--echt", action="store_true", help="mit den echten Daten in data/ (Bilder nach data/screenshots/)")
    parser.add_argument("--dunkel", action="store_true", help="Browser im Dunkelmodus (Bilder mit Endung -dunkel)")
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright

    ziel = PROJEKT / ("data" if args.echt else "data_test") / "screenshots"
    if not args.echt and not (PROJEKT / "data_test" / ".testdaten").exists():
        subprocess.run(["uv", "run", "essen", "testdaten"], cwd=PROJEKT, check=True)  # löscht nur Testdaten-Ordner
    ziel.mkdir(parents=True, exist_ok=True)
    port = freier_port()
    app = subprocess.Popen(["uv", "run", "essen", "app", *([] if args.echt else ["--testdaten"]), "--ohne-browser",
                            "--port", str(port)],
                           cwd=PROJEKT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    basis = f"http://localhost:{port}"
    try:
        for _ in range(60):
            if erreichbar(basis):
                break
            time.sleep(1)
        else:
            sys.exit("Die App ist nicht gestartet.")
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
            lokal = None if erreichbar(LEAFLET + "leaflet.js") else leaflet_lokal(Path(tmp))
            browser = None
            kandidaten = [None, "/opt/pw-browsers/chromium",  # passend zur Playwright-Version, Cloud-Sitzungen
                          *map(str, sorted(Path.home().glob(".cache/ms-playwright/chromium*/chrome-linux*/chrome"))),
                          *map(str, sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell*/"
                                                            "chrome-*/chrome-headless-shell")))]
            for pfad in kandidaten:  # vorhandenes Chromium nutzen, nichts nachinstallieren
                if pfad is not None and not Path(pfad).exists():
                    continue
                try:
                    browser = p.chromium.launch(**({"executable_path": pfad} if pfad else {}))
                    break
                except Exception:  # noqa: BLE001 - nächsten Browser versuchen
                    continue
            if browser is None:
                sys.exit("Kein Chromium für Playwright gefunden (uv run playwright install chromium lädt eins).")
            handy = args.breite < 600  # wie ein Handy: Touch und mobile Browserkennung (die App macht Karten niedriger)
            kontext = browser.new_context(viewport={"width": args.breite, "height": args.hoehe}, device_scale_factor=1,
                                          color_scheme="dark" if args.dunkel else "light", has_touch=handy,
                                          is_mobile=handy, **({"user_agent": "Mozilla/5.0 (Linux; Android 14) "
                                                               "AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36"}
                                                              if handy else {}))
            if lokal:
                for datei, art in (("leaflet.js", "application/javascript"), ("leaflet.css", "text/css")):
                    kontext.route(LEAFLET + datei, lambda r, d=datei, a=art: r.fulfill(path=str(lokal / d), content_type=a))
            if not erreichbar("https://sgx.geodatenzentrum.de/"):
                kachel = graue_kachel()
                kontext.route("https://sgx.geodatenzentrum.de/**", lambda r: r.fulfill(body=kachel, content_type="image/png"))
            seite = kontext.new_page()
            probleme: list[str] = []
            for name in args.seiten:
                seite.goto(basis + SEITEN[name])
                seite.wait_for_selector('[data-testid="stApp"]', timeout=60000)
                seite.wait_for_timeout(1500)
                # Warten, bis Streamlit fertig gerechnet hat (die Anzeige „Running…“ verschwindet)
                try:
                    seite.wait_for_function(
                        "!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=90000)
                except Exception:  # noqa: BLE001 - Zeitüberschreitung wird unten gemeldet
                    probleme.append(f"{name}: rechnet nach 90 s noch (Bild zeigt einen Zwischenstand)")
                seite.wait_for_timeout(int(os.environ.get("WARTEN_MS", "2500")))
                if name == "zeitreihen-station":  # Station Bredeney einblenden (unter „Vergleichen mit …“)
                    seite.locator('[data-testid="stExpander"] summary', has_text="Vergleichen mit").first.click()
                    seite.locator('[data-testid="stCheckbox"]', has_text="Messstation Bredeney").first.click()
                    seite.wait_for_timeout(int(os.environ.get("WARTEN_MS", "2500")))
                if name == "themen-verlauf":  # Ansicht „Verlauf über die Jahre“ wählen
                    seite.get_by_text("Verlauf über die Jahre", exact=True).first.click()
                    seite.wait_for_timeout(int(os.environ.get("WARTEN_MS", "2500")))
                if name == "zeitreihen-karte":  # zur Karte über die Jahre blättern
                    seite.get_by_text("Auf der Karte", exact=True).first.evaluate("e => e.scrollIntoView()")
                    seite.wait_for_timeout(800)
                if name == "menue":  # Menü oben rechts öffnen (dort wird hell/dunkel umgeschaltet)
                    seite.locator('[data-testid="stMainMenu"]').first.click()
                    seite.wait_for_timeout(800)
                if seite.locator('[data-testid="stException"]').count():
                    probleme.append(f"{name}: Ausnahme (Traceback) auf der Seite")
                fehler = seite.locator('[data-testid="stAlertContentError"]')
                if fehler.count():
                    probleme.append(f"{name}: Fehlermeldung „{fehler.first.inner_text()[:120]}“")
                endung = ("-dunkel" if args.dunkel else "") + (f"-{args.breite}" if args.breite != 1440 else "")
                pfad = ziel / f"{name}{endung}.png"
                seite.screenshot(path=str(pfad))
                print(pfad.relative_to(PROJEKT))
            browser.close()
            if probleme:
                print("\nAuffällig:\n- " + "\n- ".join(probleme), file=sys.stderr)
                sys.exit(1)
    finally:
        try:
            os.killpg(app.pid, signal.SIGTERM)  # ganze Prozessgruppe: uv, Python und Streamlit
            app.wait(timeout=20)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            os.killpg(app.pid, signal.SIGKILL)


if __name__ == "__main__":
    main()
