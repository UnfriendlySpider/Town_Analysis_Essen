"""Wärmebelastung am Tag je Stadtteil.

Grundlage ist die Klimaanalyse NRW 2026, Klimaanalysekarte Tag (14 Uhr MEZ, Modell FITNAH-3D).
Das Raster enthält die physiologisch äquivalente Temperatur (PET) in °C für die ganze Fläche. Für jeden
Stadtteil: welcher Anteil der Fläche liegt in welcher Belastungsklasse nach VDI 3787 Blatt 2, und wie viel
davon ist extrem stark belastet (PET über 41 °C)?

Welche Datei je Szenario gelesen wird, steht in katalog/zuordnungen/klimaanalyse-tag-raster.yaml.
Methodik: docs/methodik/hitze-tag.md
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from .. import kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import RASTER_ENDUNGEN, ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_raster_fenster
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen
from .hitze_nacht import SZENARIEN, SZENARIO_STANDARD, ZuordnungFehlt, lade_zuordnung

RASTER_ID = "klimaanalyse-tag-raster"
BESCHREIBUNG_ID = "klimaanalyse-beschreibung"

# Methodik Karte Tag, Tabelle 1 (VDI 3787 Blatt 2). Die Klassen unter 23 °C sind zusammengefasst,
# weil sie in Essen kaum vorkommen (typischer Sommertag 0,2 % der Fläche).
KLASSEN = {
    1: "kein thermischer Stress oder kühler (bis 23 °C)",
    2: "leichte Wärmebelastung (23 bis 29 °C)",
    3: "moderate Wärmebelastung (29 bis 35 °C)",
    4: "starke Wärmebelastung (35 bis 41 °C)",
    5: "extrem starke Wärmebelastung (über 41 °C)",
}
GRENZEN_C = [23.0, 29.0, 35.0, 41.0]  # Obergrenzen der Klassen 1 bis 4
AB_STARK = 4
AB_EXTREM = 5

STUFEN = Stufen(
    grenzen=(0, 20, 40, 60, 80),
    farben=FARBSTUFEN["waerme"],
    texte=("unter 20 %", "20 bis 40 %", "40 bis 60 %", "60 bis 80 %", "80 % und mehr"),
    keine_daten_text="zu wenig Fläche, kein Anteil",
)


def klasse_aus_pet(werte: np.ndarray) -> np.ndarray:
    """PET in °C → Klasse 1 bis 5 nach VDI 3787 Blatt 2; NaN → 0. Grenzwerte gehören zur unteren Klasse."""
    werte = np.asarray(werte, dtype=float)
    klassen = (1 + np.searchsorted(GRENZEN_C, werte, side="left")).astype(np.int16)
    klassen[~np.isfinite(werte)] = 0
    return klassen


def _rasterdatei(szenario: str):
    if not laden.vorhanden(RASTER_ID):
        raise DatenFehlen([RASTER_ID])
    zuordnung = lade_zuordnung(RASTER_ID)
    if not zuordnung or not (zuordnung.get("dateien") or {}).get(szenario):
        raise ZuordnungFehlt(f"In katalog/zuordnungen/{RASTER_ID}.yaml fehlt unter dateien die Datei für das "
                             f"Szenario „{szenario}“ (Format in docs/katalog.md).")
    if zuordnung.get("lesart") != "temperatur":
        raise ZuordnungFehlt(f"{zuordnung['_pfad']}: erwartet lesart: temperatur (PET in °C).")
    name = str(zuordnung["dateien"][szenario]).lower()
    kandidaten = [p for p in laden.entpackt(RASTER_ID) if p.suffix.lower() in RASTER_ENDUNGEN]
    treffer = [p for p in kandidaten if p.name.lower() == name]
    if not treffer:
        raise ZuordnungFehlt(f"{zuordnung['_pfad']}: Datei {zuordnung['dateien'][szenario]} fehlt im Datensatz. "
                             f"Vorhanden: {', '.join(sorted(p.name for p in kandidaten))}.")
    return treffer[0], zuordnung


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    szenario = p.get("szenario") or SZENARIO_STANDARD
    if szenario not in SZENARIEN:
        raise ValueError(f"Unbekanntes Szenario „{szenario}“ ({', '.join(SZENARIEN)}).")
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfad, zuordnung = _rasterdatei(szenario)
    melde(f"Szenario: {SZENARIEN[szenario]}")
    melde(f"  Raster: {pfad.name}")
    daten, transform, crs, _, _ = lies_raster_fenster(pfad, gebiete)
    band = daten[int(zuordnung.get("band", 1)) - 1]
    pet = np.ma.filled(band.astype(float), np.nan)
    unplausibel = np.isfinite(pet) & ((pet < -20) | (pet > 70))
    hinweise = list(stadtteile.hinweise)
    if unplausibel.any():  # Füllwerte ohne nodata-Angabe
        hinweise.append(f"{zahl(int(unplausibel.sum()))} Zellen mit PET unter -20 oder über 70 °C als Fehlwert behandelt.")
        pet[unplausibel] = np.nan
    klassen = klasse_aus_pet(pet)
    flaechen = kennzahlen.flaechen_nach_klasse_raster(gebiete, klassen, transform, crs, list(KLASSEN))

    # mittlere PET je Stadtteil (Zellmittelpunkt im Gebiet, wie bei den Flächen)
    from rasterio.features import rasterize
    index = rasterize(((g, i + 1) for i, g in enumerate(gebiete.to_crs(crs).geometry)), out_shape=pet.shape,
                      transform=transform, fill=0, dtype="int32")
    gueltig = (index > 0) & np.isfinite(pet)
    summe = np.bincount(index[gueltig], weights=pet[gueltig], minlength=len(gebiete) + 1)[1:]
    anzahl = np.bincount(index[gueltig], minlength=len(gebiete) + 1)[1:]
    mittel = pd.Series(np.where(anzahl > 0, summe / np.maximum(anzahl, 1), np.nan), index=gebiete["gebiet_id"].to_numpy())

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    tabelle["bewertet_ha"] = (flaechen.sum(axis=1) / 1e4).reindex(tabelle.index).fillna(0.0)
    anteile = kennzahlen.anteile(flaechen).reindex(tabelle.index)
    tabelle["anteil_ueber_41c_pct"] = anteile[[k for k in KLASSEN if k >= AB_EXTREM]].sum(axis=1, min_count=1)
    tabelle["anteil_ueber_35c_pct"] = anteile[[k for k in KLASSEN if k >= AB_STARK]].sum(axis=1, min_count=1)
    tabelle["pet_mittel_c"] = mittel.reindex(tabelle.index)
    for klasse in KLASSEN:
        tabelle[f"klasse_{klasse}_pct"] = anteile[klasse]
    minimum = float(p["min_flaeche_ha"])
    spalten = [c for c in tabelle.columns if c.startswith(("anteil_ueber", "klasse_", "pet_"))]
    tabelle = kennzahlen.mindestbezug(tabelle, "bewertet_ha", minimum, spalten,
                                      f"unter {minimum:g} ha bewertete Fläche, kein Wert ausgewiesen")
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha", "_c"))})

    mit_wert = tabelle.dropna(subset=["anteil_ueber_41c_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_ueber_41c_pct"], mit_wert["bewertet_ha"])
    text = ("Kein Stadtteil mit genug Fläche." if stadtweit is None else
            f"Stadtweit liegen {zahl(stadtweit)} % der Fläche um 14 Uhr über 41 °C PET ({SZENARIEN[szenario]}).")
    melde(text)
    if not zuordnung.get("geprueft", False):
        hinweise.append(f"Die Zuordnung {zuordnung['_pfad']} ist noch nicht als geprüft markiert.")
    hinweise += [
        f"Szenario der Klimaanalyse: {SZENARIEN[szenario]}.",
        "PET ist ein Modellwert für die gefühlte Temperatur einer Person im Freien um 14 Uhr, keine Messung der Lufttemperatur.",
        "Die Tageskarte trennt nicht nach bebauter und freier Fläche: Bezug ist die ganze Fläche des Stadtteils mit Wert, "
        "auch Wald, Wiese und Wasser.",
    ]
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise + [f"Klassen aus der Zuordnung {zuordnung['_pfad']} (PET nach VDI 3787 Blatt 2)."],
        quellen=[stadtteile.datensatz, RASTER_ID] + ([BESCHREIBUNG_ID] if laden.vorhanden(BESCHREIBUNG_ID) else []),
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="hitze-tag",
    gewicht="bewertet_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Wärmebelastung am Tag je Stadtteil",
    frage="Welcher Anteil der Fläche hat um 14 Uhr eine extrem starke Wärmebelastung (PET über 41 °C)?",
    themen=("klima",),
    benoetigt=("stadtteile", RASTER_ID),
    optional=(BESCHREIBUNG_ID,),
    rechne=rechne,
    kennzahl="anteil_ueber_41c_pct",
    kennzahl_titel="Anteil der Fläche über 41 °C PET",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_ueber_41c_pct", "über 41 °C PET", "prozent", balken=True),
        Spalte("anteil_ueber_35c_pct", "über 35 °C PET", "prozent"),
        Spalte("pet_mittel_c", "PET im Mittel, °C", "zahl", stellen=1),
    ),
    parameter=(
        Parameter("szenario", "Wie heiß ist der Tag?", SZENARIO_STANDARD,
                  "Die Klimaanalyse des Landes rechnet zwei Wetterlagen: einen typischen und einen extrem heißen "
                  "Sommertag. Der extreme Tag zeigt, wie es in Hitzewellen aussieht.",
                  tuple(SZENARIEN), "wahl", beschriftungen={"extrem": "extremer Sommertag (Standard)", "typisch": "typischer Sommertag"}),
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken könnte.", typ="zahl",
                  selten=True),
    ),
    methodik="methodik/hitze-tag.md",
    thema_titel="Hitze am Tag",
    kurz="Wie viel Fläche ist an einem heißen Sommernachmittag für Menschen im Freien extrem belastend?",
    richtung="hoch_schlecht",
    lesehilfe="Gefärbt nach dem Anteil der Fläche, auf der die gefühlte Temperatur um 14 Uhr über 41 °C liegt. Das gilt als extreme Hitzebelastung. Je dunkler, desto mehr solche Fläche. Schatten von Bäumen senkt die gefühlte Temperatur stark.",
    grenzen_kurz=(
        "Modellrechnung für einen heißen Sommertag, keine Messung.",
        "Die gefühlte Temperatur ist nicht die Lufttemperatur aus dem Wetterbericht.",
        "Gezählt wird die ganze Fläche, auch Wald, Wiesen und Wasser.",
    ),
)
