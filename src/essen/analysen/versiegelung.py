"""Versiegelte Fläche je Stadtteil.

Grundlage ist die luftbildbasierte Bodenversiegelung NRW (LANUK, Projekt EBOVE, Luftbilder 2022 bis 2024,
0,5-m-Raster) im Ausschnitt für Essen. Jede Zelle ist versiegelt oder nicht versiegelt. Welcher Rasterwert
„versiegelt“ bedeutet, steht im Katalog unter felder.versiegelt (belegt über die Gemeindetabelle des Anbieters).

Methodik: docs/methodik/versiegelung.md
"""

from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd

from .. import kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import RASTER_ENDUNGEN, ZIEL_CRS, DatenFehlen, lade_stadtteile
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen, Zeitwert
from .hitze_nacht import ZuordnungFehlt

DATENSATZ = "bodenversiegelung-nrw"
SATELLIT = "bodenversiegelung-sat-nrw"   # optional: Versiegelungsgrad 2006 bis 2018 für den Verlauf

STUFEN = Stufen(
    grenzen=(0, 20, 35, 50, 65),
    farben=FARBSTUFEN["neutral"],
    texte=("unter 20 %", "20 bis 35 %", "35 bis 50 %", "50 bis 65 %", "65 % und mehr"),
    keine_daten_text="zu wenig Fläche, kein Anteil",
)


def _codes(kontext: Kontext) -> tuple[int, int]:
    """Rasterwerte für versiegelt und nicht versiegelt aus dem Katalog (felder.versiegelt). Nie raten (E-009)."""
    felder = kontext.katalog.datensatz(DATENSATZ).felder or {}
    if "versiegelt" not in felder:
        raise ZuordnungFehlt(f"Im Katalog fehlt bei {DATENSATZ} die Angabe felder.versiegelt (welcher Rasterwert "
                             "versiegelt bedeutet). Erst mit Beleg eintragen (Skill daten-inspizieren).")
    versiegelt = int(felder["versiegelt"])
    offen = int(felder.get("nicht_versiegelt", 1 - versiegelt))
    return versiegelt, offen


def _rasterdatei():
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    kandidaten = [p for p in laden.entpackt(DATENSATZ) if p.suffix.lower() in RASTER_ENDUNGEN]
    if len(kandidaten) != 1:
        raise ZuordnungFehlt(f"Im Datensatz {DATENSATZ} wird genau ein Raster erwartet, gefunden: "
                             f"{', '.join(p.name for p in kandidaten) or 'keins'}.")
    return kandidaten[0]


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    versiegelt, offen = _codes(kontext)
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfad = _rasterdatei()
    melde(f"Raster: {pfad.name} (versiegelt = {versiegelt}, nicht versiegelt = {offen})")
    flaechen = kennzahlen.flaechen_nach_wert_rasterdatei(gebiete, pfad, [offen, versiegelt], melde=melde)

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    tabelle["bewertet_ha"] = (flaechen.sum(axis=1) / 1e4).reindex(tabelle.index).fillna(0.0)
    tabelle["versiegelt_ha"] = (flaechen[versiegelt] / 1e4).reindex(tabelle.index).fillna(0.0)
    tabelle["anteil_versiegelt_pct"] = 100 * tabelle["versiegelt_ha"] / tabelle["bewertet_ha"].where(tabelle["bewertet_ha"] > 0)
    tabelle["abdeckung_pct"] = 100 * tabelle["bewertet_ha"] / tabelle["flaeche_ha"]
    minimum = float(p["min_flaeche_ha"])
    tabelle = kennzahlen.mindestbezug(tabelle, "bewertet_ha", minimum, ["anteil_versiegelt_pct"],
                                      f"unter {minimum:g} ha bewertete Fläche, kein Anteil ausgewiesen")
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha"))})

    hinweise = list(stadtteile.hinweise)
    luecken = tabelle[tabelle["abdeckung_pct"] < 99]
    if len(luecken):
        hinweise.append("Das Raster deckt nicht die ganze Fläche ab: "
                        + ", ".join(f"{z.stadtteil} {zahl(z.abdeckung_pct)} %" for z in luecken.itertuples()) + ".")
    mit_wert = tabelle.dropna(subset=["anteil_versiegelt_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_versiegelt_pct"], mit_wert["bewertet_ha"])
    text = ("Kein Stadtteil mit genug Fläche." if stadtweit is None else
            f"Stadtweit sind {zahl(stadtweit)} % der Fläche versiegelt.")
    melde(text)
    hinweise += [
        "Versiegelt heißt: Gebäude, Straßen, Wege, Plätze und andere befestigte Flächen, erkannt aus Luftbildern "
        "2022 bis 2024 (0,5 m). Teilversiegelte Flächen sind nicht eigens ausgewiesen.",
        "Die Erkennung ist ein Modellergebnis (KI-Segmentierung) und kann einzelne Flächen falsch einordnen.",
    ]
    quellen = [stadtteile.datensatz, DATENSATZ]
    jahre = None
    if laden.vorhanden(SATELLIT):
        jahre = satellit_jahreswerte(gebiete, minimum, melde)
        quellen.append(SATELLIT)
        hinweise.append("Verlauf 2006 bis 2018 aus Satellitendaten (Copernicus, 20 m, ab 2018 10 m): mittlerer "
                        "Versiegelungsgrad, nicht mit den Luftbildern 2024 vergleichbar. Der Anstieg 2018 kommt laut "
                        "LANUK vor allem von der feineren Auflösung.")
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise,
        quellen=quellen,
        parameter=dict(p),
        jahreswerte=jahre,
    )


