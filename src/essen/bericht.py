"""Eigenständige HTML-Seite für ein Ergebnis je Stadtteil: Karte, sortierbare Tabelle, Quellen.

Die Seite ist eine einzelne Datei unter data/export/. Sie lädt MapLibre von unpkg und die
Hintergrundkarte von basemap.de; ohne Internet bleibt die Karte leer, die Tabelle geht trotzdem.
Vor einer Weitergabe den Skill lizenz-pruefen beachten.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
from pathlib import Path

from . import pfade
from .analysen.basis import Analyse, Ergebnis
from .geo import fuer_karte
from .katalog import Katalog, quellenangabe
from .laden import lese_abruf


def _runde_geometrie(geometrie: dict) -> dict:
    def runde(koordinaten):
        if isinstance(koordinaten[0], (int, float)):
            return [round(koordinaten[0], 5), round(koordinaten[1], 5)]
        return [runde(k) for k in koordinaten]
    return {"type": geometrie["type"], "coordinates": runde(geometrie["coordinates"])}


def _json_fuer_script(daten) -> str:
    """JSON so maskieren, dass es ein <script>-Element nicht beenden kann."""
    text = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    for zeichen, ersatz in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        text = text.replace(zeichen, ersatz)
    return text


def _ohne_nan(wert):
    if isinstance(wert, float) and math.isnan(wert):
        return None
    return wert


def hat_seite(analyse: Analyse, ergebnis: Ergebnis) -> bool:
    return ergebnis.geometrie is not None and analyse.stufen is not None


def schreibe(katalog: Katalog, analyse: Analyse, ergebnis: Ergebnis, ziel: Path | None = None) -> Path:
    """Schreibt die Seite nach data/export/<analyse>.html (oder `ziel`) und gibt den Pfad zurück."""
    ziel = ziel or pfade.export() / f"{analyse.id}.html"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(html_seite(katalog, analyse, ergebnis), encoding="utf-8")
    return ziel


def html_seite(katalog: Katalog, analyse: Analyse, ergebnis: Ergebnis) -> str:
    """Die eigenständige Seite als Text."""
    if not hat_seite(analyse, ergebnis):
        raise ValueError("Die HTML-Seite gibt es nur für Ergebnisse je Gebiet mit Farbstufen.")
    felder = ["gebiet_id", *{s.feld for s in analyse.spalten}, analyse.kennzahl]
    daten = fuer_karte(ergebnis.geometrie[[f for f in dict.fromkeys(felder) if f in ergebnis.geometrie.columns] + ["geometry"]])
    geojson = json.loads(daten.to_json(drop_id=True))
    for objekt in geojson["features"]:
        objekt["geometry"] = _runde_geometrie(objekt["geometry"])
        objekt["properties"] = {k: _ohne_nan(v) for k, v in objekt["properties"].items()}
    w, s, o, n = (round(x, 5) for x in daten.total_bounds)
    quellen = []
    for kennung in ergebnis.quellen:
        if kennung in katalog.datensaetze:
            abruf = lese_abruf(kennung)
            quellen.append(quellenangabe(katalog, katalog.datensatz(kennung), abruf.datum if abruf else None))
    quellen.append(f"Hintergrundkarte: © GeoBasis-DE / BKG ({dt.date.today().year}) CC BY 4.0")
    konfig = {
        "kennzahl": analyse.kennzahl,
        "stufen": list(analyse.stufen.grenzen),
        "farben": list(analyse.stufen.farben),
        "texte": list(analyse.stufen.texte),
        "keineFarbe": analyse.stufen.keine_daten,
        "keineText": analyse.stufen.keine_daten_text,
        "spalten": [{"feld": s.feld, "titel": s.titel, "art": s.art, "stellen": s.stellen, "balken": s.balken}
                    for s in analyse.spalten],
        "grenzen": [[w, s], [o, n]],
    }
    hinweise = "".join(f"<li>{html.escape(h)}</li>" for h in ergebnis.hinweise)
    ersetzungen = {
        "__TITEL__": html.escape(analyse.titel),
        "__FRAGE__": html.escape(analyse.frage),
        "__KENNZAHL_TEXT__": html.escape(ergebnis.kennzahl_text),
        "__TESTDATEN__": ('<p class="test">Testlauf mit erfundenen Testdaten: Gebiete und Werte sind nicht echt.</p>'
                          if ergebnis.testdaten else ""),
        "__HINWEISE__": f"<ul>{hinweise}</ul>" if hinweise else "",
        "__QUELLEN__": "".join(f"<li>{html.escape(q)}</li>" for q in quellen),
        "__ERSTELLT__": dt.date.today().strftime("%d.%m.%Y"),
        "__BERECHNET__": ergebnis.erstellt[:10],
        "__DATEN__": _json_fuer_script(geojson),
        "__KONFIG__": _json_fuer_script(konfig),
    }
    seite = VORLAGE
    for platzhalter, wert in ersetzungen.items():
        seite = seite.replace(platzhalter, wert)
    return seite


VORLAGE = r"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITEL__</title>
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">
<style>
:root{color-scheme:light;--bg:#f2f4f0;--surface:#fdfdfb;--ink:#15201b;--ink2:#46524c;--muted:#5f6b65;--line:#e1e5df;--line2:#c3cac4;--focus:#15201b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header,main,footer{max-width:1180px;margin:0 auto;padding:0 16px}
header{padding-top:28px;padding-bottom:12px}
h1{font-size:28px;line-height:1.15;margin:0 0 6px;font-weight:650;letter-spacing:-0.01em}
h2{font-size:18px;margin:0 0 12px;font-weight:650}
.lead{margin:0;color:var(--ink2);max-width:70ch}
.kennzahl{margin-top:14px;font-size:18px;font-weight:600;max-width:70ch}
.entwurf{display:inline-block;margin-top:12px;padding:2px 10px;border:1px dashed var(--muted);border-radius:999px;font-size:12px;font-weight:600;color:var(--ink2)}
.test{background:var(--ink);color:#fff;border-radius:8px;padding:8px 14px;font-weight:600;font-size:13px}
main{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:20px;padding-bottom:24px}
@media (max-width:860px){main{grid-template-columns:minmax(0,1fr)}}
.karte,.liste{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;min-width:0}
#map{height:560px;border-radius:6px;overflow:hidden}
@media (max-width:860px){#map{height:420px}}
.legende{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:12px;font-size:13px;color:var(--ink2)}
.legende span{display:inline-flex;align-items:center;gap:6px}
.legende i{width:14px;height:14px;border-radius:3px;display:inline-block;border:1px solid rgba(0,0,0,.08);opacity:.9}
.liste{max-height:640px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th{position:sticky;top:0;background:var(--surface);text-align:left;font-size:12px;font-weight:600;color:var(--ink2);border-bottom:1px solid var(--line2);padding:6px}
th button{all:unset;cursor:pointer}
th button:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
td{padding:6px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums;vertical-align:middle}
td.zahl,th.zahl{text-align:right;white-space:nowrap}
tr.aktiv td{background:color-mix(in srgb,var(--ink) 7%,transparent)}
.balken{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.balken span{display:block;height:8px;border-radius:0 4px 4px 0;min-width:2px;width:calc(var(--w) * 0.9px);opacity:.9}
.balken em{font-style:normal;min-width:44px;text-align:right;white-space:nowrap}
@media (max-width:520px){.balken span{width:calc(var(--w) * 0.36px)}.balken{gap:6px}td,th{padding:6px 4px}}
.maplibregl-popup-content{font:13px/1.45 system-ui,sans-serif;color:#15201b;padding:8px 10px}
.maplibregl-popup-content b{font-size:14px}
footer{padding-bottom:32px;font-size:13px;color:var(--ink2)}
footer p,footer li{max-width:90ch}
footer ul{margin:4px 0 10px;padding-left:18px}
</style>
</head>
<body>
<header>
__TESTDATEN__
<h1>__TITEL__</h1>
<p class="lead">__FRAGE__</p>
<p class="kennzahl">__KENNZAHL_TEXT__</p>
<span class="entwurf">Privater Entwurf</span>
</header>
<main>
<section class="karte" aria-labelledby="t-karte">
<h2 id="t-karte">Karte</h2>
<div id="map" role="region" aria-label="Karte der Stadtteile, die Farbe zeigt die Kennzahl"></div>
<div class="legende" id="legende" aria-label="Legende"></div>
</section>
<section class="liste" aria-labelledby="t-liste">
<h2 id="t-liste">Alle Stadtteile</h2>
<table><thead><tr id="kopf"></tr></thead><tbody id="zeilen"></tbody></table>
</section>
</main>
<footer>
<p><b>Hinweise zur Rechnung</b></p>
__HINWEISE__
<p><b>Quellen</b></p>
<ul>__QUELLEN__</ul>
<p>Berechnet am __BERECHNET__, Seite erstellt am __ERSTELLT__ mit essen-daten.</p>
</footer>
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script>
const DATEN = __DATEN__;
const K = __KONFIG__;
const fmt = (v, d = 0) => v == null ? "–" : (+v).toLocaleString("de-DE", {minimumFractionDigits: d, maximumFractionDigits: d});
const text = (v, s) => s.art === "text" ? (v ?? "") : v == null ? "–" : s.art === "prozent" ? `${fmt(v, s.stellen)} %` : s.art === "flaeche" ? `${fmt(v, s.stellen)} ha` : fmt(v, s.stellen);
const farbe = v => { if (v == null) return K.keineFarbe; let f = K.farben[0]; K.stufen.forEach((g, i) => { if (v >= g) f = K.farben[Math.min(i, K.farben.length - 1)]; }); return f; };
const legende = document.getElementById("legende");
K.farben.forEach((f, i) => legende.insertAdjacentHTML("beforeend", `<span><i style="background:${f}"></i>${K.texte[i]}</span>`));
legende.insertAdjacentHTML("beforeend", `<span><i style="background:${K.keineFarbe}"></i>${K.keineText}</span>`);

const name = K.spalten.find(s => s.art === "text") || K.spalten[0];
const maxima = {};
for (const s of K.spalten) maxima[s.feld] = Math.max(1, ...DATEN.features.map(f => +f.properties[s.feld] || 0));
const kopf = document.getElementById("kopf");
for (const s of K.spalten) {
  const th = document.createElement("th"); th.scope = "col"; if (s.art !== "text") th.className = "zahl";
  const b = document.createElement("button"); b.type = "button"; b.dataset.sort = s.feld; b.textContent = s.titel;
  th.append(b); kopf.append(th);
}
const zeilen = document.getElementById("zeilen");
let sortierung = {feld: K.kennzahl, ab: true};
function tabelle() {
  const liste = DATEN.features.map(f => f.properties).slice();
  liste.sort((a, b) => {
    const x = a[sortierung.feld], y = b[sortierung.feld];
    if (typeof x === "string" || typeof y === "string") return sortierung.ab ? String(y ?? "").localeCompare(String(x ?? ""), "de") : String(x ?? "").localeCompare(String(y ?? ""), "de");
    return ((y ?? -1) - (x ?? -1)) * (sortierung.ab ? 1 : -1);
  });
  zeilen.innerHTML = "";
  for (const p of liste) {
    const tr = document.createElement("tr"); tr.dataset.id = p.gebiet_id;
    for (const s of K.spalten) {
      const td = document.createElement("td"); const v = p[s.feld];
      if (s.art !== "text") td.className = "zahl";
      if (s.balken) {
        const breite = v == null ? 0 : Math.max(3, Math.round(s.art === "prozent" ? v : 100 * v / maxima[s.feld]));
        td.innerHTML = `<div class="balken"><span style="--w:${breite};background:${farbe(p[K.kennzahl])}"></span><em></em></div>`;
        td.querySelector("em").textContent = text(v, s);
      } else td.textContent = text(v, s);
      tr.append(td);
    }
    tr.addEventListener("mouseenter", () => hervorheben(p.gebiet_id));
    tr.addEventListener("mouseleave", () => hervorheben(null));
    zeilen.append(tr);
  }
}
kopf.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
  const feld = b.dataset.sort; const textspalte = K.spalten.find(s => s.feld === feld).art === "text";
  sortierung = {feld, ab: sortierung.feld === feld ? !sortierung.ab : !textspalte};
  kopf.querySelectorAll("th").forEach(th => th.removeAttribute("aria-sort"));
  b.parentElement.setAttribute("aria-sort", sortierung.ab ? "descending" : "ascending");
  tabelle();
}));
tabelle();

const stufe = ["step", ["coalesce", ["get", K.kennzahl], -1e9], K.keineFarbe];
K.stufen.forEach((g, i) => stufe.push(i === 0 ? -1e8 : g, K.farben[Math.min(i, K.farben.length - 1)]));
const map = new maplibregl.Map({
  container: "map", bounds: K.grenzen, fitBoundsOptions: {padding: 16}, attributionControl: {compact: true},
  style: {version: 8, sources: {
    basemap: {type: "raster", tileSize: 256, maxzoom: 18,
      tiles: ["https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_grau/default/GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png"],
      attribution: '© <a href="https://www.bkg.bund.de">GeoBasis-DE / BKG</a> <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>'},
    gebiete: {type: "geojson", data: DATEN, promoteId: "gebiet_id"}},
  layers: [
    {id: "basemap", type: "raster", source: "basemap"},
    {id: "flaeche", type: "fill", source: "gebiete", paint: {"fill-color": stufe, "fill-opacity": 0.9}},
    {id: "grenze", type: "line", source: "gebiete", paint: {"line-color": "#ffffff", "line-width": 1}},
    {id: "auswahl", type: "line", source: "gebiete", paint: {"line-color": "#15201b",
      "line-width": ["case", ["boolean", ["feature-state", "aktiv"], false], 2.5, 0]}}]}
});
map.addControl(new maplibregl.NavigationControl({showCompass: false}), "top-right");
const popup = new maplibregl.Popup({closeButton: false, closeOnClick: false, offset: 8});
let aktiv = null;
function hervorheben(id) {
  if (aktiv != null) map.setFeatureState({source: "gebiete", id: aktiv}, {aktiv: false});
  zeilen.querySelectorAll("tr.aktiv").forEach(tr => tr.classList.remove("aktiv"));
  aktiv = id;
  if (id == null) { popup.remove(); return; }
  map.setFeatureState({source: "gebiete", id}, {aktiv: true});
  const tr = zeilen.querySelector(`tr[data-id="${CSS.escape(id)}"]`); if (tr) tr.classList.add("aktiv");
}
map.on("mousemove", "flaeche", e => {
  const f = e.features[0]; if (!f) return;
  map.getCanvas().style.cursor = "pointer"; hervorheben(f.properties.gebiet_id);
  const div = document.createElement("div");
  const b = document.createElement("b"); b.textContent = f.properties[name.feld]; div.append(b);
  for (const s of K.spalten) if (s !== name) { div.append(document.createElement("br")); div.append(`${s.titel}: ${text(f.properties[s.feld], s)}`); }
  popup.setLngLat(e.lngLat).setDOMContent(div).addTo(map);
});
map.on("mouseleave", "flaeche", () => { map.getCanvas().style.cursor = ""; hervorheben(null); });
map.on("click", "flaeche", e => {
  const tr = zeilen.querySelector(`tr[data-id="${CSS.escape(e.features[0].properties.gebiet_id)}"]`);
  if (tr) tr.scrollIntoView({block: "center", behavior: "smooth"});
});
</script>
</body>
</html>
"""
