"""Daten erklärt: jeder Datensatz in Worten – Herkunft, Inhalt, Nutzen und wie man ihn liest. Lädt und rechnet nichts."""

import streamlit as st

from essen import datenerklaerung, laden
from essen.app.gemeinsam import THEMA_SYMBOL, katalog, kopf, seitenhilfe

kopf("Daten erklärt")
seitenhilfe("daten_erklaert")
k = katalog()

suche = st.text_input("Suche in allen Erklärungen", placeholder="z. B. Hitze, Bäume, Wetterdienst",
                      key="daten-erklaert-suche")
gruppen = datenerklaerung.nach_thema(k, suche)
if not gruppen:
    st.info("Kein Datensatz passt zu diesem Suchwort. Versuchen Sie ein anderes Wort.", icon=":material/search_off:")
    st.stop()

thema_von = {ds.id: titel for titel, liste in gruppen.items() for ds in liste}
ids = list(thema_von)
vorwahl = st.query_params.get("datensatz")
kennung = st.selectbox(f"Datensatz ({len(ids)} von {len(k.datensaetze)})", ids,
                       index=ids.index(vorwahl) if vorwahl in ids else 0,
                       format_func=lambda i: f"{k.datensatz(i).titel} · {thema_von[i]}", key="daten-erklaert-wahl")
st.query_params["datensatz"] = kennung
ds = k.datensatz(kennung)
s = datenerklaerung.steckbrief(k, ds)

st.subheader(s.titel)
st.markdown(f"*{s.kurz}*")

text, blick = st.columns([2, 1], gap="large")
with text:
    if not s.ausfuehrlich:
        st.info("Für diesen Datensatz gibt es noch keine ausführliche Erklärung. Oben steht die kurze Beschreibung "
                "aus dem Katalog.", icon=":material/info:")
    for ueberschrift, absatz in s.abschnitte:
        st.markdown(f"#### {ueberschrift}")
        st.markdown(absatz)

with blick:
    with st.container(border=True):
        st.markdown("**Auf einen Blick**")
        st.markdown(f":material/apartment: **Von:** {s.anbieter}"
                    + (f"  \n:material/hub: **Über:** {s.portal}" if s.portal != s.anbieter else ""))
        if s.raum:
            st.markdown(f":material/location_on: **Gebiet:** {s.raum}")
        if s.stand:
            st.markdown(f":material/schedule: **Stand:** {s.stand}")
        st.markdown(f":material/license: **Nutzung:** {s.lizenz}")
        st.caption(s.bezug)
        if s.seite:
            st.link_button("Zur Seite der Quelle", s.seite, icon=":material/open_in_new:", width="stretch")
    if s.themen:
        with st.container(border=True):
            st.markdown("**Genutzt in diesen Themen**")
            for analyse_id, titel in s.themen:
                st.page_link("seiten/themen.py", label=titel, icon=THEMA_SYMBOL.get(analyse_id, ":material/insights:"),
                             query_params={"thema": analyse_id})
    else:
        st.caption("Die App rechnet mit diesem Datensatz noch kein Thema aus. Er steht im Katalog, weil er für Essen "
                   "nützlich sein kann.")
    with st.expander("Für Fortgeschrittene: Dateien ansehen", icon=":material/construction:"):
        st.caption(s.portal_text)
        if laden.vorhanden(ds):
            st.page_link("seiten/originaldaten.py", label="In der Werkstatt ansehen", icon=":material/table_view:",
                         query_params={"datensatz": ds.id})
        elif ds.download.art != "keiner":
            st.page_link("seiten/datenkatalog.py", label="In der Werkstatt laden", icon=":material/database:",
                         query_params={"suche": ds.titel})
