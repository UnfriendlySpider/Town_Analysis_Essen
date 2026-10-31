"""Anzeige der Karte über die Jahre: große Karte mit Abspielen und Schieber, darunter kleine Karten je Schritt.

Die Daten kommen fertig aus essen.zeitkarte.daten(); hier wird nur gezeichnet und umgefärbt (Streamlit-Komponente,
läuft im Browser ohne Neuladen). Ein Klick auf einen Stadtteil meldet seine gebiet_id zurück.
"""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

_HTML = """
<div class="zk">
  <div class="kopf">
    <button type="button" class="spielen" aria-label="Abspielen" aria-pressed="false">▶</button>
    <div class="zeit"><b class="schritt"></b> <span class="unter"></span></div>
  </div>
  <input type="range" class="regler" min="0" value="0" step="1" aria-label="Zeitpunkt">
  <div class="buehne">
    <svg class="karte" role="group"></svg>
    <div class="tipp" hidden></div>
  </div>
  <div class="seite">
    <div class="legende"></div>
    <div class="raster"></div>
  </div>
</div>
"""

_CSS = """
.zk { font-family: var(--st-font, system-ui, sans-serif); color: var(--st-text-color); font-size: .875rem;
  display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); column-gap: 24px; align-items: start; }
.kopf, .regler { grid-column: 1 / -1; }
@media (max-width: 900px) { .zk { grid-template-columns: minmax(0, 1fr); } }
.kopf { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.spielen { width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--st-border-color);
  background: var(--st-primary-color); color: var(--st-background-color); font-size: 1rem; cursor: pointer; flex: none; }
.spielen:focus-visible { outline: 3px solid var(--st-primary-color); outline-offset: 2px; }
.schritt { font-size: 1.5rem; }
.unter { opacity: .75; }
.regler { width: 100%; accent-color: var(--st-primary-color); margin: 4px 0 8px; }
.buehne { position: relative; }
.karte { width: 100%; height: auto; display: block; max-height: 520px; }
.karte path { stroke: var(--st-background-color); stroke-width: 1.5; transition: fill .35s; cursor: pointer; }
.karte path:hover, .karte path:focus-visible { stroke: var(--st-text-color); stroke-width: 3; outline: none; }
.karte path.markiert { stroke: var(--st-text-color); stroke-width: 4; }
.tipp { position: absolute; pointer-events: none; background: var(--st-secondary-background-color);
  color: var(--st-text-color); border: 1px solid var(--st-border-color); border-radius: 6px; padding: 4px 8px;
  white-space: nowrap; font-size: .8125rem; box-shadow: 0 2px 6px rgba(0,0,0,.15); }
.legende { display: flex; flex-wrap: wrap; gap: 4px 14px; margin: 4px 0 12px; font-size: .8125rem; }
.legende i { display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: -2px; margin-right: 5px; }
.raster { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 6px; }
.raster button { background: none; border: 2px solid transparent; border-radius: 8px; padding: 4px; cursor: pointer;
  color: var(--st-text-color); font: inherit; font-size: .75rem; }
.raster button:focus-visible { outline: 3px solid var(--st-primary-color); outline-offset: 1px; }
.raster button.aktiv { border-color: var(--st-primary-color); }
.raster svg { width: 100%; height: auto; display: block; }
.raster path { stroke: var(--st-background-color); stroke-width: 3; }
"""

