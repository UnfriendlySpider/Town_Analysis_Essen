"""Daten aus der Originalquelle laden und jeden Abruf protokollieren.

Jeder Datensatz bekommt einen eigenen Ordner data/raw/<id>/. Darin liegen die geladenen
Dateien und _abruf.json mit Adresse, Zeit, Größe, Prüfsumme und Lizenz. Zusätzlich
schreibt jeder Abruf eine Zeile in data/abrufe.csv.

Wird von der Kommandozeile (`essen laden`) und vom Knopf in der App benutzt.
"""

from __future__ import annotations

import csv
import datetime as dt
import email.utils
import fnmatch
import hashlib
import json
import re
import shutil
import time
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests

from . import __version__, pfade
from .katalog import Datensatz, Katalog

ABRUF_DATEI = "_abruf.json"
USER_AGENT = f"essen-daten/{__version__} (privates Analyseprojekt, lokal)"
ZEITLIMIT = (20, 180)  # Verbindungsaufbau, Lesen in Sekunden
BLOCK = 1 << 20
PAUSE_ZWISCHEN_DATEIEN = 1.0  # Sekunden zwischen den Dateien von download.art = dateien

Fortschritt = Callable[[int, int | None, str], None]
"""Rückmeldung während des Ladens: (geladene Bytes, Gesamtgröße oder None, Text)."""


class DownloadFehler(RuntimeError):
    """Der Download hat nicht geklappt. Die Meldung ist für Menschen geschrieben."""


class MehrereDateien(DownloadFehler):
    """Im Ordner passen mehrere Dateien zum Muster. `kandidaten` nennt sie."""

    def __init__(self, nachricht: str, kandidaten: list[DateiInfo]):
        super().__init__(nachricht)
        self.kandidaten = kandidaten


@dataclass(frozen=True)
class DateiInfo:
    name: str
    url: str
    groesse: int | None = None
    zeit: str | None = None


@dataclass
class Abruf:
    datensatz: str
    dateien: list[str]
    url: str
    zeit: str
    bytes: int
    sha256: dict[str, str] = field(default_factory=dict)
    lizenz: str = ""
    quelle: str = ""
    stand_quelle: str | None = None
    testdaten: bool = False
    hinweis: str = ""

    @property
    def datum(self) -> str:
        return self.zeit[:10]


# -------------------------------------------------------------------- Status

def ordner(ds: Datensatz | str) -> Path:
    return pfade.roh(ds if isinstance(ds, str) else ds.id)


def lese_abruf(ds: Datensatz | str) -> Abruf | None:
    pfad = ordner(ds) / ABRUF_DATEI
    if not pfad.exists():
        return None
    try:
        return Abruf(**json.loads(pfad.read_text(encoding="utf-8")))
    except (TypeError, ValueError):
        return None


def vorhanden(ds: Datensatz | str) -> bool:
    abruf = lese_abruf(ds)
    return bool(abruf and all((ordner(ds) / name).exists() for name in abruf.dateien))


def dateien(ds: Datensatz | str, muster: str = "*") -> list[Path]:
    """Alle Dateien eines Datensatzes, auch entpackte, ohne Protokoll und Reste."""
    basis = ordner(ds)
    if not basis.exists():
        return []
    return sorted(
        p for p in basis.rglob(muster)
        if p.is_file() and p.name != ABRUF_DATEI and not p.name.endswith(".part")
    )


def belegter_platz(ds: Datensatz | str) -> int:
    return sum(p.stat().st_size for p in dateien(ds))


def status_tabelle(katalog: Katalog) -> list[dict]:
    """Eine Zeile je Datensatz: geladen ja/nein, wann, wie groß."""
    zeilen = []
    for ds in katalog.datensaetze.values():
        abruf = lese_abruf(ds)
        zeilen.append({
            "id": ds.id,
            "titel": ds.titel,
            "ladbar": ds.ladbar,
            "geladen": vorhanden(ds),
            "abgerufen": abruf.datum if abruf else None,
            "bytes": belegter_platz(ds) if abruf else 0,
            "testdaten": bool(abruf and abruf.testdaten),
        })
    return zeilen


# -------------------------------------------------------------------- Download-Ordner auflösen

