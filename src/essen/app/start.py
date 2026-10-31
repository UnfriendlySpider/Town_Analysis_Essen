"""Einstieg der lokalen App. Start mit `uv run essen app` (nicht direkt mit streamlit run).

Jede Seite liegt in seiten/ und nutzt Bausteine aus gemeinsam.py.
"""

import os
from pathlib import Path

import pyogrio
import streamlit as st

from essen.app.gemeinsam import seitenleiste

# Streamlit führt die Seiten in einem Nebenthread aus. Dort fängt pyogrio GDAL-Warnungen nicht ab, und GDAL
# schreibt sie direkt auf die Konsole (etwa „too many members in array“ bei den Stadtteilgrenzen, deren Punkte
# vier statt drei Werte haben). Fehler kommen weiterhin als Ausnahme an; nur diese Konsolenausgabe entfällt.
pyogrio.set_gdal_config_options({"CPL_LOG": os.devnull})

HIER = Path(__file__).parent
st.set_page_config(page_title="Daten für Essen", page_icon=str(HIER / "logo_symbol.svg"), layout="wide")
st.logo(str(HIER / "logo.svg"), size="large", icon_image=str(HIER / "logo_symbol.svg"))

seiten = {
    "Essen entdecken": [
        st.Page("seiten/uebersicht.py", title="Start", icon=":material/home:", default=True),
        st.Page("seiten/stadtteil.py", title="Mein Stadtteil", icon=":material/location_city:"),
        st.Page("seiten/themen.py", title="Themen", icon=":material/category:"),
        st.Page("seiten/karte.py", title="Karte", icon=":material/map:"),
        st.Page("seiten/vergleich.py", title="Themen vergleichen", icon=":material/scatter_plot:"),
        st.Page("seiten/zeitreihen.py", title="Entwicklung über die Jahre", icon=":material/show_chart:"),
        st.Page("seiten/begriffe.py", title="Begriffe erklärt", icon=":material/menu_book:"),
        st.Page("seiten/daten_erklaert.py", title="Daten erklärt", icon=":material/dataset:"),
    ],
    "Werkstatt (für Fortgeschrittene)": [
        st.Page("seiten/vorbereiten.py", title="Alles vorbereiten", icon=":material/rocket_launch:"),
        st.Page("seiten/datenkatalog.py", title="Daten laden", icon=":material/database:"),
        st.Page("seiten/originaldaten.py", title="Originaldaten ansehen", icon=":material/table_view:"),
        st.Page("seiten/analysen.py", title="Neu berechnen", icon=":material/calculate:"),
        st.Page("seiten/inspektion.py", title="Daten untersuchen", icon=":material/search:"),
        st.Page("seiten/schnellanalyse.py", title="Schnellanalyse", icon=":material/bolt:"),
        st.Page("seiten/quellen.py", title="Quellen und Portale", icon=":material/hub:"),
        st.Page("seiten/hintergrund.py", title="Methodik und Lizenzen", icon=":material/description:"),
    ],
}
seite = st.navigation(seiten, expanded=True)
seitenleiste()
seite.run()
