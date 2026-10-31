"""Lärmbelastung je Stadtteil.

Grundlage ist die Lärmkarte der Stadt Essen (Umgebungslärm, Straßen 2011, Schiene, Ruhrbahn und
Industrieanlagen 2016), je Quelle und Zeitraum eine Datei mit Isophonen-Flächen in 5-dB-Stufen. Für jeden
Stadtteil: welcher Anteil der Fläche liegt nachts (L_Night) oder ganztags (L_DEN) über der Schwelle, und
zwar durch mindestens eine Quelle? Pegel verschiedener Quellen werden nicht addiert.

Welche Datei je Quelle gelesen wird und welches Feld den Pegel trägt, steht in
katalog/zuordnungen/laermkarte-essen.yaml. Methodik: docs/methodik/laerm.md
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .. import einwohner, kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_im_stadtgebiet
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen
from .hitze_nacht import ZuordnungFehlt, lade_zuordnung

DATENSATZ = "laermkarte-essen"
ZEITRAEUME = {"nacht": "nachts (L_Night, 22 bis 6 Uhr)", "ganztags": "ganztags (L_DEN, gewichtet über 24 Stunden)"}
# Auslösewerte der ersten Stufe für die Lärmaktionsplanung laut Umweltbundesamt: 65 dB(A) L_DEN, 55 dB(A) L_Night.
SCHWELLE_STANDARD = {"nacht": 55, "ganztags": 65}
SCHWELLEN = ("standard", "55", "60", "65", "70")  # ab 55 dB(A) sind alle acht Dateien vollständig
PEGEL_MOEGLICH = range(35, 90, 5)

STUFEN = Stufen(
    grenzen=(0, 10, 20, 30, 40),
    farben=FARBSTUFEN["waerme"],
    texte=("unter 10 %", "10 bis 20 %", "20 bis 30 %", "30 bis 40 %", "40 % und mehr"),
    keine_daten_text="zu wenig Fläche, kein Anteil",
)


def _zuordnung() -> dict:
    zuordnung = lade_zuordnung(DATENSATZ)
    if not zuordnung or not zuordnung.get("quellen"):
        raise ZuordnungFehlt(f"katalog/zuordnungen/{DATENSATZ}.yaml fehlt oder hat keine quellen "
                             "(welche Datei je Quelle und Zeitraum, welches Feld den Pegel trägt).")
    for name, quelle in zuordnung["quellen"].items():
        fehlt = [k for k in ("titel", "feld", *ZEITRAEUME) if not quelle.get(k)]
        if fehlt:
            raise ZuordnungFehlt(f"{zuordnung['_pfad']}: Quelle {name} braucht {', '.join(fehlt)}.")
    return zuordnung


def schwelle_db(zeitraum: str, wahl) -> int:
    wahl = str(wahl or "standard")
    if wahl == "standard":
        return SCHWELLE_STANDARD[zeitraum]
    if wahl not in SCHWELLEN:
        raise ValueError(f"Schwelle {wahl} dB(A) nicht möglich (Auswahl: {', '.join(SCHWELLEN)}).")
    return int(wahl)


def untergrenzen(werte: pd.Series) -> pd.Series:
    """Pegel der Isophonen-Flächen → Untergrenze in ganzen dB (DB schreibt 55,01 für „über 55“)."""
    return np.floor(pd.to_numeric(werte, errors="coerce") + 1e-6)


def flaeche_ueber(pfad, feld: str, schwelle: int, ort: str):
    """Vereinigte Fläche aller Isophonen mit Untergrenze ab der Schwelle (EPSG:25832, 2D)."""
    flaechen = lies_im_stadtgebiet(pfad)
    if feld not in flaechen.columns:
        raise ZuordnungFehlt(f"{ort}: Feld {feld} fehlt in {pfad.name} (vorhanden: {', '.join(flaechen.columns)}).")
    stufe = untergrenzen(flaechen[feld])
    unbekannt = sorted(set(stufe.dropna().astype(int)) - set(PEGEL_MOEGLICH))
    if stufe.isna().any() or unbekannt:
        raise ZuordnungFehlt(f"{ort}: {pfad.name}.{feld} hat unerwartete Werte "
                             f"({', '.join(map(str, unbekannt)) or 'leer'}); erwartet 5-dB-Stufen.")
    auswahl = flaechen[stufe >= schwelle].to_crs(ZIEL_CRS)
    if auswahl.empty:
        return None, flaechen
    geometrie = shapely.force_2d(auswahl.geometry.make_valid().to_numpy())
    return shapely.union_all(geometrie), flaechen


def _datei(name: str, ort: str):
    vorhanden = [p for p in laden.entpackt(DATENSATZ) if p.suffix.lower() == ".shp"]
    treffer = [p for p in vorhanden if p.name.lower() == name.lower()]
    if not treffer:
        raise ZuordnungFehlt(f"{ort}: Datei {name} fehlt im Datensatz. Vorhanden: "
                             f"{', '.join(sorted(p.name for p in vorhanden)) or 'keine'}. "
                             f"Alle Dateien laden: uv run essen laden {DATENSATZ} --neu")
    return treffer[0]


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    zeitraum = p.get("zeitraum") or "nacht"
    if zeitraum not in ZEITRAEUME:
        raise ValueError(f"Unbekannter Zeitraum „{zeitraum}“ ({', '.join(ZEITRAEUME)}).")
    schwelle = schwelle_db(zeitraum, p.get("schwelle_db"))
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    zuordnung = _zuordnung()
    quellen = zuordnung["quellen"]
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    melde(f"Über {schwelle} dB(A) {ZEITRAEUME[zeitraum]}")

    teile = {}
    for name, quelle in quellen.items():
        pfad = _datei(str(quelle[zeitraum]), zuordnung["_pfad"])
        geometrie, alle = flaeche_ueber(pfad, quelle["feld"], schwelle, zuordnung["_pfad"])
        melde(f"  {quelle['titel']}: {pfad.name}, {zahl(len(alle))} Flächen")
        if geometrie is not None:
            teile[name] = geometrie
    gesamt = shapely.union_all(list(teile.values())) if teile else None
    zeilen = [{"klasse": k, "geometry": g} for k, g in teile.items()]
    if gesamt is not None:
        zeilen.append({"klasse": "gesamt", "geometry": gesamt})
    klassen = [*quellen, "gesamt"]
    if zeilen:
        melde("Verschneide mit den Stadtteilen …")
        flaechen = kennzahlen.flaechen_nach_klasse(
            gebiete, gpd.GeoDataFrame(zeilen, geometry="geometry", crs=ZIEL_CRS), klassen)
    else:
        flaechen = pd.DataFrame(0.0, index=gebiete["gebiet_id"], columns=klassen)

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    flaeche = tabelle["flaeche_ha"].where(tabelle["flaeche_ha"] > 0)
    tabelle["laut_ha"] = (flaechen["gesamt"] / 1e4).reindex(tabelle.index).fillna(0.0)
    tabelle["anteil_laut_pct"] = 100 * tabelle["laut_ha"] / flaeche
    for name in quellen:
        tabelle[f"{name}_pct"] = 100 * (flaechen[name] / 1e4).reindex(tabelle.index).fillna(0.0) / flaeche
    minimum = float(p["min_flaeche_ha"])
    spalten = ["anteil_laut_pct", *(f"{n}_pct" for n in quellen)]
    tabelle = kennzahlen.mindestbezug(tabelle, "flaeche_ha", minimum, spalten,
                                      f"unter {minimum:g} ha Fläche, kein Anteil ausgewiesen")
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha"))})

    hinweise = list(stadtteile.hinweise)
    if einwohner.vorhanden():
        melde("Schätze die Einwohner in lauter Fläche (Zensus-Gitter) …")
        teile = gpd.GeoDataFrame(geometry=[gesamt] if gesamt is not None else [], crs=ZIEL_CRS).explode(ignore_index=True)
        tabelle, satz = einwohner.ergaenze(tabelle, einwohner.in_flaeche(gebiete, teile))
        hinweise.append(f"{satz[:-1]} wohnen in Fläche über der Schwelle. {einwohner.HINWEIS}")
    mit_wert = tabelle.dropna(subset=["anteil_laut_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_laut_pct"], mit_wert["flaeche_ha"])
    text = ("Kein Stadtteil mit genug Fläche." if stadtweit is None else
            f"Stadtweit liegen {zahl(stadtweit, 1)} % der Fläche {ZEITRAEUME[zeitraum].split(' (')[0]} "
            f"über {schwelle} dB(A), durch mindestens eine Quelle.")
    melde(text)

    if not zuordnung.get("geprueft", False):
        hinweise.append(f"Die Zuordnung {zuordnung['_pfad']} ist noch nicht als geprüft markiert.")
    staende = ", ".join(f"{q['titel']} {q.get('stand', '?')}" for q in quellen.values())
    hinweise += [
        f"Stand der Lärmkarten: {staende}. Neuere Kartierungen für Essen sind im Portal nicht zu finden; Verkehr und "
        "Bebauung haben sich seitdem verändert.",
        "Lärmkarten sind Modellrechnungen, keine Messungen. Pegel verschiedener Quellen werden "
        "nicht addiert: gezählt wird die Fläche, an der mindestens eine Quelle über der Schwelle liegt. Die "
        "Gesamtbelastung kann deshalb höher sein.",
        "Die Kennzahl bezieht sich auf die ganze Fläche des Stadtteils, nicht auf die Zahl der Betroffenen (E-007).",
    ]
    abgeleitet = [q["titel"] for q in quellen.values() if q.get("lesart_abgeleitet")]
    if abgeleitet:
        hinweise.append(f"Bei {', '.join(abgeleitet)} ist der Pegelwert als Untergrenze der Stufe gelesen; das folgt "
                        "aus dem gleichen Dateiaufbau wie bei den Straßen, nicht aus einer Legende.")
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise + [f"Dateien und Felder aus der Zuordnung {zuordnung['_pfad']}."],
        quellen=[stadtteile.datensatz, DATENSATZ],
        parameter={**dict(p), "schwelle_genutzt_db": schwelle},
    )


ANALYSE = Analyse(
    id="laerm",
    gewicht="flaeche_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Lärmbelastung je Stadtteil",
    frage="Welcher Anteil der Fläche eines Stadtteils liegt nachts oder ganztags über der Lärmschwelle?",
    themen=("laerm",),
    benoetigt=("stadtteile", DATENSATZ),
    optional=(einwohner.DATENSATZ,),
    rechne=rechne,
    kennzahl="anteil_laut_pct",
    kennzahl_titel="Anteil der Fläche über der Lärmschwelle",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_laut_pct", "über der Schwelle", "prozent", balken=True),
        Spalte("strasse_pct", "Straße", "prozent"),
        Spalte("schiene_db_pct", "Eisenbahn", "prozent"),
        Spalte("ruhrbahn_pct", "Ruhrbahn", "prozent"),
        Spalte("industrie_pct", "Industrie", "prozent"),
        Spalte("anteil_einwohner_pct", "Einwohner betroffen", "prozent"),
    ),
    parameter=(
        Parameter("zeitraum", "Tageszeit", "nacht",
                  "Nachts stört Lärm besonders, weil er den Schlaf unterbricht. „Über den ganzen Tag“ ist ein "
                  "Mittel über 24 Stunden, in dem Abend und Nacht stärker zählen.", tuple(ZEITRAEUME), "wahl",
                  beschriftungen={"nacht": "nachts (22 bis 6 Uhr)", "ganztags": "über den ganzen Tag"}),
        Parameter("schwelle_db", "Ab wie laut?", "standard",
                  "Empfohlen sind die Werte, ab denen laut Umweltbundesamt Lärmschutz geplant werden sollte: "
                  "nachts 55, über den ganzen Tag 65 Dezibel. 10 Dezibel mehr klingen etwa doppelt so laut.",
                  SCHWELLEN, "wahl",
                  beschriftungen={"standard": "empfohlen (nachts 55, ganztags 65 dB(A))", "55": "ab 55 dB(A)",
                                  "60": "ab 60 dB(A)", "65": "ab 65 dB(A)", "70": "ab 70 dB(A)"}),
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken könnte.", typ="zahl",
                  selten=True),
    ),
    methodik="methodik/laerm.md",
    thema_titel="Lärm",
    kurz="Wie viel Fläche ist so laut, dass es auf Dauer die Gesundheit belasten kann?",
    richtung="hoch_schlecht",
    lesehilfe="Gefärbt nach dem Anteil der Fläche, auf der mindestens eine Lärmquelle (Straßen, Eisenbahn, Straßenbahn, Industrie) über der Schwelle liegt. Standard sind nachts 55 dB(A). Je dunkler, desto mehr laute Fläche.",
    grenzen_kurz=(
        "Lärmkarten von 2011 (Straßen) und 2016 (übrige Quellen); neuere gibt es nicht.",
        "Berechnete Werte, keine Messungen; mehrere Quellen zusammen sind lauter, das ist hier nicht addiert.",
        "Bezug ist die Fläche, nicht die Zahl der Betroffenen.",
    ),
)
