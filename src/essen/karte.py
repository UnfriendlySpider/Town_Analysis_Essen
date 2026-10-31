"""Karten für die App: folium (Leaflet) mit basemap.de, Kennzahlen je Gebiet und WMS-Diensten.

Die App bettet das erzeugte HTML ein. Für eigenständige Seiten zum Weitergeben siehe bericht.py.
"""

from __future__ import annotations

import datetime as dt
import html
import json

import folium
import geopandas as gpd
import pandas as pd

from .analysen.basis import Spalte, Stufen
from .farben import FARBSTUFEN, KEINE_DATEN  # noqa: F401  (für Seiten der App)
from .geo import fuer_karte
from .text import ist_leer, prozent, zahl

BASEMAP_URL = ("https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_grau/default/"
               "GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png")
ESSEN_MITTE = (51.45, 7.01)

LEAFLET_JS = "https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"
LEAFLET_CSS = "https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"


def basemap_vermerk() -> str:
    return (f'© <a href="https://www.bkg.bund.de">GeoBasis-DE / BKG</a> ({dt.date.today().year}) '
            '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>')


def neue_karte(grenzen: tuple[float, float, float, float] | None = None, canvas: bool = False) -> folium.Map:
    """Leere Karte mit grauer basemap.de. `grenzen` in WGS84: (west, süd, ost, nord).

    `canvas` zeichnet Vektoren auf eine Zeichenfläche statt als SVG: nötig bei vielen tausend Punkten."""
    karte = folium.Map(location=ESSEN_MITTE, zoom_start=11, tiles=None, control_scale=True, prefer_canvas=canvas)
    # Nur Leaflet laden. folium bindet sonst auch jQuery, Bootstrap und Icon-Schriften von fremden Servern ein.
    karte.default_js = [("leaflet", LEAFLET_JS)]
    karte.default_css = [("leaflet_css", LEAFLET_CSS)]
    karte.get_root().header.add_child(folium.Element(
        "<style>.leaflet-container{font:13px/1.4 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;"
        "background:#e9ece7}.leaflet-tooltip{font-size:13px}</style>"))
    folium.TileLayer(tiles=BASEMAP_URL, attr=basemap_vermerk(), name="basemap.de grau", max_zoom=19,
                     overlay=False, control=False).add_to(karte)
    if grenzen:
        west, sued, ost, nord = grenzen
        karte.fit_bounds([[sued, west], [nord, ost]])
    return karte


def formatiere(wert, spalte: Spalte) -> str:
    if spalte.art == "text":
        return "" if ist_leer(wert) else str(wert)
    if ist_leer(wert):
        return "–"
    if spalte.art == "prozent":
        return prozent(wert, spalte.stellen)
    if spalte.art == "flaeche":
        return f"{zahl(wert, spalte.stellen)} ha"
    return zahl(wert, spalte.stellen)


def kennzahl_flaechen(karte: folium.Map, gdf: gpd.GeoDataFrame, kennzahl: str, stufen: Stufen,
                      spalten: tuple[Spalte, ...], name: str = "Kennzahl") -> folium.Map:
    """Färbt Gebiete nach einer Kennzahl. Tooltip zeigt alle Spalten, schon deutsch formatiert."""
    daten = fuer_karte(gdf)
    sichtbar = [s for s in spalten if s.feld in daten.columns]
    eigenschaften = gpd.GeoDataFrame(geometry=daten.geometry, crs=daten.crs)
    for s in sichtbar:  # Werte maskieren: Tooltips setzen sie als HTML ein
        eigenschaften[s.titel] = [html.escape(formatiere(w, s)) for w in daten[s.feld]]
    eigenschaften["_farbe"] = [stufen.farbe(w) for w in daten[kennzahl]]
    if "gebiet_id" in daten.columns:  # für Klicks auf die Karte (app.gemeinsam.klickkarte)
        eigenschaften["gebiet_id"] = daten["gebiet_id"].astype(str)
    geojson = json.loads(eigenschaften.to_json(drop_id=True))
    folium.GeoJson(
        geojson,
        name=name,
        style_function=lambda f: {"fillColor": f["properties"]["_farbe"], "color": "#ffffff", "weight": 1,
                                  "fillOpacity": 0.85},
        highlight_function=lambda f: {"weight": 2.5, "color": "#15201b"},
        tooltip=folium.GeoJsonTooltip(fields=[s.titel for s in sichtbar], aliases=[s.titel for s in sichtbar],
                                      sticky=True, labels=True),
    ).add_to(karte)
    return karte


