"""Diagramme für die App (altair): wo ein Stadtteil steht, alle Stadtteile sortiert, Zusammenhänge.

Die Funktionen bekommen fertige Tabellen und geben ein altair-Diagramm zurück; die Seiten zeigen es nur an.
Farben kommen aus essen.farben bzw. den Stufen der Analyse, damit Diagramm und Karte zusammenpassen.
"""

from __future__ import annotations

import json

import altair as alt
import numpy as np
import pandas as pd
import shapely

from .analysen.basis import Stufen
from .farben import FARBSTUFEN, KEINE_DATEN

GRAU = "#9aa59f"
DUNKEL = "#15201b"
HELL = "#e4ebe6"   # Schrift im dunklen Thema (textColor aus .streamlit/config.toml)
MARKIERT = "#b43e03"
SCHRIFT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"


def _d3_format(stellen: int) -> str:
    return f",.{stellen}f"


def _ohne_rahmen(chart: alt.Chart | alt.LayerChart) -> alt.Chart | alt.LayerChart:
    return chart.configure_view(stroke=None).configure_axis(labelFont=SCHRIFT, titleFont=SCHRIFT, grid=False) \
        .configure_text(font=SCHRIFT).configure(locale={"number": DE_FORMAT})


# Zahlenformat deutsch (Tausenderpunkt, Dezimalkomma) für vega-embed
DE_FORMAT = {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["", " €"]}


def punktleiste(werte: pd.DataFrame, markiert: str | None, einheit: str = "", stellen: int = 1,
                mittel: float | None = None, farbe_markiert: str = MARKIERT, dunkel: bool = False,
                bezirk: float | None = None, bezirk_name: str = "Stadtbezirk") -> alt.LayerChart:
    """Eine Zeile mit allen Stadtteilen als Punkte; der gewählte Stadtteil ist hervorgehoben und beschriftet.

    `werte` braucht die Spalten gebiet_id, stadtteil, wert. Das Mittel der Stadtteile erscheint als Strich, der
    Wert des Stadtbezirks (falls angegeben) als gestrichelter Strich (Text dazu steht im Satz über dem Diagramm).
    `dunkel` passt Schrift und Konturen an das dunkle Thema an."""
    vorne, hinten = (HELL, "#111814") if dunkel else (DUNKEL, "#ffffff")
    daten = werte.dropna(subset=["wert"]).assign(
        markiert=lambda d: d["gebiet_id"].astype(str) == str(markiert))
    daten = daten.sort_values("markiert")  # markierten Punkt zuletzt zeichnen
    titel = f"Wert ({einheit})" if einheit else "Wert"
    x = alt.X("wert:Q", title=None, scale=alt.Scale(zero=False, nice=True),
              axis=alt.Axis(format=_d3_format(stellen), tickCount=5, labelColor="#5d6a63", domainColor="#c9cfcb"))
    tooltip = [alt.Tooltip("stadtteil:N", title="Stadtteil"), alt.Tooltip("wert:Q", title=titel,
                                                                          format=_d3_format(stellen))]
    andere = alt.Chart(daten[~daten["markiert"]]).mark_circle(size=60, opacity=0.45, color=GRAU).encode(
        x=x, tooltip=tooltip)
    ebenen = [andere]
    if mittel is not None and not np.isnan(mittel):
        m = pd.DataFrame({"wert": [mittel], "text": ["Mittel"]})
        ebenen.append(alt.Chart(m).mark_tick(color=vorne, thickness=2, size=22, opacity=0.6).encode(
            x=x, tooltip=[alt.Tooltip("wert:Q", title="Mittel der Stadtteile", format=_d3_format(stellen))]))
    if bezirk is not None and not np.isnan(bezirk):
        b = pd.DataFrame({"wert": [bezirk]})
        ebenen.append(alt.Chart(b).mark_tick(color=vorne, thickness=2, size=22, opacity=0.8, strokeDash=[3, 2]).encode(
            x=x, tooltip=[alt.Tooltip("wert:Q", title=bezirk_name, format=_d3_format(stellen))]))
    eigen = daten[daten["markiert"]]
    if len(eigen):
        ebenen.append(alt.Chart(eigen).mark_circle(size=170, opacity=1, color=farbe_markiert, stroke=hinten,
                                                   strokeWidth=1.5).encode(x=x, tooltip=tooltip))
        # Name neben dem Punkt, zur Mitte hin; eine Kontur in Hintergrundfarbe hält ihn über den grauen Punkten lesbar
        mitte = (daten["wert"].min() + daten["wert"].max()) / 2
        links = bool(eigen["wert"].iloc[0] > mitte)
        for kontur in (True, False):
            ebenen.append(alt.Chart(eigen).mark_text(
                align="right" if links else "left", dx=-11 if links else 11, fontSize=12, fontWeight="bold",
                color=vorne, **({"stroke": hinten, "strokeWidth": 4, "strokeJoin": "round"} if kontur else {})
            ).encode(x=x, text="stadtteil:N"))
    return _ohne_rahmen(alt.layer(*ebenen).properties(height=44))


