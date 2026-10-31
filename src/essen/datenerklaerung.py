"""Datensätze in Worten: Steckbrief für Menschen ohne Vorwissen (App-Seite „Daten erklärt“, docs/daten-erklaert.md).

Die Texte stehen im Katalog unter `erklaerung` (herkunft, inhalt, nutzen, lesen). Dieses Modul ergänzt sie um
Angaben, die der Katalog ohnehin kennt: Anbieter, Lizenz in einem Satz, Raumbezug, Stand, Themen der App.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from . import analysen
from .katalog import THEMEN, Datensatz, Katalog, Lizenz


@dataclass(frozen=True)
class Steckbrief:
    kennung: str
    titel: str
    kurz: str                                   # die Beschreibung aus dem Katalog, ein bis zwei Sätze
    anbieter: str                               # wer die Daten herausgibt
    portal: str                                 # über welches Portal sie kommen
    portal_text: str
    lizenz: str                                 # ein Satz für Menschen
    raum: str
    stand: str
    bezug: str                                  # wie die App an die Daten kommt, in einem Satz
    themen: list[tuple[str, str]] = field(default_factory=list)   # (Analyse-ID, Thementitel) der App
    abschnitte: list[tuple[str, str]] = field(default_factory=list)  # (Überschrift, Text)
    seite: str = ""

    @property
    def ausfuehrlich(self) -> bool:
        return bool(self.abschnitte)


def lizenz_satz(lizenz: Lizenz) -> str:
    """Die Lizenz in einem Satz: was man darf und was man bei einer Weitergabe beachten muss."""
    if lizenz.pruefen:
        return f"Die Nutzungsrechte sind nicht abschließend geklärt ({lizenz.kurz}); vor einer Weitergabe prüfen."
    if not lizenz.namensnennung:
        satz = "Frei nutzbar, auch gewerblich und ohne Quellenangabe"
    elif lizenz.kommerziell:
        satz = "Frei nutzbar, auch gewerblich; wer Daten oder Ergebnisse weitergibt, nennt Quelle und Lizenz"
    else:
        satz = "Nutzbar mit Quellenangabe; ob gewerbliche Nutzung erlaubt ist, steht in der Lizenz"
    if lizenz.gleiche_bedingungen:
        satz += ". Veränderte Daten nur unter derselben Lizenz weitergeben"
    return f"{satz} ({lizenz.kurz})."


def bezug_satz(ds: Datensatz) -> str:
    """Wie die App an die Daten kommt."""
    if ds.download.art == "keiner":
        return "Nur als Karte der Behörde zum Ansehen; die App lädt nichts herunter."
    if not ds.ladbar:
        return "Muss von Hand bei der Quelle geladen und in der Werkstatt übernommen werden."
    if ds.status == "ungeprueft":
        return "Die App kann ihn laden; die Download-Adresse ist aber noch nicht bestätigt."
    return "Die App lädt ihn auf Knopfdruck direkt bei der Quelle."


def steckbrief(katalog: Katalog, ds: Datensatz) -> Steckbrief:
    quelle = katalog.quelle_von(ds)
    return Steckbrief(
        kennung=ds.id, titel=ds.titel, kurz=ds.beschreibung.strip(), anbieter=ds.bereitsteller or quelle.name,
        portal=quelle.name, portal_text=quelle.beschreibung.strip(), lizenz=lizenz_satz(katalog.lizenz_von(ds)),
        raum=ds.raumbezug, stand=ds.stand, bezug=bezug_satz(ds),
        themen=[(a.id, a.thema_titel or a.titel) for a in analysen.nutzer(ds.id)],
        abschnitte=ds.erklaerung.abschnitte() if ds.erklaerung else [], seite=ds.seite)


def nach_thema(katalog: Katalog, suche: str = "") -> dict[str, list[Datensatz]]:
    """Datensätze nach ihrem ersten Thema (Titel → Liste), wahlweise gefiltert nach einem Suchwort im Text."""
    wort = suche.strip().lower()
    gruppen: dict[str, list[Datensatz]] = {}
    for kennung, titel in THEMEN.items():
        liste = [ds for ds in katalog.datensaetze.values() if ds.themen and ds.themen[0] == kennung
                 and (not wort or wort in _volltext(katalog, ds))]
        if liste:
            gruppen[titel] = liste
    return gruppen


def _volltext(katalog: Katalog, ds: Datensatz) -> str:
    teile = [ds.titel, ds.beschreibung, ds.bereitsteller, katalog.quelle_von(ds).name]
    if ds.erklaerung:
        teile += [text for _, text in ds.erklaerung.abschnitte()]
    return " ".join(teile).lower()


def als_markdown(katalog: Katalog) -> str:
    """Erzeugt docs/daten-erklaert.md. Nicht von Hand bearbeiten, sondern `erklaerung` im Katalog ändern."""
    zeilen = ["# Daten erklärt", "",
              "Jeder Datensatz in Worten: woher er kommt, was drinsteht, wofür man ihn nutzen kann und wie man ihn "
              "liest. Diese Seite wird aus `katalog/` erzeugt: `uv run essen katalog --doku`.", "",
              f"Stand: {dt.date.today().strftime('%d.%m.%Y')}", ""]
    for titel, liste in nach_thema(katalog).items():
        zeilen += [f"## {titel}", ""]
        for ds in liste:
            s = steckbrief(katalog, ds)
            zeilen += [f"### {s.titel}", "", f"*{s.anbieter} · {s.lizenz}*", ""]
            if not s.ausfuehrlich:
                zeilen += [s.kurz, ""]
            for ueberschrift, text in s.abschnitte:
                zeilen += [f"**{ueberschrift}** {text}", ""]
            if s.themen:
                zeilen += ["Genutzt in den Themen: " + ", ".join(t for _, t in s.themen) + ".", ""]
    return "\n".join(zeilen)