def umrisse(karte: folium.Map, gdf: gpd.GeoDataFrame, name: str, beschriftung: str | None = None) -> folium.Map:
    daten = fuer_karte(gdf)
    felder = [beschriftung] if beschriftung and beschriftung in daten.columns else None
    if felder:
        daten[beschriftung] = daten[beschriftung].astype(str).map(html.escape)
    kennung = ["gebiet_id"] if "gebiet_id" in daten.columns and beschriftung != "gebiet_id" else []
    if kennung:
        daten["gebiet_id"] = daten["gebiet_id"].astype(str)
    folium.GeoJson(
        json.loads(daten[[*(felder or []), *kennung, "geometry"]].to_json(drop_id=True)),
        name=name,
        style_function=lambda f: {"fillOpacity": 0, "color": "#15201b", "weight": 1, "opacity": 0.7},
        tooltip=folium.GeoJsonTooltip(fields=felder, labels=False) if felder else None,
    ).add_to(karte)
    return karte


def hervorheben(karte: folium.Map, gdf: gpd.GeoDataFrame, name: str) -> folium.Map:
    """Eine oder mehrere Flächen kräftig umrandet und leicht gefüllt, z. B. den gewählten Stadtteil."""
    daten = fuer_karte(gdf)
    folium.GeoJson(
        json.loads(daten[["geometry"]].to_json(drop_id=True)),
        name=html.escape(name),
        style_function=lambda f: {"fillColor": "#b43e03", "fillOpacity": 0.35, "color": "#912813", "weight": 3},
    ).add_to(karte)
    return karte


def objekte(karte: folium.Map, gdf: gpd.GeoDataFrame, name: str, felder: list[str] | None = None,
            farbe: str = "#2f73a6") -> folium.Map:
    """Beliebige Vektorobjekte (Punkte, Linien, Flächen) mit einem Tooltip aus bis zu acht Feldern.

    Für die Vorschau von Originaldaten; Werte werden als Text maskiert."""
    daten = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    if not len(daten):
        return karte
    daten = fuer_karte(daten, toleranz_m=1)
    felder = [f for f in (felder if felder is not None else list(daten.columns)) if f != "geometry"][:8]
    eigenschaften = gpd.GeoDataFrame(geometry=daten.geometry, crs=daten.crs)
    titel = []
    for nummer, f in enumerate(felder):
        spalte = f"f{nummer}"  # Feldnamen der Quelle können Punkte oder Leerzeichen enthalten
        eigenschaften[spalte] = ["–" if ist_leer(w) else html.escape(str(w))[:120] for w in daten[f]]
        titel.append(html.escape(str(f)))
    punkte = daten.geometry.geom_type.isin(["Point", "MultiPoint"]).all()
    radius = 4 if len(daten) <= 3000 else 1.8  # viele Punkte (z. B. 13.000 Bäume) klein, sonst eine Fläche
    folium.GeoJson(
        json.loads(eigenschaften.to_json(drop_id=True)),
        name=html.escape(name),
        marker=folium.CircleMarker(radius=radius, fill=True, fill_opacity=0.85, weight=1 if radius > 3 else 0.5,
                                   color="#ffffff",
                                   fill_color=farbe) if punkte else None,
        style_function=lambda f: {"color": farbe, "weight": 1.5, "fillColor": farbe, "fillOpacity": 0.35},
        highlight_function=lambda f: {"weight": 3, "color": "#15201b"},
        tooltip=folium.GeoJsonTooltip(fields=[f"f{n}" for n in range(len(felder))], aliases=titel, sticky=True)
        if felder else None,
    ).add_to(karte)
    return karte