def balken_sortiert(tabelle: pd.DataFrame, kennzahl: str, stufen: Stufen | None, titel: str, einheit: str = "",
                    stellen: int = 1, markiert: str | None = None, absteigend: bool = True,
                    dunkel: bool = False) -> alt.LayerChart:
    """Alle Stadtteile als waagerechte Balken, sortiert, in der Farbe ihrer Kartenstufe; Mittel als Linie.

    `tabelle` braucht gebiet_id, stadtteil und die Kennzahlspalte. Ein Klick auf einen Balken wählt den
    Stadtteil (Auswahl „stadtteil“, für st.altair_chart(on_select=…)). `dunkel` für das dunkle Thema."""
    vorne = HELL if dunkel else DUNKEL
    daten = tabelle[["gebiet_id", "stadtteil", kennzahl]].dropna(subset=[kennzahl]).rename(columns={kennzahl: "wert"})
    daten = daten.assign(gebiet_id=daten["gebiet_id"].astype(str),
                         farbe=[stufen.farbe(w) if stufen else FARBSTUFEN["neutral"][2] for w in daten["wert"]],
                         markiert=lambda d: d["gebiet_id"] == str(markiert))
    reihenfolge = daten.sort_values("wert", ascending=not absteigend)["stadtteil"].tolist()
    achse = f"{titel} ({einheit})" if einheit else titel
    auswahl = alt.selection_point(name="stadtteil", fields=["gebiet_id"], on="click", empty=False)
    y = alt.Y("stadtteil:N", sort=reihenfolge, title=None,
              axis=alt.Axis(labelLimit=180, labelColor=vorne, ticks=False, domain=False, labelOverlap=False,
                            labelFontSize=12))
    x = alt.X("wert:Q", title=achse, axis=alt.Axis(format=_d3_format(stellen), grid=True,
                                                   gridColor="#2c3530" if dunkel else "#eef0ee",
                                                   labelColor="#5d6a63"))
    balken = alt.Chart(daten).mark_bar(cornerRadiusEnd=2, height={"band": 0.78}).encode(
        x=x, y=y,
        color=alt.Color("farbe:N", scale=None),
        stroke=alt.condition("datum.markiert", alt.value(vorne), alt.value(None)),
        strokeWidth=alt.condition("datum.markiert", alt.value(2), alt.value(0)),
        tooltip=[alt.Tooltip("stadtteil:N", title="Stadtteil"),
                 alt.Tooltip("wert:Q", title=achse, format=_d3_format(stellen))],
    ).add_params(auswahl)
    mittel = pd.DataFrame({"wert": [daten["wert"].mean()], "text": ["Mittel der Stadtteile"]})
    linie = alt.Chart(mittel).mark_rule(color=vorne, strokeDash=[4, 3], strokeWidth=1.5).encode(x="wert:Q")
    beschriftung = alt.Chart(mittel).mark_text(align="left", dx=4, dy=-4, fontSize=11, color=vorne, y=0).encode(
        x="wert:Q", text="text:N")
    hoehe = max(160, 20 * len(daten))
    return _ohne_rahmen(alt.layer(balken, linie, beschriftung).properties(height=hoehe))


