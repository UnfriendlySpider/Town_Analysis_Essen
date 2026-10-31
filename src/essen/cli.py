"""Kommandozeile: `uv run essen <befehl>`. Ohne Befehl zeigt sie eine Übersicht.

Jeder Befehl ruft nur Funktionen aus dem Paket auf; die App nutzt dieselben Funktionen.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from . import pfade

BEISPIELE = """\
Beispiele:
  uv run essen app                         lokale App im Browser öffnen
  uv run essen katalog --thema klima       Datensätze zum Thema Klima
  uv run essen laden stadtteile klimaanalyse-nacht-raster
  uv run essen inspizieren klimaanalyse-nacht-raster
  uv run essen analyse hitze-nacht --export
  uv run essen testdaten                   erfundene Testdaten nach data_test/
  uv run essen --testdaten analyse hitze-nacht
"""


def _katalog():
    from .katalog import KatalogFehler, lade

    try:
        return lade()
    except KatalogFehler as fehler:
        sys.exit(str(fehler))


def _kurztext(text: str, breite: int = 100) -> str:
    return textwrap.shorten(text, width=breite, placeholder=" …")


# -------------------------------------------------------------------- Befehle

def befehl_katalog(args) -> None:
    from .katalog import THEMEN, als_markdown

    katalog = _katalog()
    if args.pruefen:
        fehler, warnungen = katalog.pruefe()
        for w in warnungen:
            print("Warnung:", w)
        for f in fehler:
            print("FEHLER:", f)
        print(f"{len(katalog.quellen)} Quellen, {len(katalog.datensaetze)} Datensätze, "
              f"{len(fehler)} Fehler, {len(warnungen)} Warnungen")
        sys.exit(1 if fehler else 0)
    if args.doku:
        from . import datenerklaerung

        for name, inhalt in (("datenquellen.md", als_markdown(katalog)),
                             ("daten-erklaert.md", datenerklaerung.als_markdown(katalog))):
            ziel = pfade.docs() / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding="utf-8")
            print("Geschrieben:", pfade.relativ(ziel))
        return
    if args.domains:
        print("\n".join(katalog.domains()))
        return
    from . import laden
    from .text import megabyte

    liste = katalog.filter(themen=[args.thema] if args.thema else None, ebene=args.ebene, nur_ladbar=args.ladbar,
                           suche=" ".join(args.suche) if args.suche else None)
    for thema, titel in THEMEN.items():
        gruppe = [ds for ds in liste if ds.themen[0] == thema]
        if not gruppe:
            continue
        print(f"\n{titel}")
        for ds in gruppe:
            zeichen = "●" if laden.vorhanden(ds) else ("○" if ds.ladbar else "·")
            groesse = f", {megabyte(ds.download.groesse_mb)}" if ds.download.groesse_mb else ""
            print(f"  {zeichen} {ds.id:32s} {_kurztext(ds.titel, 60)} [{katalog.lizenz_von(ds).kurz}{groesse}]")
    print("\n● geladen   ○ automatisch ladbar   · von Hand oder nur Kartendienst")
    print("Mehr zu einem Datensatz: uv run essen info ID")


def befehl_info(args) -> None:
    from . import laden
    from .katalog import STATUS, quellenangabe
    from .text import groesse

    katalog = _katalog()
    ds = katalog.datensatz(args.id)
    quelle = katalog.quelle_von(ds)
    lizenz = katalog.lizenz_von(ds)
    print(ds.titel)
    print("=" * len(ds.titel))
    print(textwrap.fill(ds.beschreibung, 100))
    print(f"\nQuelle:     {quelle.name}")
    print(f"Format:     {ds.format} · {ds.raumbezug} · Stand {ds.stand}")
    print(f"Lizenz:     {lizenz.kurz} – {lizenz.hinweis}")
    print(f"Seite:      {ds.seite}")
    print(f"Download:   {ds.download.art} · {STATUS[ds.status]}" + (f" ({ds.geprueft})" if ds.geprueft else ""))
    if ds.download.hinweis:
        print(f"            {ds.download.hinweis}")
    for dienst in ds.dienste:
        print(f"Dienst:     {dienst.art.upper()} {dienst.url}")
    for hinweis in ds.hinweise:
        print(f"Hinweis:    {textwrap.fill(hinweis, 88, subsequent_indent=' ' * 12, break_on_hyphens=False)}")
    abruf = laden.lese_abruf(ds)
    if abruf:
        print(f"\nGeladen am {abruf.datum}: {', '.join(abruf.dateien)} ({groesse(abruf.bytes)})")
    print("\nQuellenangabe:", quellenangabe(katalog, ds, abruf.datum if abruf else None))


def _fortschritt_terminal():
    from .text import groesse

    def melde(geladen, gesamt, text):
        if gesamt:
            anteil = geladen / gesamt
            balken = "█" * int(anteil * 30) + "░" * (30 - int(anteil * 30))
            print(f"\r  {balken} {groesse(geladen)} von {groesse(gesamt)}   ", end="", flush=True)
        elif geladen:
            print(f"\r  {groesse(geladen)} geladen   ", end="", flush=True)
        else:
            print(f"  {text}")
    return melde


def befehl_laden(args) -> None:
    from . import laden
    from .text import groesse

    katalog = _katalog()
    fehler = 0
    for kennung in args.ids:
        try:
            ds = katalog.datensatz(kennung)
        except KeyError as e:
            print(e.args[0]); fehler += 1; continue
        if laden.vorhanden(ds) and not args.neu:
            abruf = laden.lese_abruf(ds)
            print(f"{ds.id}: schon geladen am {abruf.datum}. Neu laden mit --neu.")
            continue
        if ds.gross and not args.ja:
            try:
                antwort = input(f"{ds.id} ist rund {ds.download.groesse_mb:g} MB groß. Laden? [j/N] ")
            except EOFError:  # ohne Terminal, z. B. in Agenten-Sitzungen
                antwort = ""
            if antwort.strip().lower() not in ("j", "ja", "y"):
                print(f"{ds.id}: nicht geladen. Mit --ja ohne Nachfrage laden.")
                continue
        print(f"{ds.id}: {ds.titel}")
        try:
            abruf = laden.hole(katalog, ds, fortschritt=_fortschritt_terminal(), erzwingen=args.neu, datei=args.datei)
            namen = ", ".join(abruf.dateien) if len(abruf.dateien) <= 5 else f"{len(abruf.dateien)} Dateien"
            print(f"\r  fertig: {namen}, {groesse(abruf.bytes)}" + " " * 30)
        except laden.MehrereDateien as e:
            print(f"\n  {e}")
            for k in e.kandidaten:
                print(f"    {k.name}  {groesse(k.groesse) if k.groesse else ''}")
            print(f"  Auswahl mit: uv run essen laden {ds.id} --datei NAME")
            fehler += 1
        except laden.DownloadFehler as e:
            print(f"\n  {e}")
            fehler += 1
    sys.exit(1 if fehler else 0)


def befehl_einlesen(args) -> None:
    from . import laden
    from .text import groesse

    katalog = _katalog()
    ds = katalog.datensatz(args.id)
    abruf = laden.einlesen(ds, Path(args.datei))
    print(f"{ds.id}: {abruf.dateien[0]} übernommen ({groesse(abruf.bytes)}).")


def befehl_loeschen(args) -> None:
    from . import laden

    katalog = _katalog()
    for kennung in args.ids:
        ds = katalog.datensatz(kennung)
        laden.entferne(ds)
        print(f"{ds.id}: gelöscht.")


def befehl_status(args) -> None:
    from . import laden
    from .text import groesse

    katalog = _katalog()
    zeilen = [z for z in laden.status_tabelle(katalog) if z["geladen"]]
    print(f"Datenordner: {pfade.relativ(pfade.daten())}" + ("  (TESTDATEN)" if pfade.ist_testdaten() else ""))
    if not zeilen:
        print("Noch nichts geladen. Start: uv run essen laden stadtteile")
        return
    for z in zeilen:
        print(f"  {z['id']:32s} {z['abgerufen']}  {groesse(z['bytes']):>10s}{'  Testdaten' if z['testdaten'] else ''}")
    print(f"Zusammen {groesse(sum(z['bytes'] for z in zeilen))}")
    entpackt = [(z["id"], pfad, anzahl) for z in zeilen for pfad, anzahl in laden.entpackte_ordner(z["id"])]
    if not entpackt:
        return
    gesamt = sum(anzahl for *_, anzahl in entpackt)
    if not args.aufraeumen:
        print(f"Davon entpackt (aus den ZIPs neu erzeugbar): {groesse(gesamt)}. Freigeben: uv run essen status --aufraeumen")
        return
    print(f"\nEntpackte Ordner, die sich aus dem ZIP neu erzeugen lassen ({groesse(gesamt)}):")
    for kennung, pfad, anzahl in entpackt:
        print(f"  {kennung:32s} {pfad.name:50s} {groesse(anzahl):>10s}")
    if not args.ja and input("Alle löschen? Die nächste Analyse entpackt sie bei Bedarf neu. [j/N] ").strip().lower() not in ("j", "ja"):
        print("Nichts gelöscht.")
        return
    for _, pfad, _ in entpackt:
        shutil.rmtree(pfad)
    print(f"Gelöscht, {groesse(gesamt)} frei.")


def befehl_aktualisieren(args) -> None:
    from . import laden

    katalog = _katalog()
    if args.ids:
        auswahl = [katalog.datensatz(k) for k in args.ids]
    else:
        auswahl = [ds for ds in katalog.datensaetze.values() if laden.vorhanden(ds)]
    if not auswahl:
        print("Noch nichts geladen.")
        return
    zeichen = {"aktuell": "  ", "neu": "! ", "fehler": "? ", "unbekannt": "  ", "abfrage": "  ", "hand": "  "}
    s = laden.sitzung()
    ergebnisse = []
    for ds in auswahl:
        stand = laden.pruefe_aktualitaet(ds, s)
        ergebnisse.append(stand)
        print(f"{zeichen[stand.zustand]}{ds.id:32s} {stand.zustand:9s} {stand.text}")
    neu = [e.datensatz for e in ergebnisse if e.zustand == "neu"]
    if neu:
        print(f"\nNeuer Stand verfügbar für {len(neu)} Datensätze. Laden mit: uv run essen laden --neu {' '.join(neu)}")
        print("Danach Zuordnungen und Ergebnisse prüfen (Kodierung kann sich geändert haben, E-009).")
    else:
        print("\nKein neuerer Stand gefunden.")


def befehl_inspizieren(args) -> None:
    from .inspizieren import inspiziere_datensatz, inspiziere_pfad

    katalog = _katalog()
    if args.ziel in katalog.datensaetze:
        bericht = inspiziere_datensatz(katalog, args.ziel)
        name = args.ziel
    else:
        pfad = Path(args.ziel)
        if not pfad.exists():
            sys.exit(f"Weder Datensatz noch Datei: {args.ziel}")
        bericht = inspiziere_pfad(pfad)
        name = pfad.stem
    text = bericht.als_markdown()
    print(text if len(text) < 12000 or args.alles else text[:12000] + "\n… (gekürzt, ganzer Bericht in der Datei)")
    ziel = bericht.speichern(name)
    print(f"\nBericht gespeichert: {pfade.relativ(ziel)}")


def befehl_dienst(args) -> None:
    from . import dienste

    katalog = _katalog()
    ds = katalog.datensatz(args.id)
    if not ds.dienste:
        sys.exit(f"{ds.id} hat keinen Kartendienst.")
    for dienst in ds.dienste:
        if dienst.art not in ("wms", "wfs"):
            continue
        print(f"{dienst.art.upper()} {dienst.url}")
        for ebene in dienste.ebenen(dienst.url, dienst.art):
            print(f"  {ebene.name:40s} {ebene.titel}")


def befehl_analyse(args) -> None:
    from . import analysen, bericht
    from .geo import DatenFehlen
    from .text import zahl

    katalog = _katalog()
    if not args.id:
        for analyse in analysen.ALLE.values():
            fehlend = analyse.fehlende_daten()
            stand = "bereit" if not fehlend else "es fehlt: " + ", ".join(fehlend)
            print(f"  {analyse.id:22s} {analyse.titel} ({stand})")
            for p in analyse.parameter:
                print(f"      {'-p ' + p.name + '=' + str(p.standard):34s} {p.titel}")
        return
    parameter = {}
    for eintrag in args.p or []:
        name, _, wert = eintrag.partition("=")
        parameter[name.strip()] = wert.strip()
    try:
        ergebnis = analysen.ausfuehren(katalog, args.id, parameter)
    except DatenFehlen as e:
        sys.exit(str(e))
    except analysen.hitze_nacht.ZuordnungFehlt as e:
        sys.exit("\n" + textwrap.fill(str(e), 100, break_on_hyphens=False, break_long_words=False))
    for hinweis in ergebnis.hinweise:
        print("Hinweis:", hinweis)
    analyse = analysen.hole(args.id)
    if analyse.kennzahl in ergebnis.tabelle.columns:
        name = next((s.feld for s in analyse.spalten if s.art == "text"), None)
        tabelle = ergebnis.tabelle.dropna(subset=[analyse.kennzahl])
        zusatz = ""
        if "vollstaendig" in tabelle.columns:  # z. B. das laufende Jahr nicht in die Rangliste
            tabelle, zusatz = tabelle[tabelle["vollstaendig"].astype(bool)], ", nur vollständige Jahre"
        spitze = tabelle.nlargest(5, analyse.kennzahl)
        print(f"Höchste Werte ({analyse.kennzahl_titel}{zusatz}):")
        stellen = analyse.stellen
        for _, zeile in spitze.iterrows():
            print(f"  {str(zeile[name]) if name else '':28s} {zahl(zeile[analyse.kennzahl], stellen):>8s} {analyse.einheit}")
    print(f"Gespeichert in {pfade.relativ(pfade.verarbeitet(args.id))}")
    if args.export:
        if bericht.hat_seite(analyse, ergebnis):
            ziel = bericht.schreibe(katalog, analyse, ergebnis)
            print(f"HTML-Seite: {pfade.relativ(ziel)}")
        else:
            print("Für diese Analyse gibt es keine Kartenseite; die Tabelle liegt als CSV im Ergebnisordner.")


def befehl_vorbereiten(args) -> None:
    from . import vorbereiten
    from .text import zahl

    katalog = _katalog()
    plan = vorbereiten.plan(katalog)
    if plan.fertig:
        print("Alles vorbereitet: Alle Daten sind geladen und alle Themen berechnet.")
        return
    if plan.fehlend:
        print(f"Zu laden: {len(plan.fehlend)} Datensätze, zusammen etwa {zahl(plan.download_mb / 1000, 1)} GB "
              f"(frei: {zahl(plan.frei_gb, 0)} GB): {', '.join(plan.fehlend)}")
    if plan.zu_rechnen:
        print(f"Zu berechnen: {', '.join(plan.zu_rechnen)}")
    gross = plan.download_mb > 500 and not args.ja
    if gross and input("Fortfahren? [j/N] ").strip().lower() not in ("j", "ja"):
        print("Nichts geladen.")
        return
    schritte = vorbereiten.ausfuehren(katalog, melde=print, fortschritt=_fortschritt_terminal())
    fehler = [s for s in schritte if not s.ok]
    for s in fehler:
        print(f"  ! {s.text}")
    print(f"\nFertig: {len(schritte) - len(fehler)} von {len(schritte)} Schritten ohne Fehler.")
    if fehler:
        sys.exit(1)


def befehl_pruefen_ergebnisse(args) -> None:
    from . import waechter
    from .text import zahl

    katalog = _katalog()
    if args.festschreiben:
        waechter.festschreiben(katalog, args.ids or None)
        print(f"Referenzwerte geschrieben: {pfade.relativ(waechter.referenzdatei())}")
        return
    ergebnisse = waechter.pruefe(katalog, args.ids or None, melde=lambda m: None)
    zeichen = {"gleich": "  ", "abweichend": "! ", "neu": "+ ", "daten_fehlen": "? ", "fehler": "! ", "testdaten": "  "}
    for e in ergebnisse:
        werte = f"{zahl(e.referenz, 2) if e.referenz is not None else '–':>8s} → {zahl(e.neu, 2) if e.neu is not None else '–':>8s}"
        print(f"{zeichen[e.zustand]}{e.analyse_id:22s} {e.zustand:12s} {werte}  {e.text}")
    auffaellig = [e for e in ergebnisse if e.zustand in ("abweichend", "fehler")]
    if auffaellig:
        print(f"\n{len(auffaellig)} Analysen weichen ab oder scheitern. Ursache klären (neuer Datenstand? Zuordnung?), "
              "dann bewusst neu festschreiben: uv run essen pruefen-ergebnisse --festschreiben ID")
        sys.exit(1)
    print("\nAlle geprüften Ergebnisse stimmen mit den Referenzwerten überein.")


def befehl_schnell(args) -> None:
    from .analysen import schnell

    katalog = _katalog()
    ergebnis = schnell.verteile(katalog, args.id, args.layer, melde=lambda t: None)
    ergebnis.speichern()
    print(ergebnis.kennzahl_text)
    for hinweis in ergebnis.hinweise:
        print("Hinweis:", hinweis)
    print(ergebnis.tabelle.head(50).to_string(index=False))
    print(f"Gespeichert in {pfade.relativ(pfade.verarbeitet(ergebnis.analyse_id))}")


def befehl_testdaten(args) -> None:
    from . import testdaten

    ziel = Path(args.ziel) if args.ziel else pfade.projekt() / pfade.TESTDATEN_ORDNER
    ergebnis = testdaten.erzeuge(ziel)
    print(f"{ergebnis['gebiete']} Testgebiete und alle Testdateien in {pfade.relativ(ziel)}.")
    print("Damit arbeiten: uv run essen --testdaten analyse hitze-nacht   oder   uv run essen app --testdaten")


def befehl_app(args) -> None:
    import importlib.util

    if importlib.util.find_spec("streamlit") is None:
        sys.exit("Streamlit fehlt. Bitte im Projektordner `uv sync` ausführen.")
    if getattr(args, "app_testdaten", False):
        os.environ["ESSEN_DATEN"] = pfade.TESTDATEN_ORDNER
    start = Path(__file__).resolve().parent / "app" / "start.py"
    befehl = [sys.executable, "-m", "streamlit", "run", str(start),
              "--server.address", "localhost", "--server.port", str(args.port),
              "--browser.gatherUsageStats", "false", "--server.showEmailPrompt", "false",
              "--server.headless", "true" if args.ohne_browser else "false"]
    print(f"App startet auf http://localhost:{args.port} (nur auf diesem Rechner erreichbar). Beenden mit Strg+C.")
    sys.stdout.flush()
    os.chdir(pfade.projekt())  # damit .streamlit/config.toml gilt
    if os.name == "posix":
        os.execv(sys.executable, befehl)  # Prozess ersetzen: Signale wie Strg+C erreichen Streamlit direkt
    with contextlib.suppress(KeyboardInterrupt):
        subprocess.run(befehl, env=os.environ.copy(), check=False)


# -------------------------------------------------------------------- Aufbau

def baue_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="essen", description="Öffentliche Daten für Essen: Katalog, Downloads, Analysen und lokale App.",
        epilog=BEISPIELE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--testdaten", action="store_true", help="mit den erfundenen Testdaten in data_test/ arbeiten")
    befehle = parser.add_subparsers(dest="befehl", metavar="BEFEHL")

    p = befehle.add_parser("katalog", help="Datensätze auflisten, Katalog prüfen oder Doku erzeugen")
    p.add_argument("suche", nargs="*", help="Suchwörter")
    p.add_argument("--thema"); p.add_argument("--ebene")
    p.add_argument("--ladbar", action="store_true", help="nur automatisch ladbare")
    p.add_argument("--pruefen", action="store_true", help="Katalog auf Fehler prüfen")
    p.add_argument("--doku", action="store_true", help="docs/datenquellen.md und docs/daten-erklaert.md neu schreiben")
    p.add_argument("--domains", action="store_true", help="alle Hosts für eine Netzwerkfreigabe")
    p.set_defaults(aufruf=befehl_katalog)

    p = befehle.add_parser("info", help="alles zu einem Datensatz")
    p.add_argument("id"); p.set_defaults(aufruf=befehl_info)

    p = befehle.add_parser("status", help="was ist geladen")
    p.add_argument("--aufraeumen", action="store_true", help="entpackte Ordner löschen (nach Rückfrage)")
    p.add_argument("--ja", action="store_true", help="ohne Rückfrage löschen")
    p.set_defaults(aufruf=befehl_status)

    p = befehle.add_parser("aktualisieren", help="bei den Quellen nachsehen, ob es neuere Stände gibt (lädt nichts)")
    p.add_argument("ids", nargs="*", metavar="ID", help="Standard: alle geladenen")
    p.set_defaults(aufruf=befehl_aktualisieren)

    p = befehle.add_parser("laden", help="Datensätze aus der Originalquelle laden")
    p.add_argument("ids", nargs="+", metavar="ID")
    p.add_argument("--neu", action="store_true", help="auch wenn schon geladen")
    p.add_argument("--datei", help="bei mehreren passenden Dateien im Ordner diese nehmen")
    p.add_argument("--ja", action="store_true", help="bei großen Dateien nicht nachfragen")
    p.set_defaults(aufruf=befehl_laden)

    p = befehle.add_parser("einlesen", help="eine von Hand geladene Datei übernehmen")
    p.add_argument("id"); p.add_argument("datei"); p.set_defaults(aufruf=befehl_einlesen)

    p = befehle.add_parser("loeschen", help="geladene Dateien eines Datensatzes löschen")
    p.add_argument("ids", nargs="+", metavar="ID"); p.set_defaults(aufruf=befehl_loeschen)

    p = befehle.add_parser("inspizieren", help="Inhalt eines Datensatzes oder einer Datei untersuchen")
    p.add_argument("ziel", metavar="ID_ODER_PFAD")
    p.add_argument("--alles", action="store_true", help="ganzen Bericht ausgeben")
    p.set_defaults(aufruf=befehl_inspizieren)

    p = befehle.add_parser("dienst", help="Ebenen eines WMS oder Objektarten eines WFS auflisten")
    p.add_argument("id"); p.set_defaults(aufruf=befehl_dienst)

    p = befehle.add_parser("analyse", help="Analysen auflisten oder rechnen")
    p.add_argument("id", nargs="?")
    p.add_argument("-p", action="append", metavar="NAME=WERT", help="Parameter, mehrfach möglich")
    p.add_argument("--export", action="store_true", help="zusätzlich eine HTML-Seite schreiben")
    p.set_defaults(aufruf=befehl_analyse)

    p = befehle.add_parser("vorbereiten", help="alle Daten laden und alle Themen berechnen")
    p.add_argument("--ja", action="store_true", help="bei großen Downloads nicht nachfragen")
    p.set_defaults(aufruf=befehl_vorbereiten)

    p = befehle.add_parser("pruefen-ergebnisse", help="Analysen neu rechnen und mit Referenzwerten vergleichen")
    p.add_argument("ids", nargs="*", metavar="ID", help="Standard: alle mit Referenzwert")
    p.add_argument("--festschreiben", action="store_true", help="aktuelle Werte als neue Referenz speichern")
    p.set_defaults(aufruf=befehl_pruefen_ergebnisse)

    p = befehle.add_parser("schnell", help="einen Vektordatensatz auf die Stadtteile verteilen")
    p.add_argument("id"); p.add_argument("--layer"); p.set_defaults(aufruf=befehl_schnell)

    p = befehle.add_parser("testdaten", help="erfundene Testdaten erzeugen")
    p.add_argument("--ziel", help="Ordner (Standard: data_test)"); p.set_defaults(aufruf=befehl_testdaten)

    p = befehle.add_parser("app", help="lokale App im Browser starten")
    p.add_argument("--port", type=int, default=8501)
    p.add_argument("--ohne-browser", action="store_true", help="keinen Browser öffnen")
    p.add_argument("--testdaten", dest="app_testdaten", action="store_true", help="mit den Testdaten starten")
    p.set_defaults(aufruf=befehl_app)
    return parser


def main(argv: list[str] | None = None) -> None:
    from .analysen.hitze_nacht import ZuordnungFehlt
    from .geo import DatenFehlen
    from .katalog import KatalogFehler
    from .laden import DownloadFehler

    parser = baue_parser()
    args = parser.parse_args(argv)
    if args.testdaten:
        os.environ["ESSEN_DATEN"] = pfade.TESTDATEN_ORDNER
    if not args.befehl:
        parser.print_help()
        return
    try:
        args.aufruf(args)
    except KeyError as fehler:  # unbekannte Kennung: die Meldung steht im ersten Argument
        sys.exit(f"Fehler: {fehler.args[0] if fehler.args else fehler}")
    except (DatenFehlen, DownloadFehler, ZuordnungFehlt, KatalogFehler, ValueError, FileNotFoundError) as fehler:
        sys.exit(f"Fehler: {fehler}")


if __name__ == "__main__":
    main()