def sitzung() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def verzeichnis_dateien(ordner_url: str, s: requests.Session | None = None) -> list[DateiInfo]:
    """Dateien eines Download-Ordners: zuerst index.json (OpenGeodata.NRW), sonst die Linkliste."""
    s = s or sitzung()
    if not ordner_url.endswith("/"):
        ordner_url += "/"
    try:
        antwort = s.get(ordner_url + "index.json", timeout=ZEITLIMIT)
        art = antwort.headers.get("content-type", "")
        if antwort.ok and ("json" in art or antwort.text.lstrip().startswith(("{", "["))):
            gefunden = _dateien_aus_index(lies_index_json(antwort.text), ordner_url)
            if gefunden:
                return gefunden
    except (requests.RequestException, ValueError):
        pass
    try:
        antwort = s.get(ordner_url, timeout=ZEITLIMIT)
        antwort.raise_for_status()
    except requests.RequestException as fehler:
        raise DownloadFehler(f"Ordner nicht erreichbar: {ordner_url} ({_kurz(fehler)})") from None
    return _dateien_aus_html(antwort.text, ordner_url)


def lies_index_json(text: str):
    """index.json lesen. Manche Ordner von OpenGeodata.NRW haben ein Komma vor der schließenden Klammer
    (z. B. umgebungslaerm2022, Stand Dezember 2025); das ist kein gültiges JSON und wird hier entfernt."""
    try:
        return json.loads(text)
    except ValueError:
        return json.loads(re.sub(r",(\s*[\]}])", r"\1", text))


def sicherer_name(name: str) -> str:
    """Nur einfache Dateinamen zulassen: keine Ordner, kein .., kein absoluter Pfad."""
    if (not name or name in (".", "..") or "/" in name or "\\" in name or name.startswith(".")
            or Path(name).name != name or ":" in name):
        raise DownloadFehler(f"Unerwarteter Dateiname von der Quelle: {name!r}")
    return name


def _dateien_aus_index(daten, ordner_url: str) -> list[DateiInfo]:
    """Sucht im index.json alle Einträge mit name (und optional size, timestamp)."""
    gefunden: dict[str, DateiInfo] = {}

    def besuche(knoten):
        if isinstance(knoten, dict):
            name = knoten.get("name")
            if isinstance(name, str) and "." in name and "files" not in knoten and _harmlos(name):
                groesse = knoten.get("size")
                try:
                    groesse = int(groesse) if groesse is not None else None
                except (TypeError, ValueError):
                    groesse = None
                gefunden[name] = DateiInfo(name=name, url=urljoin(ordner_url, name), groesse=groesse,
                                           zeit=knoten.get("timestamp") or knoten.get("mtime"))
            for wert in knoten.values():
                besuche(wert)
        elif isinstance(knoten, list):
            for wert in knoten:
                besuche(wert)

    besuche(daten)
    return sorted(gefunden.values(), key=lambda d: d.name)


def _dateien_aus_html(html: str, ordner_url: str) -> list[DateiInfo]:
    gefunden = {}
    for href in re.findall(r'href="([^"?#]+)"', html, flags=re.IGNORECASE):
        if href.endswith("/") or href.startswith(("mailto:", "javascript:")):
            continue
        url = urljoin(ordner_url, href)
        if not url.startswith(ordner_url):
            continue  # nur Dateien in diesem Ordner
        name = unquote(url[len(ordner_url):])
        if "." in name and _harmlos(name):
            gefunden[name] = DateiInfo(name=name, url=url)
    return sorted(gefunden.values(), key=lambda d: d.name)


def _harmlos(name: str) -> bool:
    try:
        sicherer_name(name)
        return True
    except DownloadFehler:
        return False


def kandidaten(ds: Datensatz, s: requests.Session | None = None) -> list[DateiInfo]:
    """Die Dateien, die zum Muster des Datensatzes passen (nur download.art = verzeichnis)."""
    if ds.download.art != "verzeichnis":
        raise DownloadFehler(f"{ds.id} hat keinen Download-Ordner.")
    alle = verzeichnis_dateien(ds.download.ordner, s)
    passend = [d for d in alle if fnmatch.fnmatch(d.name, ds.download.muster) and d.name != "index.json"]
    if not passend:
        namen = ", ".join(d.name for d in alle[:12]) or "keine"
        raise DownloadFehler(
            f"Im Ordner passt keine Datei zum Muster „{ds.download.muster}“. Vorhanden: {namen}. "
            "Muster im Katalog anpassen."
        )
    return passend


