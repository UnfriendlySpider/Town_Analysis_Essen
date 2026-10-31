"""Karte: berechnete Kennzahlen, Stadtteilgrenzen und Kartendienste (WMS) übereinander legen."""

import html

import folium
import pandas as pd
import streamlit as st

from essen import analysen, dienste, karte, laden, pfade, punktebenen
from essen.analysen.basis import Ergebnis
from essen.app.gemeinsam import (
    katalog,
    klickkarte,
    kopf,
    lesehilfe,
    neu_gewaehlt,
    noch_nicht_vorbereitet,
    seitenhilfe,
    stadtteile,
)
from essen.geo import ESSEN_BBOX_WGS84, DatenFehlen
from essen.katalog import anbieter
from essen.laden import DownloadFehler
from essen.text import zahl

kopf("Karte")
seitenhilfe("karte")
k = katalog()


@st.cache_data(ttl=3600, show_spinner="Frage den Kartendienst nach seinen Ebenen …")
def ebenen_von(url: str, art: str) -> list[tuple[str, str]]:
    return [(e.name, e.titel) for e in dienste.ebenen(url, art)]


@st.cache_data(ttl=3600, show_spinner="Lese die Punkte …", max_entries=8)
def punkte_von(kennung: str, stempel: str):
    return punktebenen.lade(kennung)


def _stempel_ebene(datensatz: str) -> str:
    abruf = laden.lese_abruf(datensatz)
    return abruf.zeit if abruf else ""


ergebnisse = {a.id: a for a in analysen.ALLE.values()
              if a.stufen and (e := Ergebnis.ansehen(a.id)) is not None and e.geometrie is not None}
if not ergebnisse:
    noch_nicht_vorbereitet("Für die Themenkarten")

links, rechts = st.columns([1, 3])
with links:
    vorwahl = st.query_params.get("thema")
    auswahl = [None, *ergebnisse]
    wahl = st.selectbox("Was möchten Sie sehen?", auswahl,
                        index=auswahl.index(vorwahl) if vorwahl in ergebnisse else (1 if ergebnisse else 0),
                        format_func=lambda i: "nur die Stadtteilgrenzen" if i is None else ergebnisse[i].thema_titel)
    angebotene_orte = punktebenen.verfuegbar()
    orte = []
    if angebotene_orte:
        orte = st.multiselect("Orte einblenden", [e.id for e in angebotene_orte], key="punktebenen",
                              format_func=lambda i: punktebenen.PUNKTEBENEN[i].titel,
                              placeholder="zum Beispiel kühle Orte",
                              help="Punkte aus den Daten der Stadt und anderer Stellen. Zeigen oder tippen Sie auf "
                                   "einen Punkt, um mehr zu sehen.")
        for kennung in orte:
            ebene = punktebenen.PUNKTEBENEN[kennung]
            st.html(f'<div style="font-size:13px;display:flex;gap:8px;align-items:center">'
                    f'<i style="width:12px;height:12px;border-radius:50%;background:{ebene.farbe};flex:none"></i>'
                    f'<span><b>{html.escape(ebene.titel)}</b>: {html.escape(ebene.beschreibung)}</span></div>')
    if wahl:
        st.query_params["thema"] = wahl
        thema = ergebnisse[wahl]
        tabelle = Ergebnis.ansehen(wahl).tabelle
        st.html(karte.legende_html(thema.stufen, thema.kennzahl_titel, tabelle.get(thema.kennzahl), thema.einheit,
                                   thema.stellen))
        lesehilfe(thema)
    grenzen_zeigen = st.toggle("Stadtteilgrenzen mit Namen", value=laden.vorhanden("stadtteile"),
                               disabled=not laden.vorhanden("stadtteile"))
    info = st.container()
    gewaehlt = []
    with st.expander("Weitere Karten der Anbieter (für Fortgeschrittene)", icon=":material/layers:"):
        st.caption("Originalkarten von Behörden, direkt bei ihnen abgerufen. Sie liegen halb durchsichtig über der "
                   "Karte; mit „Deckkraft“ machen Sie sie kräftiger oder blasser.")
        angebote = [(ds, nr, d) for ds in k.datensaetze.values() for nr, d in enumerate(ds.dienste) if d.art == "wms"]
        for ds, nr, dienst in angebote:
            schluessel = f"{ds.id}-{nr}"
            if st.checkbox(dienst.titel or ds.titel, key=f"wms-{schluessel}",
                           help=f"{ds.beschreibung} · {anbieter(k, ds)}"):
                try:
                    ebenen = ebenen_von(dienst.url, "wms") if not dienst.ebenen else [(e, e) for e in dienst.ebenen]
                except DownloadFehler as fehler:
                    st.error(f"{fehler} Der Dienst ist vielleicht gerade nicht erreichbar; versuchen Sie es später "
                             "noch einmal.", icon=":material/cloud_off:")
                    continue
                if not ebenen:
                    st.warning("Dieser Kartendienst bietet gerade keine Ebenen an. Bitte einen anderen wählen.",
                               icon=":material/warning:")
                    continue
                ebene = st.selectbox("Ebene", ebenen, format_func=lambda e: e[1] or e[0], key=f"ebene-{schluessel}")
                deckkraft = st.slider("Deckkraft", 0.2, 1.0, 0.75, 0.05, key=f"deck-{schluessel}")
                gewaehlt.append((ds, dienst, ebene[0], deckkraft))

