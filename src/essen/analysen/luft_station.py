"""Luftqualität an den Essener Messstationen: Jahresmittel von NO₂, PM₁₀ und PM₂,₅ seit 2010.

Grundlage sind die Jahresbilanzen des Umweltbundesamts (geprüfte Daten, alle Stationen in Deutschland) und
die Stationsliste. Essener Stationen werden über den Ort der Station gewählt. Für jedes Jahr: höchstes
Jahresmittel einer Essener Station, Mittel der Stationen und Wert je Station, verglichen mit dem EU-Grenzwert,
dem EU-Grenzwert ab 2030 und dem Richtwert der WHO von 2021.

Methodik: docs/methodik/luft-station.md
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from .. import laden
from ..geo import DatenFehlen
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte
from .hitze_nacht import ZuordnungFehlt

DATENSATZ = "uba-jahresbilanzen"
SCHADSTOFFE = {"no2": "Stickstoffdioxid (NO₂)", "pm10": "Feinstaub PM₁₀", "pm25": "Feinstaub PM₂,₅"}
# Jahresmittel in µg/m³: Richtlinie 2008/50/EG (gilt bis Ende 2029), Richtlinie (EU) 2024/2881 (ab 2030),
# WHO Air Quality Guidelines 2021.
GRENZWERTE = {
    "no2": {"eu": 40, "eu_2030": 20, "who": 10},
    "pm10": {"eu": 40, "eu_2030": 20, "who": 15},
    "pm25": {"eu": 25, "eu_2030": 10, "who": 5},
}
DATEI = re.compile(r"jahr_(\d{4})_(no2|pm10|pm25)\.json$")


def _lies(pfad) -> dict:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except ValueError as fehler:
        raise ZuordnungFehlt(f"{pfad.name} ist kein gültiges JSON: {fehler}") from None


def stationen_in_essen() -> pd.DataFrame:
    """Alle Stationen mit „Essen“ im Ort der Station, Spalten nach den Namen in indices (nicht nach Position)."""
    dateien = [p for p in laden.dateien(DATENSATZ, "stationen.json")]
    if not dateien:
        raise DatenFehlen([DATENSATZ])
    daten = _lies(dateien[0])
    namen = daten.get("indices") or []
    fehlt = [n for n in ("station id", "station code", "station name", "station city", "station active to")
             if n not in namen]
    if fehlt:
        raise ZuordnungFehlt(f"stationen.json: Felder {', '.join(fehlt)} fehlen in indices ({', '.join(namen)}).")
    tabelle = pd.DataFrame(list(daten["data"].values()), columns=namen[:len(next(iter(daten["data"].values())))])
    essen = tabelle[tabelle["station city"].fillna("").str.contains("Essen")]
    return essen.rename(columns={"station id": "id", "station code": "code", "station name": "name",
                                 "station active to": "aktiv_bis", "station type name": "typ"})[
        ["id", "code", "name", "aktiv_bis"] + (["typ"] if "station type name" in essen else [])].reset_index(drop=True)


def _spalten_aus_headers(headers: dict, datei: str) -> tuple[int, int | None]:
    """Index des Jahresmittels und der Überschreitungen laut headers der Antwort (E-009: nicht nach Position)."""
    mittel = [int(k) for k, v in headers.items() if str(v).startswith("Jahresmittelwert in µg/m³")]
    if len(mittel) != 1:
        raise ZuordnungFehlt(f"{datei}: kein eindeutiges Jahresmittel in headers ({headers}).")
    ueber = [int(k) for k, v in headers.items() if str(v).startswith("Zahl der") and "Abzug" not in str(v)]
    return mittel[0], (ueber[0] if ueber else None)


def jahreswerte(schadstoff: str) -> pd.DataFrame:
    """Lange Tabelle: jahr, code, name, wert_ug_m3, ueberschreitungen für die Essener Stationen."""
    stationen = stationen_in_essen()
    nach_id = stationen.set_index("id")
    zeilen = []
    for pfad in laden.dateien(DATENSATZ, f"jahr_*_{schadstoff}.json"):
        treffer = DATEI.search(pfad.name)
        if not treffer:
            continue
        daten = _lies(pfad)
        if not daten.get("data"):
            continue
        mittel, ueber = _spalten_aus_headers(daten.get("headers") or {}, pfad.name)
        for zeile in daten["data"]:
            if str(zeile[0]) not in nach_id.index:
                continue
            wert = pd.to_numeric(zeile[mittel], errors="coerce") if len(zeile) > mittel else np.nan
            anzahl = pd.to_numeric(zeile[ueber], errors="coerce") if ueber is not None and len(zeile) > ueber else np.nan
            station = nach_id.loc[str(zeile[0])]
            zeilen.append({"jahr": int(treffer.group(1)), "code": station["code"], "name": station["name"],
                           "wert_ug_m3": wert, "ueberschreitungen": anzahl})
    return pd.DataFrame(zeilen, columns=["jahr", "code", "name", "wert_ug_m3", "ueberschreitungen"])


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    schadstoff = p.get("schadstoff") or "no2"
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    lang = jahreswerte(schadstoff).dropna(subset=["wert_ug_m3"])
    if lang.empty:
        raise ZuordnungFehlt(f"Keine Jahreswerte für {SCHADSTOFFE[schadstoff]} an Essener Stationen gefunden.")
    kontext.melde(f"{SCHADSTOFFE[schadstoff]}: {lang['code'].nunique()} Essener Stationen, "
                  f"{lang['jahr'].min()} bis {lang['jahr'].max()}")
    grenzen = GRENZWERTE[schadstoff]
    gruppen = lang.groupby("jahr")
    tabelle = pd.DataFrame({
        "hoechstes_jahresmittel_ug_m3": gruppen["wert_ug_m3"].max(),
        "mittel_stationen_ug_m3": gruppen["wert_ug_m3"].mean().round(1),
        "stationen": gruppen["code"].nunique(),
        "stationen_ueber_eu": gruppen["wert_ug_m3"].apply(lambda w: int((w > grenzen["eu"]).sum())),
        "stationen_ueber_eu_2030": gruppen["wert_ug_m3"].apply(lambda w: int((w > grenzen["eu_2030"]).sum())),
        "stationen_ueber_who": gruppen["wert_ug_m3"].apply(lambda w: int((w > grenzen["who"]).sum())),
    })
    hoechste = lang.loc[lang.groupby("jahr")["wert_ug_m3"].idxmax()].set_index("jahr")
    tabelle["station_hoechstwert"] = hoechste["name"] + " (" + hoechste["code"] + ")"
    breit = lang.pivot_table(index="jahr", columns="code", values="wert_ug_m3", aggfunc="first")
    tabelle = tabelle.join(breit.add_prefix("wert_"))
    tabelle["vollstaendig"] = True  # Jahresbilanzen beruhen auf geprüften, abgeschlossenen Jahren
    tabelle = tabelle.reset_index()

    letzte = tabelle.iloc[-1]
    text = (f"{SCHADSTOFFE[schadstoff]} {int(letzte['jahr'])}: höchstes Jahresmittel {zahl(letzte['hoechstes_jahresmittel_ug_m3'])} "
            f"µg/m³ ({letzte['station_hoechstwert']}). Grenzwert {grenzen['eu']}, ab 2030 {grenzen['eu_2030']}, "
            f"WHO-Richtwert {grenzen['who']} µg/m³.")
    kontext.melde(text)
    erstes = tabelle[tabelle["stationen_ueber_eu"] == 0]["jahr"]
    hinweise = [
        f"Stationen über dem Grenzwert von {grenzen['eu']} µg/m³ je Jahr: "
        + ", ".join(f"{int(z.jahr)}: {int(z.stationen_ueber_eu)}" for z in tabelle.itertuples() if z.stationen_ueber_eu)
        + "." if (tabelle["stationen_ueber_eu"] > 0).any() else
        f"Keine Essener Station lag seit {int(tabelle['jahr'].min())} über dem Grenzwert von {grenzen['eu']} µg/m³.",
        f"{int(letzte['jahr'])} lagen {int(letzte['stationen_ueber_eu_2030'])} von {int(letzte['stationen'])} Stationen über "
        f"dem Grenzwert ab 2030 ({grenzen['eu_2030']} µg/m³) und {int(letzte['stationen_ueber_who'])} über dem "
        f"WHO-Richtwert ({grenzen['who']} µg/m³).",
        "Stationen messen an ihrem Ort, oft an stark befahrenen Straßen (Verkehrsstationen). Die Werte gelten nicht "
        "für ganze Stadtteile. Die Zahl der Stationen ändert sich über die Jahre; das höchste Jahresmittel hängt "
        "auch davon ab, welche Stationen gerade messen.",
        "Jahresbilanzen des Umweltbundesamts auf geprüften Daten; das Vorjahr ist ab Juni vollständig.",
    ]
    if len(erstes) and (tabelle["stationen_ueber_eu"] > 0).any():
        hinweise.append(f"Seit {int(erstes[erstes > tabelle.loc[tabelle['stationen_ueber_eu'] > 0, 'jahr'].max()].min())} "
                        f"liegt keine Station mehr über {grenzen['eu']} µg/m³."
                        if (erstes > tabelle.loc[tabelle["stationen_ueber_eu"] > 0, "jahr"].max()).any() else
                        "Im letzten Jahr lag noch eine Station über dem Grenzwert.")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        kennzahl_stadt=float(letzte["hoechstes_jahresmittel_ug_m3"]),
        kennzahl_text=text,
        hinweise=hinweise,
        quellen=[DATENSATZ],
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="luft-station",
    titel="Luftqualität an den Essener Messstationen",
    frage="Wie haben sich Stickstoffdioxid und Feinstaub an den Essener Messstationen entwickelt, gemessen an den Grenzwerten?",
    themen=("luft",),
    benoetigt=(DATENSATZ,),
    rechne=rechne,
    raumbezug="station",
    kennzahl="hoechstes_jahresmittel_ug_m3",
    kennzahl_titel="Höchstes Jahresmittel einer Essener Station (µg/m³)",
    einheit="µg/m³",
    spalten=(
        Spalte("jahr", "Jahr", "text"),
        Spalte("hoechstes_jahresmittel_ug_m3", "höchstes Jahresmittel", "zahl", balken=True),
        Spalte("mittel_stationen_ug_m3", "Mittel der Stationen", "zahl", stellen=1),
        Spalte("stationen", "Stationen", "zahl"),
        Spalte("stationen_ueber_eu", "über Grenzwert", "zahl"),
        Spalte("stationen_ueber_eu_2030", "über Grenzwert ab 2030", "zahl"),
        Spalte("station_hoechstwert", "Station mit dem höchsten Wert", "text"),
    ),
    parameter=(
        Parameter("schadstoff", "Schadstoff", "no2",
                  "Stickstoffdioxid stammt vor allem aus dem Verkehr. Feinstaub PM₁₀ und die noch feineren Teilchen "
                  "PM₂,₅ kommen aus Verkehr, Heizungen, Industrie und Landwirtschaft.", tuple(SCHADSTOFFE), "wahl",
                  beschriftungen={"no2": "Stickstoffdioxid (NO₂)", "pm10": "Feinstaub PM₁₀",
                                  "pm25": "Feinstaub PM₂,₅ (feinere Teilchen)"}),
    ),
    methodik="methodik/luft-station.md",
    thema_titel="Luftqualität",
    kurz="Wie viel Stickstoffdioxid und Feinstaub messen die Essener Stationen im Jahresmittel, und wie liegt das zu den Grenzwerten?",
    richtung="hoch_schlecht",
    lesehilfe="Je Jahr zeigt der Balken den höchsten Jahresmittelwert einer Essener Messstation. Liegt er unter dem Grenzwert, halten alle Stationen den Grenzwert ein. Der strengere Grenzwert ab 2030 und der Richtwert der Weltgesundheitsorganisation zeigen, was noch zu tun ist.",
    grenzen_kurz=(
        "Viele Stationen stehen an stark befahrenen Straßen; anderswo ist die Luft meist besser.",
        "Welche Stationen messen, wechselt über die Jahre.",
        "Nur abgeschlossene, geprüfte Jahre; das Vorjahr gibt es ab Juni.",
    ),
)