# -------------------------------------------------------------------- Laden

def hole(
    katalog: Katalog,
    ds: Datensatz,
    *,
    fortschritt: Fortschritt | None = None,
    erzwingen: bool = False,
    datei: str | None = None,
) -> Abruf:
    """Lädt einen Datensatz in data/raw/<id>/ und gibt das Protokoll zurück.

    Ist der Datensatz schon da, wird nichts geladen (außer mit erzwingen=True).
    `datei` wählt bei mehreren passenden Dateien in einem Ordner eine aus.
    """
    if not ds.ladbar:
        raise DownloadFehler(
            f"{ds.titel} lässt sich nicht automatisch laden. {ds.download.hinweis or ''} Seite: {ds.seite}".strip()
        )
    if vorhanden(ds) and not erzwingen and not (datei and ds.download.art == "dateien"):
        return lese_abruf(ds)
    melde = fortschritt or (lambda *_: None)
    s = sitzung()
    ziel_ordner = ordner(ds)
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    art = ds.download.art
    stand = None
    if art == "verzeichnis":
        melde(0, None, "Suche die Datei im Download-Ordner")
        passend = kandidaten(ds, s)
        if datei:
            passend = [d for d in passend if d.name == datei]
            if not passend:
                raise DownloadFehler(f"Die Datei {datei} passt nicht zum Muster oder fehlt im Ordner.")
        if ds.download.alle and not datei:
            return _hole_alle(ds, s, ziel_ordner, melde, passend)
        if len(passend) > 1:
            raise MehrereDateien(
                f"Im Ordner passen {len(passend)} Dateien. Bitte eine auswählen.", passend
            )
        info = passend[0]
        url, name, stand = info.url, info.name, info.zeit
    elif art == "datei":
        url = ds.download.url
        name = ds.download.datei or Path(unquote(urlparse(url).path)).name or f"{ds.id}.dat"
    elif art == "dateien":
        url = name = ""
    elif art == "api":
        url = _ersetze_platzhalter(ds.download.url)
        name = ds.download.datei or f"{ds.id}.json"
    elif art == "wfs":
        url = wfs_adresse(ds)
        name = ds.download.datei or f"{ds.id}.{'geojson' if 'json' in (ds.download.format or '') else 'gml'}"
    else:  # pragma: no cover - durch ds.ladbar ausgeschlossen
        raise DownloadFehler(f"Unbekannte Download-Art {art}")

    if art == "dateien":
        return _hole_dateien(ds, s, ziel_ordner, melde, datei)
    name = sicherer_name(name)
    pfad, anzahl, pruefsumme = _lade_datei(s, url, ziel_ordner / name, melde)
    if art in ("api", "wfs"):
        _pruefe_antwort(pfad, art)
    abruf = Abruf(
        datensatz=ds.id,
        dateien=[name],
        url=url,
        zeit=dt.datetime.now().isoformat(timespec="seconds"),
        bytes=anzahl,
        sha256={name: pruefsumme},
        lizenz=ds.lizenz,
        quelle=ds.quelle,
        stand_quelle=stand,
    )
    _alte_entpackte_entfernen(ziel_ordner, behalten=name)
    schreibe_abruf(abruf)
    melde(anzahl, anzahl, "Fertig")
    return abruf