def _bereich(werte: pd.Series, rand: float = 0.06) -> list[float]:
    """Achsenbereich über die Werte mit etwas Rand, aber nicht unter 0 oder über 100, wenn die Werte dort liegen."""
    unten, oben = float(werte.min()), float(werte.max())
    zusatz = (oben - unten) * rand or 1.0
    unten, oben = unten - zusatz, oben + zusatz
    if werte.min() >= 0:
        unten = max(unten, 0.0)
    if werte.max() <= 100:
        oben = min(oben, 100.0)
    return [unten, oben]


def streu_quadranten(paar: pd.DataFrame, a: str, b: str, titel_a: str, titel_b: str,
                     felder: tuple[str, str, str, str] = ("", "", "", ""), markiert: str | None = None,
                     stellen: int = 1, anzahl_namen: int = 4, dunkel: bool = False) -> alt.LayerChart:
    """Streudiagramm zweier Kennzahlen mit Mittel-Linien (vier Felder), Trendlinie und den auffälligsten Namen.

    `felder` beschriftet die vier Felder: (oben rechts, oben links, unten links, unten rechts)."""
    vorne, gitter = (HELL, "#2c3530") if dunkel else (DUNKEL, "#eef0ee")
    daten = paar.assign(gebiet_id=paar["gebiet_id"].astype(str),
                        markiert=paar["gebiet_id"].astype(str) == str(markiert))
    mx, my = float(daten[a].mean()), float(daten[b].mean())
    # Auffällig: am weitesten vom Mittelpunkt, in Standardabweichungen gemessen
    sa, sb = daten[a].std() or 1.0, daten[b].std() or 1.0
    abstand = ((daten[a] - mx) / sa) ** 2 + ((daten[b] - my) / sb) ** 2
    daten["name"] = ""
    auffaellig = abstand.nlargest(anzahl_namen).index
    daten.loc[auffaellig, "name"] = daten.loc[auffaellig, "stadtteil"]
    daten.loc[daten["markiert"], "name"] = daten.loc[daten["markiert"], "stadtteil"]

    # Achsen nur über die Daten (die Trendlinie darf nicht hinausragen), mit Rand für die Feldnamen
    x = alt.X(f"{a}:Q", title=titel_a, scale=alt.Scale(domain=_bereich(daten[a])),
              axis=alt.Axis(format=_d3_format(stellen), grid=True, gridColor=gitter))
    y = alt.Y(f"{b}:Q", title=titel_b, scale=alt.Scale(domain=_bereich(daten[b], 0.12)),
              axis=alt.Axis(format=_d3_format(stellen), grid=True, gridColor=gitter))
    tooltip = [alt.Tooltip("stadtteil:N", title="Stadtteil"),
               alt.Tooltip(f"{a}:Q", title=titel_a, format=_d3_format(stellen)),
               alt.Tooltip(f"{b}:Q", title=titel_b, format=_d3_format(stellen))]
    basis = alt.Chart(daten)
    ebenen = [
        alt.Chart(pd.DataFrame({"x": [mx]})).mark_rule(color=GRAU, strokeDash=[4, 3]).encode(x="x:Q"),
        alt.Chart(pd.DataFrame({"y": [my]})).mark_rule(color=GRAU, strokeDash=[4, 3]).encode(y="y:Q"),
    ]
    if len(daten) >= 3:
        ebenen.append(basis.transform_regression(a, b).mark_line(color=FARBSTUFEN["neutral"][3], opacity=0.5,
                                                                 strokeWidth=2, clip=True).encode(x=x, y=y))
    ebenen += [
        basis.mark_circle(size=80, opacity=0.85).encode(
            x=x, y=y, tooltip=tooltip,
            color=alt.condition("datum.markiert", alt.value(MARKIERT), alt.value(FARBSTUFEN["neutral"][3])),
            size=alt.condition("datum.markiert", alt.value(170), alt.value(80))),
        basis.mark_text(dy=-10, fontSize=11, color=vorne).encode(x=x, y=y, text="name:N"),
    ]
    # Beschriftung der vier Felder in den Ecken der Zeichenfläche (Pixel, unabhängig von den Daten)
    ecken = (("width - 6", "12", "right"), ("6", "12", "left"), ("6", "height - 6", "left"),
             ("width - 6", "height - 6", "right"))
    for text, (px, py, ausrichtung) in zip(felder, ecken, strict=True):
        if text:
            ebenen.append(alt.Chart(pd.DataFrame({"text": [text]})).mark_text(
                align=ausrichtung, fontSize=12, fontStyle="italic", color="#9aa59f" if dunkel else "#5d6a63",
                x={"expr": px}, y={"expr": py}).encode(text="text:N"))
    return _ohne_rahmen(alt.layer(*ebenen).properties(height=460))


