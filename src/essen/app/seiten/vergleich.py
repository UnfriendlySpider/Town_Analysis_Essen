"""Themen vergleichen: Hängen zwei Themen über die Stadtteile zusammen? Streudiagramm, Satz, Übersicht."""

import streamlit as st

from essen import analysen, diagramme, einordnung, steckbrief
from essen.app.gemeinsam import dunkel, kopf, noch_nicht_vorbereitet, seitenhilfe

kopf("Themen vergleichen")
seitenhilfe("vergleich")

kennzahlen = {k.analyse_id: k for k in steckbrief.verfuegbare() if k.analyse_id != "mehrfachbelastung"}
if len(kennzahlen) < 2:
    noch_nicht_vorbereitet("Für einen Vergleich")
    st.stop()

ids = list(kennzahlen)
titel = {i: analysen.hole(i).thema_titel for i in ids}
# direkt verlinkbar: ?a=gruenanteil&b=hitze-nacht
start_a = next(i for i in (st.query_params.get("a"), "gruenanteil", ids[0]) if i in ids)
start_b = next(i for i in (st.query_params.get("b"), "hitze-nacht", ids[1]) if i in ids)
links, rechts = st.columns(2)
a = links.selectbox("Erstes Thema (waagerecht)", ids, format_func=titel.get, index=ids.index(start_a), key="vergleich-a")
b = rechts.selectbox("Zweites Thema (senkrecht)", ids, format_func=titel.get, index=ids.index(start_b), key="vergleich-b")
st.query_params["a"], st.query_params["b"] = a, b
if a == b:
    st.info("Bitte zwei verschiedene Themen wählen.")
    st.stop()

paar, r = steckbrief.vergleich(a, b)
st.markdown(f"**{einordnung.korrelation_in_worten(r)}**")
st.caption(f"Gezählt wird bei „{titel[a]}“: {kennzahlen[a].kennzahl_titel}. Bei „{titel[b]}“: {kennzahlen[b].kennzahl_titel}.")

markiert = st.query_params.get("stadtteil")
x_titel, y_titel = f"{titel[a]} ({kennzahlen[a].einheit})", f"{titel[b]} ({kennzahlen[b].einheit})"
felder = ("beides hoch", f"{titel[b]} hoch, {titel[a]} niedrig", "beides niedrig",
          f"{titel[a]} hoch, {titel[b]} niedrig")
st.altair_chart(diagramme.streu_quadranten(paar, a, b, x_titel, y_titel, felder, markiert,
                                             dunkel=dunkel()), width="stretch")
markiert_da = str(markiert) in set(paar["gebiet_id"].astype(str))
st.caption("Jeder Punkt ist ein Stadtteil; die auffälligsten sind beschriftet. Die gestrichelten Linien zeigen das "
           "Mittel der Stadtteile und teilen das Bild in vier Felder. Die durchgezogene schräge Linie zeigt die "
           "Richtung des Zusammenhangs." + (" Ihr Stadtteil ist als großer, beschrifteter Punkt hervorgehoben."
                                           if markiert_da else ""))

with st.expander("Alle Themen auf einen Blick", icon=":material/grid_on:"):
    st.markdown("Jedes Feld zeigt, wie eng zwei Themen zusammenhängen. **Blau**: Sie steigen gemeinsam. **Orange**: "
                "Das eine steigt, wenn das andere fällt. **Kräftige Farbe**: enger Zusammenhang; **blass**: kaum einer. "
                "Die Zahl ist das r: 1 heißt gleichlaufend, 0 kein Zusammenhang, −1 gegenläufig.")
    matrix = steckbrief.korrelationen()
    matrix = matrix.loc[[i for i in matrix.index if i in titel], [c for c in matrix.columns if c in titel]]
    st.altair_chart(diagramme.korrelation_heatmap(matrix.rename(index=titel, columns=titel), dunkel=dunkel()))
    st.caption("Ein Zusammenhang ist kein Beweis, dass das eine das andere verursacht.")

with st.expander("Werte je Stadtteil", icon=":material/table:"):
    st.dataframe(paar.drop(columns="gebiet_id").rename(columns={"stadtteil": "Stadtteil", a: x_titel, b: y_titel}),
                 hide_index=True, width="stretch",
                 column_config={x_titel: st.column_config.NumberColumn(format="localized"),
                                y_titel: st.column_config.NumberColumn(format="localized")})
