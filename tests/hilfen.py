"""Kleine Kataloge für Tests, die einen lokalen Server statt echter Anbieter nutzen."""

from essen.katalog import Datensatz, Katalog, Lizenz, Quelle


def mini_katalog(*datensaetze):
    lizenz = Lizenz(id="dl-de-zero-2.0", name="Zero", kurz="DL-DE Zero 2.0", namensnennung=False)
    quelle = Quelle(id="test", name="Testquelle", ebene="stadt", themen=("geo",), beschreibung="", lizenz=lizenz.id)
    return Katalog(lizenzen={lizenz.id: lizenz}, quellen={quelle.id: quelle}, datensaetze={d.id: d for d in datensaetze})


def datensatz(kennung, download, **weitere):
    return Datensatz(id=kennung, titel=kennung, quelle="test", themen=("geo",), beschreibung="", lizenz="dl-de-zero-2.0",
                     seite="https://example.org/", download=download, status="ungeprueft", **weitere)