def _hole_dateien(ds: Datensatz, s: requests.Session, ziel_ordner: Path, melde: Fortschritt,
                  datei: str | None) -> Abruf:
    """download.art = dateien: alle Adressen in denselben Ordner laden. Mit `datei` nur diese eine nachladen."""
    ziele = [(u, sicherer_name(n)) for u, n in ds.download.ziele]
    auswahl = ziele
    if datei:
        auswahl = [(u, n) for u, n in ziele if n == datei]
        if not auswahl:
            raise DownloadFehler(f"{datei} steht nicht in download.urls. Vorhanden: {', '.join(n for _, n in ziele)}")
    alt = lese_abruf(ds) if datei else None
    sha256 = dict(alt.sha256) if alt else {}
    for nummer, (url, name) in enumerate(auswahl, 1):
        if nummer > 1:
            time.sleep(PAUSE_ZWISCHEN_DATEIEN)  # Rücksicht auf APIs mit Anfragegrenzen
        _, _, sha256[name] = _lade_datei(s, url, ziel_ordner / name, melde)
        melde(0, None, f"{nummer} von {len(auswahl)} geladen")
    namen = [n for _, n in ziele if n in sha256]
    abruf = Abruf(
        datensatz=ds.id,
        dateien=namen,
        url=" ".join(ds.download.urls),
        zeit=dt.datetime.now().isoformat(timespec="seconds"),
        bytes=sum((ziel_ordner / n).stat().st_size for n in namen),
        sha256={n: sha256[n] for n in namen},
        lizenz=ds.lizenz,
        quelle=ds.quelle,
    )
    for unterordner in ziel_ordner.glob("entpackt_*"):
        if unterordner.is_dir() and f"{unterordner.name[len('entpackt_'):]}.zip" not in namen:
            shutil.rmtree(unterordner, ignore_errors=True)
    for _, name in auswahl:
        shutil.rmtree(ziel_ordner / f"entpackt_{Path(name).stem}", ignore_errors=True)
    if ds.download.format and "json" in ds.download.format.lower():
        for _, name in auswahl:
            _pruefe_antwort(ziel_ordner / name, "api")
    schreibe_abruf(abruf)
    melde(abruf.bytes, abruf.bytes, "Fertig")
    return abruf


def _hole_alle(ds: Datensatz, s: requests.Session, ziel_ordner: Path, melde: Fortschritt,
               passend: list[DateiInfo]) -> Abruf:
    """download.alle: alle passenden Dateien eines Ordners laden. Schon vorhandene mit gleicher Größe bleiben."""
    alt = lese_abruf(ds)
    sha256 = dict(alt.sha256) if alt else {}
    for nummer, info in enumerate(passend, 1):
        name = sicherer_name(info.name)
        ziel = ziel_ordner / name
        if not (name in sha256 and ziel.exists() and info.groesse and ziel.stat().st_size == info.groesse):
            _, _, sha256[name] = _lade_datei(s, info.url, ziel, melde)
        melde(0, None, f"{nummer} von {len(passend)} Dateien")
    namen = [sicherer_name(d.name) for d in passend]
    for rest in ziel_ordner.iterdir():  # Dateien, die es im Ordner nicht mehr gibt
        if rest.is_file() and rest.name not in namen and rest.name != ABRUF_DATEI:
            rest.unlink()
    staende = sorted(d.zeit for d in passend if d.zeit)
    abruf = Abruf(
        datensatz=ds.id,
        dateien=namen,
        url=ds.download.ordner,
        zeit=dt.datetime.now().isoformat(timespec="seconds"),
        bytes=sum((ziel_ordner / n).stat().st_size for n in namen),
        sha256={n: sha256[n] for n in namen if n in sha256},
        lizenz=ds.lizenz,
        quelle=ds.quelle,
        stand_quelle=staende[-1] if staende else None,
    )
    schreibe_abruf(abruf)
    melde(abruf.bytes, abruf.bytes, "Fertig")
    return abruf


def _lade_datei(s: requests.Session, url: str, ziel: Path, melde: Fortschritt) -> tuple[Path, int, str]:
    """Lädt eine Datei. Bricht die Verbindung vor dem ersten Byte ab (opendata.essen.de schließt
    wiederverwendete Verbindungen manchmal), folgt ein zweiter Versuch mit neuer Verbindung."""
    for versuch in range(4):
        try:
            return _lade_datei_einmal(s, url, ziel, melde)
        except _VerbindungWeg:
            if versuch:
                raise
            s = sitzung()
        except _ZuVieleAnfragen as fehler:
            if versuch == 3:
                raise DownloadFehler(f"Die Quelle meldet zu viele Anfragen (429), auch nach Warten. Später erneut "
                                     f"versuchen. Adresse: {url}") from None
            melde(0, None, f"Quelle bittet um Pause, warte {fehler.sekunden:g} s")
            time.sleep(fehler.sekunden)
    raise AssertionError("nicht erreichbar")  # pragma: no cover


class _VerbindungWeg(DownloadFehler):
    pass


