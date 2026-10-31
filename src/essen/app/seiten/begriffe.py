"""Begriffe erklärt: das Glossar der App mit Suche."""

import streamlit as st

from essen import begriffe
from essen.app.gemeinsam import kopf, seitenhilfe

kopf("Begriffe erklärt")
seitenhilfe("begriffe")

suche = st.text_input("Suche", placeholder="z. B. Hitze, Lärm, Grenzwert", key="begriffe-suche")
treffer = begriffe.suche(suche)
if not treffer:
    st.info("Kein Begriff gefunden. Versuchen Sie ein anderes Wort.", icon=":material/search_off:")
for name, text in treffer.items():
    with st.container(border=True):
        st.markdown(f"**{name}**  \n{text}")
