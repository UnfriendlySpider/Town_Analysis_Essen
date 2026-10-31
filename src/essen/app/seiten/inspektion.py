"""Inspektion: geladene Daten untersuchen, bevor man mit ihnen rechnet."""

import streamlit as st

from essen import pfade
from essen.app.gemeinsam import (
    datensatz_wahl,
    geladene_datensaetze,
    katalog,
    kopf,
    seitenhilfe,
)
from essen.inspizieren import inspiziere_datensatz

kopf("Daten untersuchen")
seitenhilfe("untersuchen")
k = katalog()

geladen = geladene_datensaetze(k)
if not geladen:
    st.info("Noch nichts geladen. Laden Sie unter „Daten laden“ einen Datensatz herunter.", icon=":material/info:")
    st.page_link("seiten/datenkatalog.py", label="Zu „Daten laden“", icon=":material/database:")
    st.stop()

wahl = datensatz_wahl(k, geladen)
datei = pfade.inspektion() / f"{wahl}.md"

st.page_link("seiten/originaldaten.py", label="Die Dateien selbst ansehen (Karte, Tabelle, Bild)",
             icon=":material/table_view:", query_params={"datensatz": wahl})

bericht = None
if st.button("Untersuchen", type="primary", icon=":material/search:"):
    with st.spinner("Lese Dateien … große Raster brauchen einige Sekunden"):
        bericht = inspiziere_datensatz(k, wahl)
        datei = bericht.speichern(wahl)
    st.toast("Bericht gespeichert", icon=":material/check:")

if bericht is not None:
    # frisch erstellt: Abschnitte mit echten Tabellen (sortier- und durchsuchbar) statt Markdown
    st.download_button("Bericht herunterladen (Markdown)", datei.read_bytes(), datei.name, "text/markdown",
                       icon=":material/download:")
    st.caption(f"Gespeichert unter {pfade.relativ(datei)}")
    for abschnitt in bericht.abschnitte:
        with st.container(border=True):
            st.markdown(f"**{abschnitt.titel}**")
            if abschnitt.zeilen:
                st.markdown("\n".join(abschnitt.zeilen))
            if abschnitt.tabelle is not None and not abschnitt.tabelle.empty:
                st.dataframe(abschnitt.tabelle, hide_index=True, width="stretch")
    if bericht.legende:
        with st.container(border=True):
            st.markdown("**Legenden aus Stildateien**")
            st.dataframe([{"Wert": e.wert, "Beschriftung": e.label, "Farbe": e.farbe or "", "Datei": e.datei}
                          for e in bericht.legende], hide_index=True, width="stretch")
elif datei.exists():
    text = datei.read_text(encoding="utf-8")
    st.download_button("Bericht herunterladen (Markdown)", text.encode("utf-8"), datei.name, "text/markdown",
                       icon=":material/download:")
    st.caption(f"Gespeichert unter {pfade.relativ(datei)}")
    kleiner = "\n".join("###" + z if z.startswith("#") else z for z in text.splitlines()[1:])
    with st.container(border=True):
        st.markdown(kleiner)
else:
    st.caption("Für diesen Datensatz gibt es noch keinen Bericht.")