class _ZuVieleAnfragen(DownloadFehler):
    def __init__(self, sekunden: float):
        super().__init__("429")
        self.sekunden = sekunden


PAUSE_429 = 20.0  # Sekunden, wenn die Quelle keine Retry-After-Angabe macht


def _lade_datei_einmal(s: requests.Session, url: str, ziel: Path, melde: Fortschritt) -> tuple[Path, int, str]:
    teil = ziel.with_name(ziel.name + ".part")
    pruefsumme = hashlib.sha256()
    geladen = 0
    letzte_meldung = 0.0
    try:
        with s.get(url, stream=True, timeout=ZEITLIMIT) as antwort:
            if antwort.status_code == 429:
                angabe = antwort.headers.get("retry-after", "")
                raise _ZuVieleAnfragen(min(120.0, float(angabe)) if angabe.isdigit() else PAUSE_429)
            if antwort.status_code == 404:
                raise DownloadFehler(f"Die Adresse gibt es nicht (404): {url}. Den Eintrag im Katalog prüfen.")
            antwort.raise_for_status()
            gesamt = int(antwort.headers.get("content-length") or 0) or None
            with open(teil, "wb") as datei:
                for block in antwort.iter_content(chunk_size=BLOCK):
                    datei.write(block)
                    pruefsumme.update(block)
                    geladen += len(block)
                    jetzt = time.monotonic()
                    if jetzt - letzte_meldung > 0.25:
                        melde(geladen, gesamt, f"Lade {ziel.name}")
                        letzte_meldung = jetzt
    except requests.RequestException as fehler:
        teil.unlink(missing_ok=True)
        art = _VerbindungWeg if isinstance(fehler, requests.ConnectionError) and geladen == 0 else DownloadFehler
        raise art(f"Download fehlgeschlagen: {_kurz(fehler)}. Adresse: {url}") from None
    except BaseException:
        teil.unlink(missing_ok=True)
        raise
    if geladen == 0:
        teil.unlink(missing_ok=True)
        raise DownloadFehler(f"Die Quelle hat eine leere Datei geliefert: {url}")
    teil.replace(ziel)
    return ziel, geladen, pruefsumme.hexdigest()


def _pruefe_antwort(pfad: Path, art: str) -> None:
    """APIs und WFS antworten bei Fehlern oft mit Status 200 und einer Fehlermeldung im Text."""
    with open(pfad, "rb") as datei:
        anfang = datei.read(2000).decode("utf-8", errors="replace")
    if "ExceptionReport" in anfang or "ServiceException" in anfang:
        pfad.unlink(missing_ok=True)
        raise DownloadFehler(f"Der Dienst meldet einen Fehler: {anfang[:500]}")
    if art == "api" and pfad.suffix == ".json" and pfad.stat().st_size < 200_000_000:
        try:
            json.loads(pfad.read_text(encoding="utf-8"))
        except ValueError:
            pfad.unlink(missing_ok=True)
            raise DownloadFehler(f"Die Antwort ist kein JSON: {anfang[:300]}") from None


def _alte_entpackte_entfernen(ziel_ordner: Path, behalten: str) -> None:
    for unterordner in ziel_ordner.iterdir():
        if unterordner.is_dir() and unterordner.name.startswith("entpackt"):
            shutil.rmtree(unterordner, ignore_errors=True)
    for alt in ziel_ordner.iterdir():
        if alt.is_file() and alt.name not in (behalten, ABRUF_DATEI):
            alt.unlink()


def _kurz(fehler: Exception) -> str:
    text = str(fehler)
    if "Max retries exceeded" in text or "NameResolution" in text or "ConnectionError" in type(fehler).__name__:
        return "keine Verbindung zum Server"
    if "403" in text and "Tunnel" in text:
        return "Zugriff durch Proxy oder Netzwerkfreigabe gesperrt (403)"
    return text[:300]


def _ersetze_platzhalter(text: str) -> str:
    heute = dt.date.today()
    werte = {
        "{heute}": heute.isoformat(),
        "{gestern}": (heute - dt.timedelta(days=1)).isoformat(),
        "{vor_7_tagen}": (heute - dt.timedelta(days=7)).isoformat(),
        "{vor_30_tagen}": (heute - dt.timedelta(days=30)).isoformat(),
    }
    if "{bbox_wgs84}" in text or "{bbox_25832}" in text:
        from .geo import essen_bbox

        werte["{bbox_wgs84}"] = ",".join(f"{x:.5f}" for x in essen_bbox("EPSG:4326"))
        werte["{bbox_25832}"] = ",".join(f"{x:.0f}" for x in essen_bbox("EPSG:25832"))
    for alt, neu in werte.items():
        text = text.replace(alt, neu)
    return text