def mini_karte(gdf, kennzahl: str, stufen: Stufen, einheit: str = "", stellen: int = 1,
               hoehe: int = 180, breite: int = 260) -> alt.Chart:
    """Kleine Karte ohne Hintergrund: Stadtteile in den Farben ihrer Stufe, Name und Wert beim Überfahren.

    `gdf` ist ein GeoDataFrame mit stadtteil und der Kennzahl (zum Beispiel Ergebnis.geometrie)."""
    from .geo import fuer_karte

    daten = fuer_karte(gdf[[c for c in ("stadtteil", kennzahl, "geometry") if c in gdf.columns]], toleranz_m=25)
    daten = daten.assign(farbe=[stufen.farbe(w) for w in daten[kennzahl]]).rename(columns={kennzahl: "wert"})
    # d3-geo (vega) erwartet Außenringe im Uhrzeigersinn, GeoJSON gegen den Uhrzeigersinn
    daten["geometry"] = shapely.orient_polygons(daten.geometry.values, exterior_cw=True)
    titel = f"Wert ({einheit})" if einheit else "Wert"
    tooltip = [alt.Tooltip("properties.wert:Q", title=titel, format=_d3_format(stellen))]
    if "stadtteil" in daten.columns:
        tooltip.insert(0, alt.Tooltip("properties.stadtteil:N", title="Stadtteil"))
    # Als GeoJSON-Werte übergeben: einen GeoDataFrame wandelt Streamlit in eine Tabelle um, die Flächen gingen verloren
    merkmale = json.loads(daten.to_json(drop_id=True))["features"]
    chart = alt.Chart(alt.Data(values=merkmale)).mark_geoshape(stroke="#ffffff", strokeWidth=0.6).encode(
        color=alt.Color("properties.farbe:N", scale=None), tooltip=tooltip).project("mercator")
    # feste Breite: die Projektion passt sich beim ersten Zeichnen an, bei Breite „container“ wäre sie 0
    return _ohne_rahmen(chart.properties(height=hoehe, width=breite))


