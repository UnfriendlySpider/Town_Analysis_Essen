"""Datenkatalog: alle Datensätze mit Lizenz, Stand und einem Knopf zum Laden."""

import streamlit as st

from essen import analysen, laden
from essen.app.gemeinsam import abzeichen, download_knopf, katalog, kopf, seitenhilfe
from essen.katalog import EBENEN, THEMEN, anbieter, quellenangabe
from essen.text import datum, groesse, zahl

kopf("Daten laden")
seitenhilfe("daten_laden")

k = katalog()
filter_spalten = st.columns([2, 2, 1.2, 1.2, 1.2], vertical_alignment="bottom")
suche = filter_spalten[0].text_input("Suche", value=st.query_params.get("suche", ""),
                                     placeholder="z. B. Klimaanalyse, Lärm, Wetter")
themen = filter_spalten[1].multiselect("Themen", list(THEMEN), format_func=THEMEN.get, placeholder="alle Themen")
ebene = filter_spalten[2].selectbox("Ebene", [None, *EBENEN], format_func=lambda e: "alle" if e is None else EBENEN[e])
nur_ladbar = filter_spalten[3].toggle("nur ladbare", help="nur Datensätze mit automatischem Download")
nur_geladen = filter_spalten[4].toggle("nur geladene")

liste = k.filter(themen=themen or None, ebene=ebene, nur_ladbar=nur_ladbar, suche=suche or None)
if nur_geladen:
    liste = [ds for ds in liste if laden.vorhanden(ds)]
st.caption(f"{zahl(len(liste))} von {zahl(len(k.datensaetze))} Datensätzen")

for thema, titel in THEMEN.items():
    gruppe = [ds for ds in liste if ds.themen[0] == thema]
    if not gruppe:
        continue
    st.subheader(titel)
    for ds in gruppe:
        with st.container(border=True):
            links, rechts = st.columns([3, 1.3])
            with links:
                st.markdown(f"**{ds.titel}**")
                st.caption(f"{anbieter(k, ds)} · {ds.format} · {ds.raumbezug}")
                abzeichen(k, ds)
                nutzer = analysen.nutzer(ds.id)
                if nutzer:
                    st.caption("Genutzt von: " + ", ".join(a.thema_titel or a.titel for a in nutzer))
                with st.container(horizontal=True, gap="small"):
                    st.page_link("seiten/daten_erklaert.py", label="Was ist das?", icon=":material/dataset:",
                                 query_params={"datensatz": ds.id})
                    if laden.vorhanden(ds):
                        st.page_link("seiten/originaldaten.py", label="Originaldaten ansehen",
                                     icon=":material/table_view:", query_params={"datensatz": ds.id})
                with st.expander("Details"):
                    st.write(ds.beschreibung)
                    st.markdown(f"Stand: {ds.stand or '–'}  \nSeite: [{ds.seite}]({ds.seite})  \nKennung: `{ds.id}`")
                    if ds.download.hinweis:
                        st.markdown(f"**Von Hand:** {ds.download.hinweis}")
                    for hinweis in ds.hinweise:
                        st.markdown(f"- {hinweis}")
                    for dienst in ds.dienste:
                        st.markdown(f"Kartendienst ({dienst.art.upper()}): `{dienst.url}`")
                    if ds.geprueft:
                        st.caption(f"Geprüft: {ds.geprueft}")
                    abruf = laden.lese_abruf(ds)
                    if abruf:
                        st.caption(f"Abruf: {datum(abruf.datum)} · {abruf.url} · {groesse(abruf.bytes)}"
                                   + (f" · Stand der Quelle {datum(abruf.stand_quelle)}" if abruf.stand_quelle else ""))
                    st.text_area("Quellenangabe", quellenangabe(k, ds, abruf.datum if abruf else None),
                                 key=f"qa-{ds.id}", height=80)
            with rechts:
                download_knopf(k, ds, zusatz="katalog")