def rasterbild(karte: folium.Map, bild, grenzen: tuple[float, float, float, float], name: str,
               deckkraft: float = 0.8) -> folium.Map:
    """Ein RGBA-Bild (in Web-Mercator ausgerichtet) über die Karte legen; `grenzen` in WGS84 (west, süd, ost, nord)."""
    west, sued, ost, nord = grenzen
    folium.raster_layers.ImageOverlay(image=bild, bounds=[[sued, west], [nord, ost]], opacity=deckkraft,
                                      name=html.escape(name), mercator_project=False, pixelated=True,
                                      interactive=False, zindex=2).add_to(karte)
    return karte


def wms(karte: folium.Map, url: str, ebene: str, titel: str, deckkraft: float = 0.75, vermerk: str = "") -> folium.Map:
    folium.WmsTileLayer(url=url, layers=ebene, fmt="image/png", transparent=True, name=html.escape(titel),
                        overlay=True, control=True, opacity=deckkraft, attr=html.escape(vermerk or titel),
                        version="1.3.0").add_to(karte)
    return karte


def als_html(karte: folium.Map, mit_ebenenwahl: bool = False) -> str:
    if mit_ebenenwahl:
        folium.LayerControl(collapsed=False).add_to(karte)
    return karte.get_root().render()


def legende_html(stufen: Stufen, titel: str = "", werte=None, einheit: str = "", stellen: int = 1) -> str:
    """Legende als kleines HTML für die App (neben der Karte).

    Mit `werte` (eine Zahl je Gebiet) steht hinter jeder Stufe, wie viele Gebiete sie hat, und darunter das
    Mittel der Gebiete mit Einheit."""
    zaehlung = keine = None
    if werte is not None:
        werte = pd.Series(werte, dtype="float64")
        zaehlung = [0] * len(stufen.farben)
        for wert in werte.dropna():
            zaehlung[stufen.farben.index(stufen.farbe(wert))] += 1
        keine = int(werte.isna().sum())

    def zeile(farbe: str, text: str, anzahl: int | None, deckkraft: str = ".85") -> str:
        zusatz = (f'<span style="margin-left:auto;opacity:.7;font-variant-numeric:tabular-nums">'
                  f'{anzahl}</span>') if anzahl is not None else ""
        return (f'<div style="display:flex;align-items:center;gap:8px;margin:0 0 4px 0;max-width:300px">'
                f'<i style="width:22px;height:14px;border-radius:3px;background:{farbe};opacity:{deckkraft};'
                f'border:1px solid rgba(0,0,0,.08);flex:none"></i>{html.escape(text)}{zusatz}</div>')

    eintraege = "".join(zeile(farbe, text, zaehlung[i] if zaehlung else None)
                        for i, (farbe, text) in enumerate(zip(stufen.farben, stufen.texte, strict=True)))
    if keine is None or keine:
        eintraege += zeile(stufen.keine_daten, stufen.keine_daten_text, keine, "1")
    kopf = f'<div style="font-weight:600;margin-bottom:6px">{html.escape(titel)}</div>' if titel else ""
    if zaehlung:
        kopf += '<div style="font-size:12px;opacity:.7;margin-bottom:4px">Farbe · Anzahl Stadtteile</div>'
    fuss = ""
    if werte is not None and werte.notna().any():
        mittel = f"{zahl(werte.mean(), stellen)}{' ' + html.escape(einheit) if einheit else ''}"
        fuss = f'<div style="margin-top:6px">Mittel der Stadtteile: <b>{mittel}</b></div>'
    return f'<div style="font-size:13px;color:inherit">{kopf}{eintraege}{fuss}</div>'


def legende_html_eintraege(eintraege: list[tuple[str, str]], titel: str = "") -> str:
    """Legende aus (Farbe, Text)-Paaren, etwa aus einer Stildatei; Texte werden maskiert."""
    zeilen = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:0 0 4px 0">'
        f'<i style="width:22px;height:14px;border-radius:3px;background:{html.escape(farbe)};flex:none;'
        f'border:1px solid rgba(0,0,0,.08)"></i>{html.escape(text)}</div>'
        for farbe, text in eintraege[:40])
    mehr = f'<div style="opacity:.7">… und {len(eintraege) - 40} weitere</div>' if len(eintraege) > 40 else ""
    kopf = f'<div style="font-weight:600;margin-bottom:6px">{html.escape(titel)}</div>' if titel else ""
    return f'<div style="font-size:13px;color:inherit">{kopf}{zeilen}{mehr}</div>'
