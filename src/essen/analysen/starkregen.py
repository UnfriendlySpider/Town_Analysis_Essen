"""Überflutungsgefahr bei Starkregen je Stadtteil.

Grundlage ist die Starkregengefahrenkarte der Stadt Essen (Stand 2022): Einstautiefe unmittelbar nach einem
100-jährlichen Starkregen, ohne Wirkung der Kanalisation, in drei Klassen. Für jeden Stadtteil: welcher Anteil
der Fläche steht 25 cm oder tiefer unter Wasser, und welcher mindestens 5 cm?

Welche Zahl welche Klasse ist, steht in katalog/zuordnungen/starkregen-essen.yaml.
Methodik: docs/methodik/starkregen.md
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pyogrio

from .. import einwohner, kennzahlen, laden
from ..farben import FARBSTUFEN
from ..geo import ZIEL_CRS, DatenFehlen, lade_stadtteile, lies_im_stadtgebiet, vektordatei
from ..text import zahl
from .basis import Analyse, Ergebnis, Kontext, Parameter, Spalte, Stufen
from .hitze_nacht import ZuordnungFehlt, lade_zuordnung

DATENSATZ = "starkregen-essen"
LANDBEDECKUNG = "landbedeckung-nrw"   # optional: Gewässer abziehen (E-017)
TIEF = 3       # Klasse ab 25 cm
FLACH = 2      # Klasse 5 bis unter 25 cm

STUFEN = Stufen(
    grenzen=(0, 2, 4, 6, 8),
    farben=FARBSTUFEN["neutral"],
    texte=("unter 2 %", "2 bis 4 %", "4 bis 6 %", "6 bis 8 %", "8 % und mehr"),
    keine_daten_text="zu wenig Fläche, kein Anteil",
)


def _zuordnung() -> dict:
    zuordnung = lade_zuordnung(DATENSATZ)
    if not zuordnung or not zuordnung.get("feld") or not zuordnung.get("klassen"):
        raise ZuordnungFehlt(f"katalog/zuordnungen/{DATENSATZ}.yaml fehlt oder nennt feld und klassen nicht.")
    klassen = {int(k) for k in zuordnung["klassen"]}
    if not {FLACH, TIEF} <= klassen:
        raise ZuordnungFehlt(f"{zuordnung['_pfad']}: Klassen {FLACH} und {TIEF} müssen beschrieben sein.")
    return zuordnung


def pruefe_klassen(flaechen: gpd.GeoDataFrame, zuordnung: dict) -> None:
    """Jeder Code muss beschrieben sein und, wenn es ein Textfeld gibt, zum Text passen (E-009)."""
    ort = zuordnung["_pfad"]
    feld = zuordnung["feld"]
    if feld not in flaechen.columns:
        raise ZuordnungFehlt(f"{ort}: Feld {feld} fehlt (vorhanden: {', '.join(flaechen.columns)}).")
    klassen = {int(k): v for k, v in zuordnung["klassen"].items()}
    codes = set(pd.to_numeric(flaechen[feld], errors="coerce").dropna().astype(int))
    offen = sorted(codes - set(klassen))
    if offen:
        raise ZuordnungFehlt(f"{ort}: In {feld} kommen Codes ohne Beschreibung vor: {', '.join(map(str, offen))}.")
    textfeld = zuordnung.get("textfeld")
    if textfeld and textfeld in flaechen.columns:
        paare = flaechen[[feld, textfeld]].drop_duplicates()
        falsch = [f"{int(c)} = „{t}“" for c, t in paare.itertuples(index=False)
                  if str(klassen[int(c)].get("text", t)).strip() != str(t).strip()]
        if falsch:
            raise ZuordnungFehlt(f"{ort}: {feld} und {textfeld} passen nicht zur Zuordnung: {', '.join(falsch)}.")


def gewaesser(melde) -> object | None:
    """Gewässerflächen im Stadtgebiet als eine Geometrie (ZIEL_CRS), aus der Landbedeckung NRW.

    Welche Layer Wasser sind, steht in der geprüften Zuordnung katalog/zuordnungen/landbedeckung-nrw.yaml
    (Gruppe „wasser“). Ohne Landbedeckung oder ohne diese Angabe: None."""
    if not laden.vorhanden(LANDBEDECKUNG):
        return None
    zuordnung = lade_zuordnung(LANDBEDECKUNG) or {}
    layer = [name for name, gruppe in (zuordnung.get("gruppen") or {}).items() if gruppe == "wasser"]
    if not layer:
        raise ZuordnungFehlt(f"katalog/zuordnungen/{LANDBEDECKUNG}.yaml nennt keinen Layer der Gruppe wasser.")
    pfad = vektordatei(LANDBEDECKUNG)
    teile = []
    for name in layer:
        melde(f"Gewässer aus der Landbedeckung: Layer {name}")
        teile.append(lies_im_stadtgebiet(pfad, layer=name, columns=[]).to_crs(ZIEL_CRS))
    wasser = pd.concat(teile, ignore_index=True)
    return wasser.geometry.make_valid().union_all() if len(wasser) else None


def rechne(kontext: Kontext) -> Ergebnis:
    p = kontext.parameter
    melde = kontext.melde
    if not laden.vorhanden(DATENSATZ):
        raise DatenFehlen([DATENSATZ])
    zuordnung = _zuordnung()
    feld = zuordnung["feld"]
    stadtteile = lade_stadtteile(kontext.katalog)
    gebiete = stadtteile.gdf
    pfad = vektordatei(DATENSATZ)
    melde(f"Starkregenkarte: {pfad.name}")
    spalten = [c for c in (feld, zuordnung.get("textfeld"), zuordnung.get("flaechenfeld")) if c]
    vorhanden = set(pyogrio.read_info(pfad)["fields"])
    sachdaten = pyogrio.read_dataframe(pfad, read_geometry=False, columns=[c for c in spalten if c in vorhanden])
    pruefe_klassen(sachdaten, zuordnung)
    # Klasse 1 („unter 5 cm“) ist im Original eine einzige Fläche mit 3,3 Millionen Ecken und 206.820 Löchern,
    # die sich kaum verschneiden lässt. Für die Kennzahl reichen die Klassen ab 5 cm.
    flaechen = lies_im_stadtgebiet(pfad, where=f"{feld} IN ({FLACH}, {TIEF})")
    flaechen["klasse"] = pd.to_numeric(flaechen[feld]).astype(int)
    melde(f"  {zahl(len(flaechen))} Flächen mit 5 cm Einstau und mehr. Verschneide mit den Stadtteilen …")
    je_klasse = kennzahlen.flaechen_nach_klasse(gebiete, flaechen[["klasse", "geometry"]], [FLACH, TIEF])

    tabelle = gebiete.drop(columns="geometry").rename(columns={"name": "stadtteil", "nummer": "stadtteil_nr"}).set_index("gebiet_id")
    tabelle["tief_ha"] = (je_klasse[TIEF] / 1e4).reindex(tabelle.index).fillna(0.0)
    tabelle["flach_ha"] = (je_klasse[FLACH] / 1e4).reindex(tabelle.index).fillna(0.0)
    wasser = gewaesser(melde) if p["gewaesser"] == "abziehen" else None
    if wasser is not None:
        melde("Ziehe Gewässer ab (Bäche, Teiche, Ruhr und Baldeneysee) …")
        flaeche_wasser = gpd.GeoDataFrame({"klasse": [0]}, geometry=[wasser], crs=ZIEL_CRS)
        in_wasser = kennzahlen.flaechen_nach_klasse(gebiete, kennzahlen.schnitt_mit(flaechen[["klasse", "geometry"]],
                                                                                    wasser), [FLACH, TIEF])
        tabelle["gewaesser_ha"] = (kennzahlen.flaechen_nach_klasse(gebiete, flaeche_wasser, [0])[0] / 1e4) \
            .reindex(tabelle.index).fillna(0.0)
        tabelle["tief_gewaesser_ha"] = (in_wasser[TIEF] / 1e4).reindex(tabelle.index).fillna(0.0)
        tabelle["tief_ha"] = (tabelle["tief_ha"] - tabelle["tief_gewaesser_ha"]).clip(lower=0)
        tabelle["flach_ha"] = (tabelle["flach_ha"] - (in_wasser[FLACH] / 1e4).reindex(tabelle.index).fillna(0.0)) \
            .clip(lower=0)
        tabelle["land_ha"] = (tabelle["flaeche_ha"] - tabelle["gewaesser_ha"]).clip(lower=0)
        bezug = "land_ha"
    else:
        bezug = "flaeche_ha"
    flaeche = tabelle[bezug].where(tabelle[bezug] > 0)
    tabelle["anteil_ueber_25cm_pct"] = 100 * tabelle["tief_ha"] / flaeche
    tabelle["anteil_ueber_5cm_pct"] = 100 * (tabelle["tief_ha"] + tabelle["flach_ha"]) / flaeche
    minimum = float(p["min_flaeche_ha"])
    tabelle = kennzahlen.mindestbezug(tabelle, bezug, minimum, ["anteil_ueber_25cm_pct", "anteil_ueber_5cm_pct"],
                                      f"unter {minimum:g} ha Fläche, kein Anteil ausgewiesen")
    tabelle = tabelle.reset_index()
    tabelle = tabelle.round({c: 1 for c in tabelle.columns if c.endswith(("_pct", "_ha"))})

    einwohner_satz = None
    if einwohner.vorhanden():
        melde("Schätze die Einwohner in Flächen ab 25 cm (Zensus-Gitter) …")
        tief = flaechen[flaechen["klasse"] == TIEF][["geometry"]].to_crs(ZIEL_CRS)
        tief["geometry"] = tief.geometry.make_valid()
        tief = kennzahlen.ohne(tief, wasser) if wasser is not None else tief
        tabelle, satz = einwohner.ergaenze(tabelle, einwohner.in_flaeche(gebiete, tief))
        einwohner_satz = (f"{satz[:-1]} wohnen in Zellen mit Flächen ab 25 cm Einstau, anteilig nach Fläche. "
                          f"{einwohner.HINWEIS}")
    mit_wert = tabelle.dropna(subset=["anteil_ueber_25cm_pct"])
    stadtweit = kennzahlen.gewichtetes_mittel(mit_wert["anteil_ueber_25cm_pct"], mit_wert[bezug])
    text = ("Kein Stadtteil mit genug Fläche." if stadtweit is None else
            f"Stadtweit stehen nach einem 100-jährlichen Starkregen {zahl(stadtweit, 1)} % der "
            + ("Landfläche (ohne Gewässer)" if wasser is not None else "Fläche")
            + " 25 cm oder tiefer unter Wasser (Modell ohne Kanalisation).")
    melde(text)
    hinweise = list(stadtteile.hinweise)
    if not zuordnung.get("geprueft", False):
        hinweise.append(f"Die Zuordnung {zuordnung['_pfad']} ist noch nicht als geprüft markiert.")
    hinweise += [
        "Modell der Stadt Essen (Stand 2022): Einstau unmittelbar nach einem 100-jährlichen Starkregen, ohne Wirkung "
        "der Kanalisation. Kein Hochwasser von Ruhr oder Emscher.",
        ("Gewässer der Landbedeckung NRW (Bäche, Teiche, Ruhr, Baldeneysee) sind abgezogen: gezählt wird nur "
         "Einstau an Land, bezogen auf die Landfläche des Stadtteils (E-017). Davon lagen "
         f"{zahl(tabelle['tief_gewaesser_ha'].sum(), 0)} ha der Flächen ab 25 cm in Gewässern."
         if wasser is not None else
         "Die tiefen Flächen schließen Wasser in Bächen, Teichen und an der Ruhr ein; in Stadtteilen an der Ruhr ist "
         "ein großer Teil davon Gewässer. "
         + ("Zum Abziehen die Landbedeckung NRW laden." if p["gewaesser"] == "abziehen" else
            "Gewässer werden auf Wunsch mitgezählt (Einstellung „Gewässer“).")),
        "Die Kennzahl bezieht sich auf Fläche, nicht auf die Zahl der Betroffenen (E-007).",
    ]
    if einwohner_satz:
        hinweise.append(einwohner_satz)
    flaechenfeld = zuordnung.get("flaechenfeld")
    if flaechenfeld in sachdaten.columns:
        abgedeckt = 100 * pd.to_numeric(sachdaten[flaechenfeld], errors="coerce").sum() / 1e4 / tabelle["flaeche_ha"].sum()
        hinweise.append(f"Alle drei Klassen der Karte zusammen bedecken laut {flaechenfeld} {zahl(abgedeckt, 1)} % der "
                        "Stadtfläche; der Rest ist nicht modelliert und zählt hier als ohne Einstau.")
    geometrie = gebiete[["gebiet_id", "geometry"]].merge(tabelle, on="gebiet_id")
    return Ergebnis(
        analyse_id=ANALYSE.id,
        tabelle=tabelle,
        geometrie=gpd.GeoDataFrame(geometrie, geometry="geometry", crs=ZIEL_CRS),
        kennzahl_stadt=stadtweit,
        kennzahl_text=text,
        hinweise=hinweise + [f"Klassen aus der Zuordnung {zuordnung['_pfad']}."],
        quellen=[stadtteile.datensatz, DATENSATZ] + ([LANDBEDECKUNG] if wasser is not None else []),
        parameter=dict(p),
    )


ANALYSE = Analyse(
    id="starkregen",
    gewicht="land_ha",  # wie der stadtweite Wert; für Werte je Stadtbezirk (E-018)
    titel="Überflutung bei Starkregen je Stadtteil",
    frage="Welcher Anteil der Fläche eines Stadtteils steht nach einem 100-jährlichen Starkregen 25 cm oder tiefer unter Wasser?",
    themen=("wasser",),
    benoetigt=("stadtteile", DATENSATZ),
    optional=(LANDBEDECKUNG, einwohner.DATENSATZ),
    rechne=rechne,
    kennzahl="anteil_ueber_25cm_pct",
    kennzahl_titel="Anteil der Landfläche mit 25 cm Einstau und mehr",
    einheit="%",
    stufen=STUFEN,
    spalten=(
        Spalte("stadtteil", "Stadtteil", "text"),
        Spalte("anteil_ueber_25cm_pct", "ab 25 cm", "prozent", balken=True),
        Spalte("anteil_ueber_5cm_pct", "ab 5 cm", "prozent"),
        Spalte("tief_ha", "ab 25 cm, ha", "zahl", stellen=1),
        Spalte("anteil_einwohner_pct", "Einwohner betroffen", "prozent"),
    ),
    parameter=(
        Parameter("gewaesser", "Gewässer", "abziehen",
                  "Bäche, Teiche, Ruhr und Baldeneysee aus der Landbedeckung NRW abziehen (Standard, E-017) oder wie "
                  "vor dem 12.10.2026 mitzählen.", optionen=("abziehen", "mitzaehlen"), typ="wahl",
                  beschriftungen={"abziehen": "abziehen (nur Land)", "mitzaehlen": "mitzählen"}, selten=True),
        Parameter("min_flaeche_ha", "Mindestfläche in Hektar", 5.0,
                  "Stadtteile mit weniger Fläche bekommen keinen Wert, weil ein Anteil dort zufällig wirken könnte.", typ="zahl",
                  selten=True),
    ),
    methodik="methodik/starkregen.md",
    thema_titel="Starkregen",
    kurz="Wo stünde das Wasser nach einem sehr seltenen Starkregen 25 cm hoch oder mehr?",
    richtung="hoch_schlecht",
    lesehilfe="Gefärbt nach dem Anteil der Landfläche (ohne Gewässer), auf der nach einem Regen, wie er statistisch einmal in 100 Jahren vorkommt, mindestens 25 cm Wasser steht. Dunkleres Blau heißt mehr solche Fläche.",
    grenzen_kurz=(
        "Modell ohne Kanalisation: Es zeigt, wohin das Wasser fließt, wenn die Kanäle voll sind.",
        "Bäche, Teiche, Ruhr und Baldeneysee sind abgezogen; gezählt wird Wasser, das an Land steht.",
        "Kein Hochwasser der Flüsse, nur Regenwasser.",
    ),
)
