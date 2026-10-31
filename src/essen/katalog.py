"""Der Datenkatalog: Lizenzen, Quellen und Datensätze aus katalog/*.yaml.

Der Katalog ist die einzige Stelle, an der Adressen, Lizenzen und Download-Angaben
stehen. Code, App und Doku lesen von hier. Aufbau der Dateien: docs/katalog.md.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar
from urllib.parse import unquote, urlparse

import yaml

from . import pfade

EBENEN = {
    "stadt": "Stadt Essen",
    "region": "Metropole Ruhr",
    "land": "Land NRW",
    "bund": "Bund",
    "mobilitaet": "Verkehrsverbund und Betreiber",
    "community": "Community und Drittanbieter",
}

THEMEN = {
    "klima": "Klima und Hitze",
    "luft": "Luft",
    "laerm": "Lärm",
    "wasser": "Wasser und Starkregen",
    "gruen": "Grün, Natur und Boden",
    "energie": "Energie und Klimaschutz",
    "geo": "Geobasis, Gebäude und Grenzen",
    "bevoelkerung": "Bevölkerung und Soziales",
    "mobilitaet": "Mobilität",
    "wahlen": "Wahlen und Politik",
    "wirtschaft": "Wirtschaft und Arbeit",
    "verwaltung": "Verwaltung und Haushalt",
    "kultur": "Kultur und Freizeit",
}
UMWELT_THEMEN = ("klima", "luft", "laerm", "wasser", "gruen", "energie")

DOWNLOAD_ARTEN = {
    "datei": "Datei unter fester Adresse",
    "dateien": "mehrere Dateien unter festen Adressen",
    "verzeichnis": "Datei aus einem Download-Ordner",
    "wfs": "WFS-Abfrage für das Stadtgebiet",
    "api": "JSON-Abfrage",
    "manuell": "von Hand laden und einlesen",
    "keiner": "nichts zu laden, nur ansehen",
}
AUTOMATISCH = ("datei", "dateien", "verzeichnis", "wfs", "api")

STATUS = {
    "geprueft": "Download geprüft",
    "ungeprueft": "Download eingetragen, noch nicht bestätigt",
    "manuell": "nur von Hand",
    "dienst": "nur Kartendienst",
}

KONTO = {
    "ohne": "ohne Konto",
    "registrierung": "kostenlose Registrierung",
    "auf-anfrage": "nur auf Anfrage",
    "oeffentlicher-schluessel": "öffentlich genannter Schlüssel",
    "bedingt": "ohne Konto für private Nutzung",
    "unklar": "unklar",
}

DIENST_ARTEN = ("wms", "wfs", "xyz", "ogcapi")

_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class KatalogFehler(ValueError):
    """Der Katalog enthält Fehler. Die Meldung nennt alle gefundenen Probleme."""


@dataclass(frozen=True)
class Link:
    titel: str
    url: str


@dataclass(frozen=True)
class Lizenz:
    id: str
    name: str
    kurz: str
    url: str | None = None
    namensnennung: bool = True
    kommerziell: bool = False
    bearbeitung: bool = False
    gleiche_bedingungen: bool = False
    pruefen: bool = False
    hinweis: str = ""

    @property
    def offen(self) -> bool:
        return not self.pruefen


@dataclass(frozen=True)
class Quelle:
    id: str
    name: str
    ebene: str
    themen: tuple[str, ...]
    beschreibung: str
    lizenz: str
    kurz: str = ""
    zugang: tuple[str, ...] = ()
    lizenz_hinweis: str = ""
    aktualitaet: str = ""
    konto: str = "unklar"
    konto_hinweis: str = ""
    eignung: int = 2
    endpunkte: tuple[Link, ...] = ()
    links: tuple[Link, ...] = ()
    beispiele: tuple[str, ...] = ()
    hinweise: tuple[str, ...] = ()
    kontakt: tuple[str, ...] = ()


@dataclass(frozen=True)
class Download:
    art: str
    url: str | None = None
    urls: tuple[str, ...] = ()
    namen: tuple[str, ...] = ()   # Dateinamen zu urls (leer: aus der Adresse)
    ordner: str | None = None
    muster: str | None = None
    alle: bool = False            # verzeichnis: alle passenden Dateien laden (z. B. eine Datei je Jahr)
    datei: str | None = None
    groesse_mb: float | None = None
    typname: str | None = None
    format: str | None = None
    parameter: dict = field(default_factory=dict)
    hinweis: str = ""

    @property
    def automatisch(self) -> bool:
        return self.art in AUTOMATISCH

    @property
    def ziele(self) -> list[tuple[str, str]]:
        """download.art = dateien: (Adresse, Dateiname) je Eintrag. Ohne eigenen Namen der letzte Teil der Adresse."""
        namen = list(self.namen) + [""] * (len(self.urls) - len(self.namen))
        return [(u, n or Path(unquote(urlparse(u).path)).name) for u, n in zip(self.urls, namen, strict=True)]


@dataclass(frozen=True)
class Dienst:
    art: str
    url: str
    titel: str = ""
    ebenen: tuple[str, ...] = ()


@dataclass(frozen=True)
class Erklaerung:
    """Ein Datensatz in Worten für Menschen ohne Vorwissen (Seite „Daten erklärt“, docs/daten-erklaert.md)."""
    herkunft: str = ""   # wer die Daten erhebt und wie sie entstehen
    inhalt: str = ""     # was drinsteht
    nutzen: str = ""     # wofür man sie verwenden kann
    lesen: str = ""      # wie man sie richtig deutet, wo die Grenzen sind

    ABSCHNITTE: ClassVar[dict[str, str]] = {"herkunft": "Woher kommen die Daten?", "inhalt": "Was steht drin?",
                  "nutzen": "Wofür kann man sie nutzen?", "lesen": "Wie liest man sie, und was sagen sie nicht?"}

    def abschnitte(self) -> list[tuple[str, str]]:
        """(Überschrift, Text) der ausgefüllten Abschnitte, in fester Reihenfolge."""
        return [(titel, getattr(self, feld).strip()) for feld, titel in self.ABSCHNITTE.items()
                if getattr(self, feld).strip()]


@dataclass(frozen=True)
class Datensatz:
    id: str
    titel: str
    quelle: str
    themen: tuple[str, ...]
    beschreibung: str
    lizenz: str
    seite: str
    download: Download
    status: str
    bereitsteller: str = ""
    format: str = ""
    raumbezug: str = ""
    stand: str = ""
    namensnennung: str = ""
    dienste: tuple[Dienst, ...] = ()
    felder: dict = field(default_factory=dict)
    geprueft: str = ""
    analysen: tuple[str, ...] = ()
    begleitend: tuple[str, ...] = ()
    hinweise: tuple[str, ...] = ()
    erklaerung: Erklaerung | None = None

    @property
    def ladbar(self) -> bool:
        return self.download.automatisch

    @property
    def gross(self) -> bool:
        return (self.download.groesse_mb or 0) >= 500


@dataclass(frozen=True)
class Luecke:
    art: str
    titel: str
    text: str
    weg: str


@dataclass
class Katalog:
    lizenzen: dict[str, Lizenz]
    quellen: dict[str, Quelle]
    datensaetze: dict[str, Datensatz]
    luecken: list[Luecke] = field(default_factory=list)
    ordner: Path | None = None

    # ---------------------------------------------------------------- Abfragen

    def datensatz(self, kennung: str) -> Datensatz:
        try:
            return self.datensaetze[kennung]
        except KeyError:
            aehnlich = [k for k in self.datensaetze if kennung.split("-")[0] in k][:5]
            tipp = f" Meintest du: {', '.join(aehnlich)}?" if aehnlich else ""
            raise KeyError(f"Datensatz „{kennung}“ steht nicht im Katalog.{tipp}") from None

    def quelle_von(self, ds: Datensatz) -> Quelle:
        return self.quellen[ds.quelle]

    def lizenz_von(self, objekt: Datensatz | Quelle) -> Lizenz:
        return self.lizenzen[objekt.lizenz]

    def filter(
        self,
        themen: list[str] | tuple[str, ...] | None = None,
        ebene: str | None = None,
        nur_ladbar: bool = False,
        suche: str | None = None,
    ) -> list[Datensatz]:
        ergebnis = []
        for ds in self.datensaetze.values():
            if themen and not set(themen) & set(ds.themen):
                continue
            if ebene and self.quellen[ds.quelle].ebene != ebene:
                continue
            if nur_ladbar and not ds.ladbar:
                continue
            if suche:
                text = " ".join([ds.id, ds.titel, ds.beschreibung, ds.bereitsteller, ds.format]).lower()
                if not all(teil in text for teil in suche.lower().split()):
                    continue
            ergebnis.append(ds)
        return ergebnis

    def domains(self) -> list[str]:
        """Alle Hosts, die das Projekt erreichen muss, z. B. für eine Netzwerk-Freigabe in der Cloud."""
        hosts: set[str] = set()
        for ds in self.datensaetze.values():
            for url in (ds.download.url, ds.download.ordner, *ds.download.urls, *(d.url for d in ds.dienste)):
                if url:
                    hosts.add(urlparse(url).hostname or "")
        return sorted(h for h in hosts if h)

    def zaehle(self) -> dict[str, Counter]:
        return {
            "themen": Counter(t for ds in self.datensaetze.values() for t in ds.themen),
            "status": Counter(ds.status for ds in self.datensaetze.values()),
            "lizenzen": Counter(ds.lizenz for ds in self.datensaetze.values()),
            "ebenen": Counter(q.ebene for q in self.quellen.values()),
        }

    # ---------------------------------------------------------------- Prüfung

    def pruefe(self) -> tuple[list[str], list[str]]:
        """Gibt (Fehler, Warnungen) zurück. Fehler machen den Katalog unbrauchbar."""
        fehler: list[str] = []
        warnungen: list[str] = []
        for q in self.quellen.values():
            ort = f"Quelle {q.id}"
            if not _ID.match(q.id):
                fehler.append(f"{ort}: Kennung nur aus Kleinbuchstaben, Ziffern und Bindestrichen bilden")
            if q.ebene not in EBENEN:
                fehler.append(f"{ort}: unbekannte Ebene „{q.ebene}“ (erlaubt: {', '.join(EBENEN)})")
            if q.lizenz not in self.lizenzen:
                fehler.append(f"{ort}: unbekannte Lizenz „{q.lizenz}“")
            if q.konto not in KONTO:
                fehler.append(f"{ort}: unbekannte Kontoart „{q.konto}“ (erlaubt: {', '.join(KONTO)})")
            for thema in q.themen:
                if thema not in THEMEN:
                    fehler.append(f"{ort}: unbekanntes Thema „{thema}“")
            for link in (*q.endpunkte, *q.links):
                _pruefe_url(link.url, ort, fehler, warnungen, platzhalter_erlaubt=True)
        for ds in self.datensaetze.values():
            ort = f"Datensatz {ds.id}"
            if not _ID.match(ds.id):
                fehler.append(f"{ort}: Kennung nur aus Kleinbuchstaben, Ziffern und Bindestrichen bilden")
            if ds.quelle not in self.quellen:
                fehler.append(f"{ort}: Quelle „{ds.quelle}“ fehlt in quellen.yaml")
            if ds.lizenz not in self.lizenzen:
                fehler.append(f"{ort}: unbekannte Lizenz „{ds.lizenz}“")
            elif self.lizenzen[ds.lizenz].pruefen:
                warnungen.append(f"{ort}: Lizenz „{self.lizenzen[ds.lizenz].kurz}“ vor einer Weitergabe klären")
            if not ds.themen:
                fehler.append(f"{ort}: mindestens ein Thema angeben")
            for thema in ds.themen:
                if thema not in THEMEN:
                    fehler.append(f"{ort}: unbekanntes Thema „{thema}“")
            if ds.status not in STATUS:
                fehler.append(f"{ort}: unbekannter Status „{ds.status}“ (erlaubt: {', '.join(STATUS)})")
            _pruefe_url(ds.seite, ort, fehler, warnungen)
            _pruefe_download(ds, ort, fehler, warnungen)
            for dienst in ds.dienste:
                if dienst.art not in DIENST_ARTEN:
                    fehler.append(f"{ort}: unbekannte Dienstart „{dienst.art}“ (erlaubt: {', '.join(DIENST_ARTEN)})")
                _pruefe_url(dienst.url, ort, fehler, warnungen, platzhalter_erlaubt=dienst.art == "xyz")
            for kennung in ds.begleitend:
                if kennung not in self.datensaetze:
                    fehler.append(f"{ort}: begleitender Datensatz „{kennung}“ fehlt im Katalog")
            if ds.status == "dienst" and not ds.dienste:
                fehler.append(f"{ort}: Status dienst, aber kein Eintrag unter dienste")
            if ds.status == "geprueft" and not ds.geprueft:
                warnungen.append(f"{ort}: Status geprueft, aber kein Vermerk unter geprueft (wann, wie)")
            if ds.erklaerung is None:
                warnungen.append(f"{ort}: keine erklaerung (herkunft, inhalt, nutzen, lesen) für „Daten erklärt“")
            elif len(ds.erklaerung.abschnitte()) < len(Erklaerung.ABSCHNITTE):
                warnungen.append(f"{ort}: erklaerung unvollständig (herkunft, inhalt, nutzen und lesen ausfüllen)")
        return fehler, warnungen


def _pruefe_url(url, ort, fehler, warnungen, platzhalter_erlaubt=False) -> None:
    if not url:
        fehler.append(f"{ort}: Adresse fehlt")
        return
    teile = urlparse(url)
    if teile.scheme not in ("http", "https") or not teile.netloc:
        fehler.append(f"{ort}: keine gültige Adresse: {url}")
    elif teile.scheme == "http":
        warnungen.append(f"{ort}: unverschlüsselte Adresse (http): {url}")
    if not platzhalter_erlaubt and ("<" in url or "{" in url):
        fehler.append(f"{ort}: Platzhalter in der Adresse: {url}")


def _pruefe_download(ds: Datensatz, ort: str, fehler: list[str], warnungen: list[str]) -> None:
    d = ds.download
    if d.art not in DOWNLOAD_ARTEN:
        fehler.append(f"{ort}: unbekannte Download-Art „{d.art}“ (erlaubt: {', '.join(DOWNLOAD_ARTEN)})")
        return
    if d.art in ("datei", "api", "wfs"):
        if not d.url:
            fehler.append(f"{ort}: download.url fehlt")
        else:
            _pruefe_url(d.url, ort, fehler, warnungen, platzhalter_erlaubt=d.art == "api")
    if d.art == "dateien":
        if not d.urls:
            fehler.append(f"{ort}: download.urls fehlt (Liste der Adressen)")
        namen = [n for _, n in d.ziele]
        if len(set(namen)) != len(namen):
            fehler.append(f"{ort}: download.urls enthält Dateinamen doppelt")
        for u in d.urls:
            _pruefe_url(u, ort, fehler, warnungen)
    if d.art == "verzeichnis":
        if not d.ordner or not d.muster:
            fehler.append(f"{ort}: download.ordner und download.muster angeben")
        elif not d.ordner.endswith("/"):
            fehler.append(f"{ort}: download.ordner muss mit / enden")
        else:
            _pruefe_url(d.ordner, ort, fehler, warnungen)
    if d.art == "wfs" and not d.typname:
        fehler.append(f"{ort}: download.typname für den WFS angeben")
    if d.art == "manuell" and not d.hinweis:
        fehler.append(f"{ort}: download.hinweis erklären, wie man die Daten von Hand bekommt")
    if d.automatisch and ds.status in ("manuell", "dienst"):
        fehler.append(f"{ort}: Status {ds.status} passt nicht zu download.art {d.art}")
    if not d.automatisch and ds.status in ("geprueft", "ungeprueft"):
        fehler.append(f"{ort}: Status {ds.status} braucht einen automatischen Download (art: {', '.join(AUTOMATISCH)})")


# -------------------------------------------------------------------- Laden

def _tupel(werte) -> tuple:
    return tuple(werte or ())


def _links(werte) -> tuple[Link, ...]:
    return tuple(Link(titel=w.get("titel", ""), url=w["url"]) for w in (werte or ()))


def _lese_yaml(pfad: Path):
    try:
        with open(pfad, encoding="utf-8") as datei:
            return yaml.safe_load(datei) or {}
    except yaml.YAMLError as fehler:
        raise KatalogFehler(f"{pfad.name} ist kein gültiges YAML: {fehler}") from None


def lade(ordner: Path | None = None, streng: bool = True) -> Katalog:
    """Liest den Katalog. Mit streng=True bricht ein fehlerhafter Katalog mit KatalogFehler ab."""
    ordner = Path(ordner) if ordner else pfade.katalog()
    try:
        lizenzen = {
            kennung: Lizenz(id=kennung, **werte) for kennung, werte in _lese_yaml(ordner / "lizenzen.yaml").items()
        }
        roh_quellen = _lese_yaml(ordner / "quellen.yaml")
        quellen = {}
        for q in roh_quellen.get("quellen", []):
            q = dict(q)
            for schluessel in ("themen", "zugang", "beispiele", "hinweise", "kontakt"):
                q[schluessel] = _tupel(q.get(schluessel))
            q["endpunkte"] = _links(q.get("endpunkte"))
            q["links"] = _links(q.get("links"))
            if q["id"] in quellen:
                raise KatalogFehler(f"Quelle {q['id']} steht doppelt in quellen.yaml")
            quellen[q["id"]] = Quelle(**q)
        luecken = [Luecke(**eintrag) for eintrag in roh_quellen.get("luecken", [])]
        datensaetze = {}
        for d in _lese_yaml(ordner / "datensaetze.yaml").get("datensaetze", []):
            d = dict(d)
            for schluessel in ("themen", "analysen", "begleitend", "hinweise"):
                d[schluessel] = _tupel(d.get(schluessel))
            download = dict(d.get("download") or {"art": "manuell"})
            eintraege = download.get("urls") or ()
            download["urls"] = tuple(e["url"] if isinstance(e, dict) else e for e in eintraege)
            download["namen"] = tuple(e.get("datei", "") if isinstance(e, dict) else "" for e in eintraege)
            d["download"] = Download(**download)
            d["dienste"] = tuple(
                Dienst(art=x["art"], url=x["url"], titel=x.get("titel", ""), ebenen=_tupel(x.get("ebenen")))
                for x in d.get("dienste") or ()
            )
            d["felder"] = dict(d.get("felder") or {})
            d["erklaerung"] = Erklaerung(**{k: str(v or "") for k, v in d["erklaerung"].items()}) \
                if d.get("erklaerung") else None
            if d["id"] in datensaetze:
                raise KatalogFehler(f"Datensatz {d['id']} steht doppelt in datensaetze.yaml")
            datensaetze[d["id"]] = Datensatz(**d)
    except TypeError as fehler:  # unbekanntes oder fehlendes Feld
        raise KatalogFehler(f"Unerwartetes oder fehlendes Feld im Katalog: {fehler}") from None
    except KeyError as fehler:
        raise KatalogFehler(f"Pflichtfeld fehlt im Katalog: {fehler}") from None
    katalog = Katalog(lizenzen=lizenzen, quellen=quellen, datensaetze=datensaetze, luecken=luecken, ordner=ordner)
    if streng:
        fehler, _ = katalog.pruefe()
        if fehler:
            raise KatalogFehler("Der Katalog enthält Fehler:\n- " + "\n- ".join(fehler))
    return katalog


# -------------------------------------------------------------------- Tabellen für die App

def lizenz_tabelle(katalog: Katalog) -> list[dict]:
    """Eine Zeile je Lizenz: Pflichten in Worten und wie viele Datensätze sie nutzen."""
    return [{"Lizenz": lz.kurz, "Namensnennung": "ja" if lz.namensnennung else "nein",
             "kommerziell": "ja" if lz.kommerziell else "nein oder unklar",
             "Datensätze": sum(ds.lizenz == lz.id for ds in katalog.datensaetze.values()), "Hinweis": lz.hinweis,
             "Text": lz.url} for lz in katalog.lizenzen.values()]


def quellen_filtern(katalog: Katalog, ebenen: list[str] | None = None,
                    themen: list[str] | None = None) -> list[Quelle]:
    return [q for q in katalog.quellen.values()
            if (not ebenen or q.ebene in ebenen) and (not themen or set(themen) & set(q.themen))]


def quellen_tabelle(katalog: Katalog, quellen: list[Quelle]) -> list[dict]:
    """Eine Zeile je Quelle für die Übersicht „Quellen und Portale“."""
    return [{"Quelle": q.name, "Ebene": EBENEN[q.ebene], "Themen": ", ".join(THEMEN[t] for t in q.themen),
             "Lizenz": katalog.lizenzen[q.lizenz].kurz, "Zugang": ", ".join(q.zugang),
             "Konto": KONTO.get(q.konto, q.konto), "Eignung": q.eignung,
             "Link": (q.links or q.endpunkte)[0].url if (q.links or q.endpunkte) else None,
             "Datensätze": sum(ds.quelle == q.id for ds in katalog.datensaetze.values())} for q in quellen]


def anbieter(katalog: Katalog, ds: Datensatz) -> str:
    """Wer die Daten herausgibt: Bereitsteller, sonst der Name der Quelle."""
    return ds.bereitsteller or katalog.quelle_von(ds).name


# -------------------------------------------------------------------- Quellenangaben

def quellenangabe(katalog: Katalog, ds: Datensatz, abgerufen: str | None = None, geaendert: bool = True) -> str:
    """Quellenangabe nach den Regeln der Lizenz, z. B. für Fußzeilen von Karten.

    `abgerufen` ist ein ISO-Datum. `geaendert` kennzeichnet bearbeitete Daten (bei Namensnennung Pflicht).
    """
    lizenz = katalog.lizenz_von(ds)
    jahr = (abgerufen or dt.date.today().isoformat())[:4]
    if ds.namensnennung:
        kopf = ds.namensnennung.replace("{jahr}", jahr)
    else:
        bereitsteller = ds.bereitsteller or katalog.quelle_von(ds).name
        lizenz_text = lizenz.kurz + (f" ({lizenz.url})" if lizenz.url else "")
        kopf = f"{bereitsteller}: {ds.titel}, {lizenz_text}"
    teile = [kopf, ds.seite]
    if abgerufen:
        teile.append(f"abgerufen am {'.'.join(reversed(abgerufen[:10].split('-')))}")
    if geaendert and lizenz.namensnennung:
        teile.append("Daten geändert")
    return ", ".join(teile)


# -------------------------------------------------------------------- Übersicht als Markdown

def als_markdown(katalog: Katalog) -> str:
    """Erzeugt docs/datenquellen.md. Nicht von Hand bearbeiten, sondern den Katalog ändern."""
    zahlen = katalog.zaehle()
    zeilen = [
        "# Datenquellen für Essen",
        "",
        "Diese Seite wird aus `katalog/` erzeugt: `uv run essen katalog --doku`. Änderungen bitte im Katalog machen.",
        "",
        f"Stand: {dt.date.today().strftime('%d.%m.%Y')} · {len(katalog.quellen)} Quellen · "
        f"{len(katalog.datensaetze)} Datensätze, davon {sum(ds.ladbar for ds in katalog.datensaetze.values())} "
        "automatisch ladbar.",
        "",
        "## Datensätze nach Thema",
        "",
        "Status: **geprüft** = Adresse bestätigt, **ungeprüft** = eingetragen, aber noch nicht bestätigt, "
        "**manuell** = von Hand laden und mit `essen einlesen` übernehmen, **Dienst** = nur Kartendienst.",
        "",
    ]
    status_kurz = {"geprueft": "geprüft", "ungeprueft": "ungeprüft", "manuell": "manuell", "dienst": "Dienst"}
    for thema, titel in THEMEN.items():
        liste = [ds for ds in katalog.datensaetze.values() if ds.themen and ds.themen[0] == thema]
        if not liste:
            continue
        zeilen += [f"### {titel}", "", "| Datensatz | Anbieter | Format | Lizenz | Status | Laden |", "| --- | --- | --- | --- | --- | --- |"]
        for ds in liste:
            lizenz = katalog.lizenz_von(ds)
            laden = f"`essen laden {ds.id}`" if ds.ladbar else ("–" if ds.download.art == "keiner" else "von Hand")
            groesse = f", {ds.download.groesse_mb:g} MB".replace(".", ",") if ds.download.groesse_mb else ""
            zeilen.append(
                f"| [{ds.titel}]({ds.seite}) | {ds.bereitsteller or katalog.quelle_von(ds).name} | "
                f"{ds.format}{groesse} | {lizenz.kurz} | {status_kurz[ds.status]} | {laden} |"
            )
        zeilen.append("")
    zeilen += ["## Quellen nach Ebene", ""]
    for ebene, titel in EBENEN.items():
        liste = [q for q in katalog.quellen.values() if q.ebene == ebene]
        if not liste:
            continue
        zeilen += [f"### {titel}", ""]
        for q in liste:
            lizenz = katalog.lizenzen[q.lizenz]
            link = (q.links or q.endpunkte or (None,))[0]
            name = f"[{q.name}]({link.url})" if link else q.name
            themen = ", ".join(THEMEN[t] for t in q.themen)
            zeilen.append(f"- **{name}**{' · ' + q.kurz if q.kurz else ''}. {q.beschreibung}")
            zeilen.append(f"  Themen: {themen}. Lizenz: {lizenz.kurz}"
                          f"{' (' + q.lizenz_hinweis + ')' if q.lizenz_hinweis else ''}. "
                          f"Zugang: {', '.join(q.zugang) or '–'}; {KONTO.get(q.konto, q.konto)}.")
            for hinweis in q.hinweise:
                zeilen.append(f"  - {hinweis}")
        zeilen.append("")
    if katalog.luecken:
        zeilen += ["## Lücken und offene Fragen", "", "| Art | Thema | Stand | Weg |", "| --- | --- | --- | --- |"]
        for luecke in katalog.luecken:
            zeilen.append(f"| {luecke.art} | {luecke.titel} | {luecke.text} | {luecke.weg} |")
        zeilen.append("")
    zeilen += ["## Lizenzen", "", "| Lizenz | Namensnennung | kommerziell | Hinweis |", "| --- | --- | --- | --- |"]
    for lizenz in katalog.lizenzen.values():
        if zahlen["lizenzen"].get(lizenz.id) or any(q.lizenz == lizenz.id for q in katalog.quellen.values()):
            name = f"[{lizenz.kurz}]({lizenz.url})" if lizenz.url else lizenz.kurz
            zeilen.append(f"| {name} | {'ja' if lizenz.namensnennung else 'nein'} | "
                          f"{'ja' if lizenz.kommerziell else 'nein oder unklar'} | {lizenz.hinweis} |")
    zeilen.append("")
    return "\n".join(zeilen)