def wfs_adresse(ds: Datensatz) -> str:
    """GetFeature-Abfrage für das Stadtgebiet (WFS 2.0, Koordinaten in EPSG:25832)."""
    from .geo import essen_bbox

    d = ds.download
    x1, y1, x2, y2 = essen_bbox("EPSG:25832")
    parameter = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": d.typname,
        "SRSNAME": "urn:ogc:def:crs:EPSG::25832",
        "BBOX": f"{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f},urn:ogc:def:crs:EPSG::25832",
    }
    if d.format:
        parameter["OUTPUTFORMAT"] = d.format
    parameter.update({k.upper(): str(v) for k, v in (d.parameter or {}).items()})
    trenner = "&" if "?" in d.url else "?"
    return d.url + trenner + "&".join(f"{k}={requests.utils.quote(v, safe=':,/')}" for k, v in parameter.items())


# -------------------------------------------------------------------- Protokoll

def schreibe_abruf(abruf: Abruf) -> None:
    pfad = ordner(abruf.datensatz) / ABRUF_DATEI
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(asdict(abruf), ensure_ascii=False, indent=2), encoding="utf-8")
    protokoll = pfade.abrufprotokoll()
    neu = not protokoll.exists()
    with open(protokoll, "a", newline="", encoding="utf-8") as datei:
        schreiber = csv.writer(datei)
        if neu:
            schreiber.writerow(["zeit", "datensatz", "dateien", "bytes", "url", "lizenz", "testdaten", "hinweis"])
        schreiber.writerow([abruf.zeit, abruf.datensatz, " ".join(abruf.dateien), abruf.bytes, abruf.url,
                            abruf.lizenz, "ja" if abruf.testdaten else "", abruf.hinweis])


def einlesen_bytes(ds: Datensatz, name: str, daten: bytes) -> Abruf:
    """Eine hochgeladene Datei (Name und Inhalt) übernehmen, etwa aus der App. Pfadteile im Namen zählen nicht."""
    import tempfile

    with tempfile.TemporaryDirectory() as ordner_tmp:
        pfad = Path(ordner_tmp) / (Path(name).name or "datei")
        pfad.write_bytes(daten)
        return einlesen(ds, pfad)


def quellenangaben(katalog: Katalog) -> list[str]:
    """Quellenangaben aller geladenen Datensätze, mit dem Datum des Abrufs (für Fußzeilen und Weitergabe)."""
    from .katalog import quellenangabe

    zeilen = []
    for ds in katalog.datensaetze.values():
        if vorhanden(ds):
            abruf = lese_abruf(ds)
            zeilen.append(quellenangabe(katalog, ds, abruf.datum if abruf else None))
    return zeilen


def einlesen(ds: Datensatz, quelle_pfad: Path, hinweis: str = "") -> Abruf:
    """Eine von Hand geladene Datei übernehmen, z. B. aus dem Browser-Download."""
    quelle_pfad = Path(quelle_pfad).expanduser().resolve()
    if not quelle_pfad.is_file():
        raise DownloadFehler(f"Datei nicht gefunden: {quelle_pfad}")
    ziel_ordner = ordner(ds)
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    ziel = ziel_ordner / quelle_pfad.name
    if quelle_pfad != ziel:
        shutil.copy2(quelle_pfad, ziel)
    pruefsumme = hashlib.sha256()
    with open(ziel, "rb") as datei:
        for block in iter(lambda: datei.read(BLOCK), b""):
            pruefsumme.update(block)
    _alte_entpackte_entfernen(ziel_ordner, behalten=ziel.name)
    abruf = Abruf(
        datensatz=ds.id,
        dateien=[ziel.name],
        url=f"von Hand übernommen: {quelle_pfad.name}",
        zeit=dt.datetime.now().isoformat(timespec="seconds"),
        bytes=ziel.stat().st_size,
        sha256={ziel.name: pruefsumme.hexdigest()},
        lizenz=ds.lizenz,
        quelle=ds.quelle,
        hinweis=hinweis or f"Seite der Quelle: {ds.seite}",
    )
    schreibe_abruf(abruf)
    return abruf


