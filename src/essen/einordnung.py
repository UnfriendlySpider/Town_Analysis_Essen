"""Zahlen in Sätze übersetzen: Wie steht ein Stadtteil im Vergleich da, was bedeutet eine Korrelation?

Berücksichtigt die Richtung einer Analyse (hoch_schlecht, hoch_gut, neutral), damit „Rang 1“ nicht als gut
missverstanden wird, wenn es um Hitze geht.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .analysen.basis import Analyse
from .text import zahl

STUFEN_TEXT = {
    "deutlich_schlechter": "ungünstiger als die meisten Stadtteile",
    "schlechter": "etwas ungünstiger als der Durchschnitt",
    "mittel": "im Mittelfeld",
    "besser": "etwas günstiger als der Durchschnitt",
    "deutlich_besser": "günstiger als die meisten Stadtteile",
    "hoch": "unter den höchsten Werten",
    "eher_hoch": "eher hoch",
    "eher_niedrig": "eher niedrig",
    "niedrig": "unter den niedrigsten Werten",
}


@dataclass(frozen=True)
class Einordnung:
    stufe: str      # Schlüssel aus STUFEN_TEXT
    text: str       # kurze Einordnung, z. B. „ungünstiger als die meisten Stadtteile“
    farbe: str      # red | orange | gray | blue | green (für Abzeichen in der App)
    satz: str       # ganzer Satz für Menschen


def _fuenftel(rang: int, von: int) -> int:
    """1 = oberstes Fünftel (höchste Werte) … 5 = unterstes Fünftel."""
    return min(5, 1 + int(5 * (rang - 1) / max(von, 1)))


def einheit_text(einheit: str, wert: float) -> str:
    """„Themen“ wird bei genau 1 zu „Thema“; sonst bleibt die Einheit."""
    return "Thema" if einheit == "Themen" and round(wert) == 1 else einheit


def einordnen(analyse: Analyse, name: str, wert: float | None, rang: int | None, von: int,
              mittel: float | None, rang_mitte: float | None = None) -> Einordnung | None:
    """Einordnung eines Stadtteilwerts. None, wenn es keinen Wert gibt.

    Bei Gleichstand (z. B. 15 Stadtteile mit genau einem Thema) zählt der mittlere Rang der Gleichen, damit ein
    Stadtteil nicht wegen geteilter Plätze als besonders belastet erscheint."""
    if wert is None or rang is None or (isinstance(wert, float) and math.isnan(wert)):
        return None
    fuenftel = _fuenftel(round(rang_mitte) if rang_mitte else rang, von)
    if analyse.richtung == "neutral":
        stufe = {1: "hoch", 2: "eher_hoch", 3: "mittel", 4: "eher_niedrig", 5: "niedrig"}[fuenftel]
        farbe = "gray"
    else:
        schlecht_oben = analyse.richtung == "hoch_schlecht"
        reihenfolge = ["deutlich_schlechter", "schlechter", "mittel", "besser", "deutlich_besser"]
        stufe = reihenfolge[fuenftel - 1] if schlecht_oben else reihenfolge[5 - fuenftel]
        farbe = {"deutlich_schlechter": "red", "schlechter": "orange", "mittel": "gray", "besser": "blue",
                 "deutlich_besser": "green"}[stufe]
    stellen = analyse.stellen
    einheit = f" {einheit_text(analyse.einheit, wert)}" if analyse.einheit else ""
    vergleich = ""
    if mittel is not None and not (isinstance(mittel, float) and math.isnan(mittel)):
        if abs(wert - mittel) < 0.05 * max(abs(mittel), 1e-9) or (stellen == 0 and round(wert) == round(mittel)):
            vergleich = f", etwa so viel wie im Mittel der Stadtteile ({zahl(mittel, stellen)}{einheit})"
        else:
            richtung = "mehr" if wert > mittel else "weniger"
            vergleich = f", {richtung} als im Mittel der Stadtteile ({zahl(mittel, stellen)}{einheit})"
    hoeher = rang - 1
    if hoeher == 0:
        platz = f"Kein anderer der {von} Stadtteile hat einen höheren Wert."
    elif hoeher == von - 1:
        platz = f"Alle anderen {hoeher} Stadtteile haben einen höheren Wert."
    else:
        platz = f"{hoeher} von {von} Stadtteilen haben einen höheren Wert."
    satz = f"{name}: {zahl(wert, stellen)}{einheit}{vergleich}. {platz}"
    return Einordnung(stufe, STUFEN_TEXT[stufe], farbe, satz)


def korrelation_in_worten(r: float | None) -> str:
    """Pearson-r als Satz für Menschen."""
    if r is None or math.isnan(r):
        return "Zu wenige Stadtteile mit beiden Werten, um einen Zusammenhang zu beurteilen."
    staerke = ("sehr eng" if abs(r) >= 0.9 else "deutlich" if abs(r) >= 0.6 else "schwach" if abs(r) >= 0.3
               else "kaum")
    if abs(r) < 0.3:
        return f"Die beiden Werte hängen kaum zusammen (r = {zahl(r, 2)}): Ein hoher Wert beim einen sagt wenig über den anderen."
    if r > 0:
        art = "Stadtteile mit hohem Wert beim einen haben meist auch beim anderen einen hohen Wert"
    else:
        art = "Stadtteile mit hohem Wert beim einen haben meist beim anderen einen niedrigen Wert"
    zusatz = " Sie messen fast dasselbe." if abs(r) >= 0.9 else ""
    return f"Die beiden Werte hängen {staerke} zusammen (r = {zahl(r, 2)}): {art}.{zusatz}"


def richtung_text(analyse: Analyse) -> str:
    """Kurzer Satz, wie Farbe und Zahl zu lesen sind."""
    return {
        "hoch_schlecht": "Höhere Werte und dunklere Farben bedeuten mehr Belastung – also ungünstiger.",
        "hoch_gut": "Höhere Werte und dunklere Farben sind hier günstig.",
    }.get(analyse.richtung, "Höhere Werte und dunklere Farben bedeuten mehr davon; das ist weder gut noch schlecht.")


FUSSBALLFELD_HA = 0.714  # 105 m × 68 m, Maß der FIFA für internationale Spiele


def flaeche_alltag(hektar: float | None) -> str:
    """Fläche zum Vorstellen: „etwa so groß wie 120 Fußballfelder“ (ab 1 Feld), sonst leer."""
    if hektar is None or (isinstance(hektar, float) and math.isnan(hektar)):
        return ""
    felder = hektar / FUSSBALLFELD_HA
    if felder < 1:
        return ""
    gerundet = round(felder) if felder < 20 else round(felder, -1) if felder < 1000 else round(felder, -2)
    return f"etwa so groß wie {zahl(gerundet)} Fußballfeld{'er' if gerundet != 1 else ''}"


def menschen_ungefaehr(anzahl: int | float | None) -> str:
    """Einwohnerzahl gerundet, damit die Schätzung nicht genauer wirkt, als sie ist: 3.912 → „etwa 3.900“."""
    if anzahl is None or (isinstance(anzahl, float) and math.isnan(anzahl)):
        return "–"
    stelle = -1 if anzahl < 1000 else -2 if anzahl < 100_000 else -3
    return f"etwa {zahl(round(anzahl, stelle))}"


EINWOHNER_HILFE = ("Modellschätzung aus der Volkszählung 2022 (100-m-Gitter). Sie sagt, wie viele Menschen in den "
                   "belasteten Flächen wohnen, nicht, wie viele selbst belastet sind.")


def einwohner_satz(belastet: float, einwohner: float, im_stadtteil: bool = False) -> str:
    """Satz zu den geschätzten Einwohnern in belasteten Flächen (E-013), gerundet, damit er nicht zu genau wirkt."""
    anteil = zahl(100 * belastet / einwohner) if einwohner else "–"
    if im_stadtteil:
        return (f":material/groups: Geschätzt wohnen **{menschen_ungefaehr(belastet)}** von "
                f"{menschen_ungefaehr(einwohner)} Menschen im Stadtteil in solchen Flächen ({anteil} %).")
    return (f":material/groups: Geschätzt wohnen **{menschen_ungefaehr(belastet)} Menschen** ({anteil} % der "
            "Einwohner) in diesen Flächen.")


def richtung_wort(wert: float) -> str:
    """„mehr“ oder „weniger“ für einen Trend oder eine Differenz."""
    return "mehr" if wert > 0 else "weniger"


def frueher_heute_satz(reihe: str, art: str, frueher: float, heute: float, von: int, bis: int, letzte: int) -> str:
    """„In Rüttenscheid gab es 2016–2025 im Schnitt 10,6 heiße Tage im Jahr, 1961–1990 waren es 4,3 – also
    etwa zweieinhalbmal so viele.“ `art` ist z. B. „heiße Tage“; bei „°C“ wird die Temperatur verglichen."""
    ort = "in ganz Essen" if reihe == "Essen gesamt" else f"an der {reihe}" if reihe.startswith("Messstation") \
        else f"in {reihe}"
    zeitraum = f"{letzte - 9}–{letzte}"
    if art == "°C":
        unterschied = heute - frueher
        richtung = "wärmer" if unterschied > 0 else "kühler"
        return (f"{zeitraum} lag die Jahresmitteltemperatur {ort} bei {zahl(heute, 1)} °C, {von}–{bis} bei "
                f"{zahl(frueher, 1)} °C – also {zahl(abs(unterschied), 1)} Grad {richtung}.")
    satz = f"{zeitraum} gab es {ort} im Schnitt {zahl(heute, 1)} {art} im Jahr, {von}–{bis} waren es {zahl(frueher, 1)}"
    if frueher > 0 and heute / frueher >= 1.5:
        faktor = heute / frueher
        halb = round(faktor * 2) / 2
        wort = {1.5: "anderthalbmal", 2: "doppelt", 2.5: "zweieinhalbmal", 3: "dreimal", 3.5: "dreieinhalbmal",
                4: "viermal"}.get(halb, f"{zahl(faktor, 1)}-mal")
        return satz + f" – {'etwa ' if abs(faktor - halb) > 0.05 else ''}{wort} so viele."
    if heute > frueher:
        return satz + f" – {zahl(heute - frueher, 1)} mehr."
    return satz + "."