def werte_verteilung(werte: pd.DataFrame, stetig: bool, farbe: str = FARBSTUFEN["neutral"][3]) -> alt.Chart:
    """Verteilung der Werte eines Rasters: Klassen als Balken je Wert, stetige Werte als Histogramm.

    `werte` hat bei Klassen die Spalten wert, zellen, sonst von, bis, zellen (aus vorschau.raster_vorschau)."""
    if stetig:
        chart = alt.Chart(werte).mark_bar(color=farbe, binSpacing=1).encode(
            x=alt.X("von:Q", bin="binned", title="Wert", axis=alt.Axis(format=",.4~g")), x2="bis:Q",
            y=alt.Y("zellen:Q", title="Zellen", axis=alt.Axis(format=",d")),
            tooltip=[alt.Tooltip("von:Q", title="von", format=",.4~g"), alt.Tooltip("bis:Q", title="bis", format=",.4~g"),
                     alt.Tooltip("zellen:Q", title="Zellen", format=",d")])
    else:
        chart = alt.Chart(werte).mark_bar(color=farbe).encode(
            x=alt.X("wert:O", title="Wert", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("zellen:Q", title="Zellen", axis=alt.Axis(format=",d")),
            tooltip=[alt.Tooltip("wert:O", title="Wert"), alt.Tooltip("zellen:Q", title="Zellen", format=",d")])
    return _ohne_rahmen(chart.properties(height=220))


def korrelation_heatmap(matrix: pd.DataFrame, dunkel: bool = False) -> alt.LayerChart:
    """Korrelationsmatrix als Feldergitter: blau steigen gemeinsam, orange gegenläufig, Zahl im Feld.

    `dunkel` färbt die Mitte der Skala und die Zahlen auf schwachen Feldern für das dunkle Thema."""
    if matrix.empty:
        return alt.layer(alt.Chart(pd.DataFrame()).mark_point())
    reihenfolge = list(matrix.columns)
    lang = matrix.rename_axis("zeile").reset_index().melt(id_vars="zeile", var_name="spalte", value_name="r")
    lang["text"] = [("–" if pd.isna(r) else f"{r:.2f}".replace(".", ",")) for r in lang["r"]]
    lang["hell"] = lang["r"].abs() > 0.6
    basis = alt.Chart(lang).encode(
        x=alt.X("spalte:N", sort=reihenfolge, title=None, axis=alt.Axis(labelAngle=-35, labelLimit=160)),
        y=alt.Y("zeile:N", sort=reihenfolge, title=None, axis=alt.Axis(labelLimit=180)))
    felder = basis.mark_rect(cornerRadius=3).encode(
        color=alt.Color("r:Q", title="Zusammenhang", scale=alt.Scale(
            domain=[-1, 0, 1], range=[FARBSTUFEN["waerme"][2], "#1b241f" if dunkel else "#f4f5f3",
                                       FARBSTUFEN["neutral"][3]]),
            legend=alt.Legend(format=".1f", orient="bottom", gradientLength=220)),
        tooltip=[alt.Tooltip("zeile:N", title="Thema"), alt.Tooltip("spalte:N", title="mit"),
                 alt.Tooltip("r:Q", title="r", format=".2f")])
    zahlen = basis.mark_text(fontSize=12).encode(
        text="text:N", color=alt.condition("datum.hell", alt.value("#ffffff"), alt.value(HELL if dunkel else DUNKEL)))
    groesse = max(220, 52 * len(reihenfolge))
    return _ohne_rahmen(alt.layer(felder, zahlen).properties(height=groesse, width=groesse))


__all__ = ["KEINE_DATEN", "balken_sortiert", "korrelation_heatmap", "punktleiste", "streu_quadranten"]


# Linienfarben für Zeitreihen: aus den geprüften Stufen, gut unterscheidbar; die erste Reihe ist die gewählte
REIHEN_FARBEN = (MARKIERT, "#2f73a6", "#5d6a63", "#3b8432", "#e9a23e", "#7aaed6", "#912813", "#8cc274")
VERGLEICH_FARBE = "#912813"
VERGLEICH_FARBE_DUNKEL = "#f0876a"  # redColor des dunklen Themas


def zeitverlauf(daten: pd.DataFrame, einheit: str, trend: pd.DataFrame | None = None,
                vergleich: dict[str, float] | None = None, marken: dict[int, str] | None = None,
                stellen: int = 1, hoehe: int = 420, dunkel: bool = False) -> alt.LayerChart:
    """Linien je Reihe über die Jahre, mit Trendgeraden, waagerechten Vergleichswerten und senkrechten Marken.

    `daten` braucht jahr, reihe, wert, vollstaendig (unvollständige Jahre erscheinen blass). Die Reihenfolge der
    Reihen in `daten` bestimmt die Farben; die erste bekommt die Markierfarbe. `dunkel` hellt Achsen und Gitter
    für das dunkle Thema auf."""
    achse, linie = ("#9aa59f", "#4a5650") if dunkel else ("#5d6a63", "#c9cfcb")
    grenzwert = VERGLEICH_FARBE_DUNKEL if dunkel else VERGLEICH_FARBE
    reihen = list(dict.fromkeys(daten["reihe"]))
    farbe = alt.Color("reihe:N", title=None, sort=reihen,
                      scale=alt.Scale(domain=reihen, range=list(REIHEN_FARBEN[:len(reihen)]) or None),
                      legend=alt.Legend(orient="bottom", labelLimit=260))
    x = alt.X("jahr:Q", title=None, axis=alt.Axis(format="d", labelColor=achse, domainColor=linie,
                                                   tickCount=8))
    y = alt.Y("wert:Q", title=einheit, scale=alt.Scale(zero=einheit != "°C"),
              axis=alt.Axis(labelColor=achse, titleColor=achse, grid=True, gridColor=linie,
                            gridOpacity=0.35, domain=False, ticks=False))
    def linien(teil: pd.DataFrame, breite: float) -> alt.Chart:
        return alt.Chart(teil).mark_line(point=alt.OverlayMarkDef(size=22), strokeWidth=breite).encode(
            x=x, y=y, color=farbe,
            opacity=alt.condition("datum.vollstaendig", alt.value(1.0), alt.value(0.35)),
            tooltip=[alt.Tooltip("jahr:Q", format="d", title="Jahr"), alt.Tooltip("reihe:N", title="Reihe"),
                     alt.Tooltip("wert:Q", title=einheit, format=_d3_format(stellen))],
        )

    # die gewählte (erste) Reihe zuletzt und etwas kräftiger zeichnen, damit sie oben liegt
    erste = daten["reihe"] == (reihen[0] if reihen else None)
    ebenen = [linien(daten[~erste], 1.6), linien(daten[erste], 2.6)]
    if vergleich:
        regeln = pd.DataFrame({"text": list(vergleich), "wert": list(vergleich.values())})
        ebenen.append(alt.Chart(regeln).mark_rule(strokeDash=[4, 4], color=grenzwert).encode(
            y="wert:Q", tooltip="text:N"))
        ebenen.append(alt.Chart(regeln).mark_text(align="left", dx=4, dy=-6, color=grenzwert).encode(
            y="wert:Q", text="text:N", x=alt.value(0)))
    if trend is not None and not trend.empty:
        ebenen.append(alt.Chart(trend).mark_line(strokeDash=[6, 4], strokeWidth=2, opacity=0.8).encode(
            x="jahr:Q", y="wert:Q", color=alt.Color("reihe:N", legend=None, sort=reihen,
                                                    scale=alt.Scale(domain=reihen,
                                                                    range=list(REIHEN_FARBEN[:len(reihen)])))))
    jahre = (daten["jahr"].min(), daten["jahr"].max()) if len(daten) else (0, 0)
    marken_df = pd.DataFrame([{"jahr": j, "text": t} for j, t in (marken or {}).items() if jahre[0] <= j <= jahre[1]])
    if not marken_df.empty:
        ebenen.append(alt.Chart(marken_df).mark_rule(color=achse, strokeDash=[2, 3]).encode(
            x="jahr:Q", tooltip=alt.Tooltip("text:N", title="Hinweis")))
        ebenen.append(alt.Chart(marken_df).mark_text(align="left", dx=4, y=8, color=achse, fontSize=11).encode(
            x="jahr:Q", text="text:N"))
    return _ohne_rahmen(alt.layer(*ebenen).properties(height=hoehe))


# Farben für Anteile, die zusammen 100 % ergeben (Analyse.zusammensetzung), in der Reihenfolge der Spalten:
# belastet/dicht zuerst, Grün zuletzt; Grau für die Mitte
FARBEN_ZUSAMMENSETZUNG = (FARBSTUFEN["waerme"][4], FARBSTUFEN["waerme"][1], "#9aa59f", FARBSTUFEN["gruen"][3])


def anteile_gestapelt(tabelle: pd.DataFrame, spalten, markiert: str | None = None, stellen: int = 1,
                      dunkel: bool = False, hoehe_je_zeile: int = 18) -> alt.Chart:
    """Ein Balken je Stadtteil, gestapelt aus Anteilen (Spalte(feld, titel)), sortiert nach dem ersten Anteil.

    `tabelle` braucht gebiet_id, stadtteil und die Felder. Der markierte Stadtteil ist fett beschriftet. Die Legende
    steht nicht im Diagramm (Streamlit schneidet sie beim Einpassen ab), sondern kommt aus `legende_zusammensetzung`."""
    felder = [s.feld for s in spalten if s.feld in tabelle.columns]
    titel = {s.feld: s.titel for s in spalten}
    daten = tabelle.dropna(subset=felder[:1])
    reihenfolge = list(daten.sort_values(felder[0], ascending=False)["stadtteil"])
    lang = daten.melt(id_vars=["gebiet_id", "stadtteil"], value_vars=felder, var_name="feld", value_name="anteil")
    # als Zahl, auch wenn die Zeile aus einer gemischten Tabelle kommt (sonst überträgt Streamlit Text)
    lang["anteil"] = pd.to_numeric(lang["anteil"], errors="coerce")
    lang["teil"] = lang["feld"].map(titel)
    lang["nummer"] = lang["feld"].map({f: i for i, f in enumerate(felder)})
    vorne = HELL if dunkel else DUNKEL
    farben = list(FARBEN_ZUSAMMENSETZUNG[:len(felder)])
    y = alt.Y("stadtteil:N", sort=reihenfolge, title=None,
              axis=alt.Axis(labelLimit=160, labelColor=vorne, labelFontWeight=alt.ExprRef(
                  expr=f"datum.value == {json.dumps(_name_von(daten, markiert))} ? 'bold' : 'normal'")))
    return _ohne_rahmen(alt.Chart(lang).mark_bar(size=hoehe_je_zeile - 4).encode(
        x=alt.X("anteil:Q", stack="zero", title="Anteil in %", scale=alt.Scale(domain=[0, 100])),
        y=y,
        color=alt.Color("teil:N", sort=[titel[f] for f in felder], title=None,
                        scale=alt.Scale(domain=[titel[f] for f in felder], range=farben), legend=None),
        order=alt.Order("nummer:Q"),
        tooltip=[alt.Tooltip("stadtteil:N", title="Stadtteil"), alt.Tooltip("teil:N", title="Teil"),
                 alt.Tooltip("anteil:Q", title="Anteil in %", format=_d3_format(stellen))],
    # Streamlit passt Diagramme mit width="stretch" ein: die Höhe umfasst dann auch die Achse darunter
    ).properties(height=hoehe_je_zeile * max(1, len(reihenfolge)) + 45))


def legende_zusammensetzung(spalten) -> list[tuple[str, str]]:
    """(Farbe, Text) je Teil für karte.legende_html_eintraege, in der Reihenfolge der Balken."""
    return list(zip(FARBEN_ZUSAMMENSETZUNG[:len(spalten)], [s.titel for s in spalten], strict=True))


def _name_von(daten: pd.DataFrame, gebiet_id: str | None) -> str:
    treffer = daten.loc[daten["gebiet_id"].astype(str) == str(gebiet_id), "stadtteil"]
    return str(treffer.iloc[0]) if len(treffer) else ""