_JS = """
const ZUSTAND = new WeakMap();
const NS = "http://www.w3.org/2000/svg";

export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component;
  if (!data || !data.schritte || !data.schritte.length) return;
  const wurzel = parentElement.querySelector(".zk");
  const karte = wurzel.querySelector(".karte");
  const regler = wurzel.querySelector(".regler");
  const knopf = wurzel.querySelector(".spielen");
  const tipp = wurzel.querySelector(".tipp");
  const raster = wurzel.querySelector(".raster");
  const n = data.schritte.length;
  let z = ZUSTAND.get(parentElement);
  if (!z) { z = { uhr: null }; ZUSTAND.set(parentElement, z); }
  z.nummer = Math.min(Math.max(data.schritt ?? n - 1, 0), n - 1);

  const box = `0 0 ${data.breite} ${data.hoehe}`;
  karte.setAttribute("viewBox", box);
  karte.setAttribute("aria-label", data.titel);
  karte.replaceChildren();
  const flaechen = data.pfade.map((p, i) => {
    const el = document.createElementNS(NS, "path");
    el.setAttribute("d", p.d);
    if (p.gebiet_id === data.markiert) el.classList.add("markiert");
    // per Tastatur erreichbar: Tab springt von Stadtteil zu Stadtteil, Enter oder Leertaste wählt ihn aus
    el.setAttribute("tabindex", "0");
    el.setAttribute("role", "button");
    const zeigeTipp = (x, y) => {
      const r = wurzel.querySelector(".buehne").getBoundingClientRect();
      tipp.hidden = false;
      tipp.textContent = `${p.name}: ${data.schritte[z.nummer].texte[i]}`;
      tipp.style.left = `${Math.max(0, Math.min(x - r.left + 12, r.width - tipp.offsetWidth - 4))}px`;
      tipp.style.top = `${y - r.top + 12}px`;
    };
    const mitte = () => { const b = el.getBoundingClientRect(); zeigeTipp(b.left + b.width / 2, b.top + b.height / 2); };
    el.addEventListener("mousemove", (e) => zeigeTipp(e.clientX, e.clientY));
    el.addEventListener("touchstart", mitte, { passive: true });
    el.addEventListener("focus", mitte);
    el.addEventListener("mouseleave", () => { tipp.hidden = true; });
    el.addEventListener("blur", () => { tipp.hidden = true; });
    el.addEventListener("click", () => setTriggerValue("gebiet", p.gebiet_id));
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setTriggerValue("gebiet", p.gebiet_id); }
    });
    karte.appendChild(el);
    return el;
  });
  // markierten Stadtteil zuletzt zeichnen, damit seine Kontur oben liegt
  flaechen.filter((el) => el.classList.contains("markiert")).forEach((el) => karte.appendChild(el));

  wurzel.querySelector(".legende").replaceChildren(...data.legende.map((l) => {
    const s = document.createElement("span");
    const i = document.createElement("i");
    i.style.background = l.farbe;
    s.append(i, l.text);
    return s;
  }));

  raster.replaceChildren();
  raster.hidden = !data.raster;
  const minis = data.raster ? data.schritte.map((s, k) => {
    const b = document.createElement("button");
    b.type = "button";
    b.title = s.untertitel || s.titel;
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", box);
    svg.setAttribute("aria-hidden", "true");
    data.pfade.forEach((p, i) => {
      const el = document.createElementNS(NS, "path");
      el.setAttribute("d", p.d);
      el.setAttribute("fill", s.farben[i]);
      svg.appendChild(el);
    });
    b.append(svg, s.titel);
    b.addEventListener("click", () => { halt(); zeige(k, true); });
    raster.appendChild(b);
    return b;
  }) : [];

  function zeige(k, merken) {
    z.nummer = k;
    const s = data.schritte[k];
    flaechen.forEach((el, i) => {
      el.setAttribute("fill", s.farben[i]);
      el.setAttribute("aria-label", `${data.pfade[i].name}: ${s.texte[i]}`);
    });
    wurzel.querySelector(".schritt").textContent = s.titel;
    wurzel.querySelector(".unter").textContent = s.untertitel;
    regler.value = String(k);
    regler.setAttribute("aria-valuetext", s.titel);
    minis.forEach((b, i) => b.classList.toggle("aktiv", i === k));
    if (merken) setStateValue("schritt", k);
  }
  function halt() {
    if (z.uhr) { clearInterval(z.uhr); z.uhr = null; }
    knopf.textContent = "▶";
    knopf.setAttribute("aria-label", "Abspielen");
    knopf.setAttribute("aria-pressed", "false");
  }
  function spiele() {
    if (z.nummer >= n - 1) zeige(0, false);
    knopf.textContent = "❚❚";
    knopf.setAttribute("aria-label", "Anhalten");
    knopf.setAttribute("aria-pressed", "true");
    z.uhr = setInterval(() => {
      if (z.nummer >= n - 1) { halt(); setStateValue("schritt", z.nummer); return; }
      zeige(z.nummer + 1, false);
    }, data.takt_ms || 900);
  }

  regler.max = String(n - 1);
  regler.oninput = () => { halt(); zeige(Number(regler.value), false); };
  regler.onchange = () => setStateValue("schritt", Number(regler.value));
  knopf.onclick = () => (z.uhr ? (halt(), setStateValue("schritt", z.nummer)) : spiele());
  if (!z.uhr) halt();
  zeige(z.nummer, false);
  return () => { if (z.uhr) clearInterval(z.uhr); ZUSTAND.delete(parentElement); };
}
"""



def _komponente():
    # Bei jedem Aufruf anmelden (ein Eintrag im Verzeichnis der laufenden App, billig): eine Anmeldung nur beim
    # Import ginge verloren, wenn Streamlit neu startet, das Modul aber geladen bleibt (z. B. in Tests).
    return st.components.v2.component("essen_zeitkarte", html=_HTML, css=_CSS, js=_JS)