with rechts:
    m = karte.neue_karte(ESSEN_BBOX_WGS84, canvas=bool(orte))
    for ds, dienst, ebene, deckkraft in gewaehlt:
        vermerk = f"{anbieter(k, ds)}, {k.lizenz_von(ds).kurz}"
        karte.wms(m, dienst.url, ebene, f"{dienst.titel}: {ebene}", deckkraft, vermerk)
    if wahl:
        analyse = ergebnisse[wahl]
        ergebnis = Ergebnis.laden(wahl)
        karte.kennzahl_flaechen(m, ergebnis.geometrie, analyse.kennzahl, analyse.stufen, analyse.spalten,
                                name=analyse.kennzahl_titel)
    if grenzen_zeigen:
        try:
            karte.umrisse(m, stadtteile(), "Stadtteile", beschriftung="name")
        except (DatenFehlen, ValueError) as fehler:
            st.warning(f"Die Stadtteilgrenzen lassen sich nicht zeigen: {fehler}", icon=":material/warning:")
    for kennung in sorted(orte, key=lambda i: i != "jungbaeume"):  # die vielen Bäume unten, alles andere darüber
        ebene = punktebenen.PUNKTEBENEN[kennung]
        try:
            karte.objekte(m, punkte_von(kennung, _stempel_ebene(ebene.datensatz)), ebene.titel, farbe=ebene.farbe)
        except Exception as fehler:  # noqa: BLE001 - kaputte oder geänderte Datei: Meldung statt Absturz
            st.warning(f"{ebene.titel} lassen sich nicht anzeigen ({fehler}). Laden Sie die Daten unter „Daten "
                       "laden“ neu.", icon=":material/warning:")
    if gewaehlt or wahl or orte:
        folium.LayerControl(collapsed=False).add_to(m)
    geklickt = klickkarte(m, 680, "hauptkarte")
    if neu_gewaehlt(geklickt, "hauptkarte"):
        st.query_params["stadtteil"] = geklickt

with info:
    zeile = None
    if wahl and st.query_params.get("stadtteil"):
        treffer = tabelle[tabelle["gebiet_id"].astype(str) == st.query_params["stadtteil"]]
        zeile = treffer.iloc[0] if len(treffer) else None
    if zeile is not None:
        with st.container(border=True):
            wert = zeile[thema.kennzahl]
            st.markdown(f"**{zeile['stadtteil']}**  \n{thema.kennzahl_titel}: "
                        + (f"**{zahl(wert, thema.stellen)} {thema.einheit}**" if pd.notna(wert)
                           else "kein Wert"))
            st.page_link("seiten/stadtteil.py", label="Alle Themen für diesen Stadtteil",
                         icon=":material/arrow_forward:", query_params={"stadtteil": str(zeile["gebiet_id"])})
    elif wahl:
        st.caption("Klicken Sie auf einen Stadtteil in der Karte, um seinen Wert hier zu sehen.")
if pfade.ist_testdaten():
    with rechts:
        st.caption("Achtung: Kartendienste zeigen echte Daten, Kennzahlen und Grenzen sind erfunden.")
