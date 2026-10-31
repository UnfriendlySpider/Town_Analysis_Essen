"""Quellen und Portale: alle Anbieter mit Zugang, Lizenz und Hinweisen, dazu bekannte Lücken."""

import pandas as pd
import streamlit as st

from essen.app.gemeinsam import katalog, kopf, seitenhilfe
from essen.katalog import EBENEN, KONTO, THEMEN, quellen_filtern, quellen_tabelle

kopf("Quellen und Portale")
seitenhilfe("quellen")

k = katalog()
links, rechts = st.columns(2)
ebenen = links.multiselect("Ebene", list(EBENEN), format_func=EBENEN.get, placeholder="alle Ebenen")
themen = rechts.multiselect("Themen", list(THEMEN), format_func=THEMEN.get, placeholder="alle Themen")

liste = quellen_filtern(k, ebenen, themen)
tabelle = pd.DataFrame(quellen_tabelle(k, liste))
st.dataframe(
    tabelle, hide_index=True, width="stretch",
    column_config={
        "Quelle": st.column_config.TextColumn("Quelle", width="medium", pinned=True),
        "Themen": st.column_config.TextColumn("Themen", width="medium"),
        "Zugang": st.column_config.TextColumn("Zugang", width="medium"),
        "Link": st.column_config.LinkColumn("Link", display_text="öffnen"),
        "Eignung": st.column_config.NumberColumn("Eignung", help="1 eingeschränkt, 2 mittel, 3 hoch", format="%d"),
        "Datensätze": st.column_config.NumberColumn("im Katalog", help="Datensätze dieser Quelle im Katalog"),
    },
)

st.subheader("Einzelheiten")
for q in liste:
    with st.expander(f"{q.name}" + (f" · {q.kurz}" if q.kurz else "")):
        st.write(q.beschreibung)
        st.markdown(f"**Lizenz:** {k.lizenzen[q.lizenz].kurz}" + (f" ({q.lizenz_hinweis})" if q.lizenz_hinweis else ""))
        st.markdown(f"**Zugang:** {', '.join(q.zugang) or '–'} · {q.konto_hinweis or KONTO.get(q.konto, q.konto)} · "
                    f"Aktualität: {q.aktualitaet or '–'}")
        if q.endpunkte:
            st.markdown("**Schnittstellen:**\n" + "\n".join(f"- {e.titel}: `{e.url}`" for e in q.endpunkte))
        if q.links:
            st.markdown("**Links:** " + " · ".join(f"[{link.titel}]({link.url})" for link in q.links))
        if q.beispiele:
            st.markdown("**Beispiele:**\n" + "\n".join(f"- {b}" for b in q.beispiele))
        if q.hinweise:
            st.markdown("**Hinweise:**\n" + "\n".join(f"- {h}" for h in q.hinweise))
        if q.kontakt:
            st.caption("Kontakt: " + ", ".join(q.kontakt))

if k.luecken:
    st.subheader("Lücken und offene Fragen")
    st.dataframe(pd.DataFrame([{"Art": lu.art, "Thema": lu.titel, "Stand": lu.text, "Weg": lu.weg} for lu in k.luecken]),
                 hide_index=True, width="stretch")