def entferne(ds: Datensatz | str) -> None:
    """Löscht alle geladenen Dateien eines Datensatzes."""
    shutil.rmtree(ordner(ds), ignore_errors=True)


# -------------------------------------------------------------------- Aktualität

@dataclass(frozen=True)
class Aktualitaet:
    """Vergleich des geladenen Stands mit der Quelle. zustand: aktuell, neu, unbekannt, fehler, abfrage, hand."""

    datensatz: str
    zustand: str
    text: str


def pruefe_aktualitaet(ds: Datensatz, s: requests.Session | None = None) -> Aktualitaet:
    """Fragt die Quelle, ob es einen neueren Stand gibt. Lädt nichts herunter."""
    abruf = lese_abruf(ds)
    if not abruf:
        return Aktualitaet(ds.id, "unbekannt", "nicht geladen")
    if abruf.url.startswith("von Hand"):
        return Aktualitaet(ds.id, "hand", f"von Hand übernommen am {abruf.datum}; Seite ansehen: {ds.seite}")
    art = ds.download.art
    if art in ("api", "wfs"):
        return Aktualitaet(ds.id, "abfrage", f"Abfrage vom {abruf.datum}; wird bei jedem Laden neu erzeugt")
    s = s or sitzung()
    try:
        if art == "verzeichnis":
            return _aktualitaet_ordner(ds, abruf, s)
        if art == "datei":
            return _aktualitaet_datei(ds, abruf, abruf.url, abruf.dateien[0], s)
        if art == "dateien":
            staende = [_aktualitaet_datei(ds, abruf, url, name, s) for url, name in ds.download.ziele]
            fehlend = [name for _, name in ds.download.ziele if name not in abruf.dateien]
            for zustand in ("fehler", "neu", "unbekannt"):
                betroffen = [st.text for st in staende if st.zustand == zustand]
                if betroffen:
                    return Aktualitaet(ds.id, zustand, "; ".join(betroffen))
            if fehlend:
                return Aktualitaet(ds.id, "neu", f"noch nicht geladen: {', '.join(fehlend)}")
            return Aktualitaet(ds.id, "aktuell", f"{len(staende)} Dateien, geladen am {abruf.datum}")
    except DownloadFehler as fehler:
        return Aktualitaet(ds.id, "fehler", str(fehler))
    return Aktualitaet(ds.id, "unbekannt", f"Download-Art {art} lässt sich nicht vergleichen")


def _aktualitaet_ordner(ds: Datensatz, abruf: Abruf, s: requests.Session) -> Aktualitaet:
    passend = kandidaten(ds, s)
    if ds.download.alle:
        neu = [d.name for d in passend if d.name not in abruf.dateien]
        if neu:
            return Aktualitaet(ds.id, "neu", f"neue Dateien: {', '.join(neu)}")
        return Aktualitaet(ds.id, "aktuell", f"{len(passend)} Dateien, geladen am {abruf.datum}")
    name = abruf.dateien[0]
    weitere = [d.name for d in passend if d.name != name]
    gleich = next((d for d in passend if d.name == name), None)
    if gleich is None:
        return Aktualitaet(ds.id, "neu", f"{name} gibt es im Ordner nicht mehr; jetzt: {', '.join(weitere)}")
    gruende = []
    if gleich.zeit and abruf.stand_quelle and gleich.zeit != abruf.stand_quelle:
        gruende.append(f"Stand {gleich.zeit} statt {abruf.stand_quelle}")
    if gleich.groesse and gleich.groesse != abruf.bytes:
        gruende.append(f"Größe {gleich.groesse} statt {abruf.bytes} Bytes")
    if weitere:
        gruende.append(f"weitere passende Dateien: {', '.join(weitere)}")
    if gruende:
        return Aktualitaet(ds.id, "neu", "; ".join(gruende))
    if not gleich.zeit and not gleich.groesse:
        return Aktualitaet(ds.id, "unbekannt", "der Ordner nennt weder Stand noch Größe")
    return Aktualitaet(ds.id, "aktuell", f"Stand {abruf.stand_quelle or abruf.datum}")