def satellit_jahreswerte(gebiete: gpd.GeoDataFrame, min_flaeche_ha: float, melde=lambda m: None) -> pd.DataFrame:
    """Mittlerer Versiegelungsgrad (%) je Stadtteil und Jahr aus den Satellitenrastern (eine Datei je Jahr).

    Jahr und Zellgröße stehen im Dateinamen (VG_20m_2006_Essen.tif). Gültig sind Werte von 0 bis 100 (Prozent laut
    Methodik des LANUK); andere Werte, etwa 254 im Raster 2012, zählen nicht. Belegt über die Gemeindemittel des
    Anbieters (Katalog, Hinweise zu bodenversiegelung-sat-nrw)."""
    raster = [p for p in laden.entpackt(SATELLIT) if p.suffix.lower() in RASTER_ENDUNGEN]
    teile = []
    for pfad in sorted(raster):
        treffer = re.search(r"_(\d+)m_((?:19|20)\d{2})_", pfad.name)
        if not treffer:
            raise ZuordnungFehlt(f"{pfad.name}: Jahr und Zellgröße nicht im Dateinamen (erwartet wie VG_20m_2006_Essen.tif). "
                                 "Erst untersuchen: uv run essen inspizieren bodenversiegelung-sat-nrw")
        zelle_m, jahr = int(treffer.group(1)), int(treffer.group(2))
        melde(f"  Satellit {jahr} ({zelle_m} m): {pfad.name}")
        werte = kennzahlen.mittel_je_gebiet_rasterdatei(gebiete, pfad, (0, 100))
        werte = werte.reindex(gebiete["gebiet_id"])
        werte.loc[werte["gueltig_ha"] < min_flaeche_ha, "mittel"] = float("nan")
        teile.append(pd.DataFrame({"gebiet_id": gebiete["gebiet_id"].to_numpy(), "stadtteil": gebiete["name"].to_numpy(),
                                   "jahr": jahr, "versiegelungsgrad_pct": werte["mittel"].round(1).to_numpy(),
                                   "zellgroesse_m": zelle_m, "vollstaendig": True}))
    if not teile:
        raise ZuordnungFehlt(f"Im Datensatz {SATELLIT} liegt kein Raster. Neu laden: uv run essen laden {SATELLIT} --neu")
    return pd.concat(teile, ignore_index=True).sort_values(["gebiet_id", "jahr"]).reset_index(drop=True)


ANALYSE = Analyse(
    id="versiegelung",
    gewicht="bewertet_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Versiegelte Fläche je Stadtteil",
    frage="Welcher Anteil der Fläche eines Stadtteils ist versiegelt?",
    themen=("gruen", "wasser"),
    benoetigt=("stadtteile", DATENSATZ),
    optional=(SATELLIT,),
    rechne=rechne,
    kennzahl="anteil_versiegelt_pct",
    kennzahl_titel="Anteil der versiegelten Fläche",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_versiegelt_pct", "versiegelt", "prozent", balken=True),
        Spalte("versiegelt_ha", "versiegelt, ha", "zahl", stellen=1),
        Spalte("bewertet_ha", "Fläche, ha", "zahl", stellen=1),
    ),
    parameter=(
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken könnte.", typ="zahl",
                  selten=True),
    ),
    methodik="methodik/versiegelung.md",
    zeitachse=(Zeitwert("versiegelungsgrad_pct", "Mittlerer Versiegelungsgrad (Satellit, 2006 bis 2018)", "%", STUFEN,
                        jahrzehnte=False,
                        hinweis="Satellitendaten, gröber als die Luftbilder der Ansicht „Heute“ und nicht mit ihnen "
                                "vergleichbar. 2018 wechselt die Auflösung von 20 auf 10 m; der Anstieg in diesem Jahr "
                                "kommt laut Anbieter vor allem daher, nicht von neuer Bebauung."),),
    thema_titel="Versiegelter Boden",
    kurz="Welcher Anteil des Bodens ist mit Gebäuden, Asphalt oder Pflaster bedeckt?",
    richtung="hoch_schlecht",
    lesehilfe="Gefärbt nach dem Anteil des Bodens, der versiegelt ist. Je dunkler, desto mehr. Auf versiegelten Flächen kann Regen nicht versickern, und sie heizen sich stärker auf. Grundlage sind Luftbilder mit 50 cm Auflösung.",
    grenzen_kurz=(
        "Erkannt aus Luftbildern; Bäume über Straßen verdecken den Asphalt darunter.",
        "Bezug ist die ganze Fläche des Stadtteils, auch Wald und Wasser.",
        "Schotter oder Rasengitter sind nicht eigens ausgewiesen.",
    ),
)