def zeitkarte(daten: dict, *, key: str, markiert: str | None = None, raster: bool = True, takt_ms: int = 900,
              bei_klick: Callable[[str], None] | None = None) -> str | None:
    """Zeigt die Karte über die Jahre und gibt die gebiet_id eines angeklickten Stadtteils zurück (sonst None).

    `daten` kommt aus essen.zeitkarte.daten(). Der gewählte Zeitpunkt bleibt beim Neulauf erhalten
    (zuerst der letzte). `raster` zeigt darunter alle Zeitpunkte als kleine Karten. `bei_klick` läuft vor dem
    Neulauf der Seite und darf deshalb Auswahlfelder umstellen (st.session_state)."""
    def geklickt() -> None:
        gebiet = getattr(st.session_state.get(key), "gebiet", None)
        if bei_klick and gebiet:
            bei_klick(str(gebiet))

    gemerkt = st.session_state.get(key) or {}
    schritt = gemerkt.get("schritt")
    if schritt is None or schritt >= len(daten["schritte"]):
        schritt = len(daten["schritte"]) - 1
    ergebnis = _komponente()(data={**daten, "schritt": schritt, "markiert": markiert, "raster": raster,
                                 "takt_ms": takt_ms},
                           key=key, on_schritt_change=lambda: None, on_gebiet_change=geklickt)
    return getattr(ergebnis, "gebiet", None)


def abschnitt(analyse, ergebnis, *, key: str, markiert: str | None = None, feld: str | None = None,
              bei_klick: Callable[[str], None] | None = None) -> None:
    """Karte über die Jahre mit Wahl von Jahrzehnten oder Einzeljahren (und des Werts, wenn `feld` fehlt)."""
    from essen import pfade, zeitkarte as zk
    from essen.app.gemeinsam import zeitkarte_daten

    werte = zk.verfuegbar(analyse, ergebnis)
    if not werte:
        return
    auswahl = st.container(horizontal=True, gap="medium")  # bricht in schmalen Spalten um
    if feld is None and len(werte) > 1:
        with auswahl:
            feld = st.pills("Welche Zahl?", [z.feld for z in werte], default=werte[0].feld,
                            format_func={z.feld: z.titel for z in werte}.get, key=f"{key}-feld")
    zeitwert = next((z for z in werte if z.feld == feld), werte[0])
    art = "jahre"
    if zeitwert.jahrzehnte:
        jahre = ergebnis.jahreswerte.dropna(subset=[zeitwert.feld])["jahr"]
        lang = jahre.max() - jahre.min() >= 30  # kurze Reihen: Jahrzehnte ergäben nur zwei, drei Bilder
        with auswahl:
            art = st.segmented_control("Zeitschritte", ["jahrzehnte", "jahre"], default="jahrzehnte" if lang else "jahre",
                                       format_func={"jahrzehnte": "Jahrzehnte", "jahre": "Einzelne Jahre"}.get,
                                       key=f"{key}-art", help="Jahrzehnte sind Mittel über bis zu zehn Jahre und "
                                       "zeigen den Verlauf ruhiger; einzelne Jahre schwanken stark.") \
                or ("jahrzehnte" if lang else "jahre")
    jahrzehnte = art == "jahrzehnte"
    daten = zeitkarte_daten(analyse.id, zeitwert.feld, jahrzehnte, ergebnis.erstellt, str(pfade.daten()))
    st.markdown(f"**{daten['titel']}**")
    wenige = len(daten["schritte"]) <= 10  # mehr kleine Karten würden eine lange Spalte
    zeitkarte(daten, key=f"{key}-karte-{zeitwert.feld}-{art}", markiert=markiert, raster=jahrzehnte or wenige,
              takt_ms=900 if jahrzehnte or wenige else 350, bei_klick=bei_klick)
    st.caption("▶ spielt die Zeitpunkte nacheinander ab; mit dem Schieber wählen Sie einen Zeitpunkt"
               + (", mit den kleinen Karten springen Sie direkt hin" if jahrzehnte or wenige else "")
               + ". Die Farbstufen sind für alle Zeitpunkte gleich. Zeigen oder tippen Sie auf einen Stadtteil (oder "
                 "springen Sie mit der Tabulatortaste), um den Wert zu sehen; ein Klick oder Enter wählt ihn aus." + (f" {zeitwert.hinweis}" if zeitwert.hinweis else ""))