def _aktualitaet_datei(ds: Datensatz, abruf: Abruf, url: str, name: str, s: requests.Session) -> Aktualitaet:
    lokal = ordner(ds) / name
    groesse_lokal = lokal.stat().st_size if lokal.exists() else None
    for versuch in range(2):  # opendata.essen.de schließt wiederverwendete Verbindungen manchmal
        try:
            antwort = s.head(url, allow_redirects=True, timeout=ZEITLIMIT)
            break
        except requests.ConnectionError:
            if versuch:
                return Aktualitaet(ds.id, "fehler", "Quelle nicht erreichbar: keine Verbindung zum Server")
        except requests.RequestException as fehler:
            raise DownloadFehler(f"Quelle nicht erreichbar: {_kurz(fehler)}") from None
    if antwort.status_code == 404:
        return Aktualitaet(ds.id, "fehler", f"Die Adresse gibt es nicht mehr (404): {url}")
    if not antwort.ok:
        return Aktualitaet(ds.id, "unbekannt", f"Die Quelle beantwortet HEAD nicht ({antwort.status_code})")
    gruende = []
    laenge = antwort.headers.get("content-length")
    if (laenge and laenge.isdigit() and groesse_lokal is not None and int(laenge) != groesse_lokal
            and "gzip" not in antwort.headers.get("content-encoding", "")):
        gruende.append(f"{name}: Größe {laenge} statt {groesse_lokal} Bytes")
    geaendert = antwort.headers.get("last-modified")
    if geaendert:
        try:
            zeit = email.utils.parsedate_to_datetime(geaendert).astimezone().replace(tzinfo=None)
        except (TypeError, ValueError):
            zeit = None
        if zeit and zeit > dt.datetime.fromisoformat(abruf.zeit):
            gruende.append(f"{name}: geändert am {zeit:%d.%m.%Y}, geladen am {abruf.datum}")
    if gruende:
        return Aktualitaet(ds.id, "neu", "; ".join(gruende))
    if not laenge and not geaendert:
        return Aktualitaet(ds.id, "unbekannt", "die Quelle nennt weder Größe noch Änderungsdatum")
    return Aktualitaet(ds.id, "aktuell", f"geladen am {abruf.datum}")


# -------------------------------------------------------------------- Aufräumen

def entpackte_ordner(ds: Datensatz | str) -> list[tuple[Path, int]]:
    """Entpackte Ordner, deren ZIP noch daliegt (lassen sich jederzeit neu erzeugen), mit Größe in Bytes."""
    basis = ordner(ds)
    if not basis.exists():
        return []
    gefunden = []
    for unterordner in sorted(basis.glob("entpackt_*")):
        if unterordner.is_dir() and (basis / f"{unterordner.name[len('entpackt_'):]}.zip").exists():
            groesse = sum(p.stat().st_size for p in unterordner.rglob("*") if p.is_file())
            gefunden.append((unterordner, groesse))
    return gefunden


# -------------------------------------------------------------------- Entpacken

def entpacke(archiv: Path, ziel: Path) -> Path:
    """Entpackt ein ZIP sicher: keine Pfade außerhalb des Zielordners."""
    ziel = ziel.resolve()
    with zipfile.ZipFile(archiv) as zf:
        for eintrag in zf.infolist():
            pfad = (ziel / eintrag.filename).resolve()
            if pfad != ziel and ziel not in pfad.parents:
                raise DownloadFehler(f"Unerwarteter Pfad im ZIP {archiv.name}: {eintrag.filename}")
        teil = ziel.with_name(ziel.name + ".part")
        shutil.rmtree(teil, ignore_errors=True)
        zf.extractall(teil)
        shutil.rmtree(ziel, ignore_errors=True)
        teil.replace(ziel)
    return ziel


def entpackt(ds: Datensatz | str) -> list[Path]:
    """Entpackt alle ZIPs des Datensatzes einmalig und gibt alle nutzbaren Dateien zurück."""
    basis = ordner(ds)
    for archiv in sorted(basis.glob("*.zip")):
        ziel = basis / f"entpackt_{archiv.stem}"
        if not ziel.exists():
            entpacke(archiv, ziel)
    return [p for p in dateien(ds) if p.suffix.lower() != ".zip"]
