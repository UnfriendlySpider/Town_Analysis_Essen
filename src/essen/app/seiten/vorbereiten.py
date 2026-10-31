"""Alles vorbereiten: alle Daten laden und alle Themen berechnen, mit einem Knopf."""

import streamlit as st

from essen import analysen, vorbereiten
from essen.app.gemeinsam import fortschritt, katalog, kopf, seitenhilfe
from essen.text import zahl

kopf("Alles vorbereiten")
seitenhilfe("vorbereiten")
k = katalog()
plan = vorbereiten.plan(k)

if plan.fertig:
    st.success("Alles ist vorbereitet: Alle Daten sind geladen und alle Themen berechnet.", icon=":material/check_circle:")
    st.page_link("seiten/uebersicht.py", label="Zur Startseite", icon=":material/home:")
    st.caption("Ob es bei den Behörden neuere Daten gibt, zeigt in der Kommandozeile `uv run essen aktualisieren`.")
    st.stop()

with st.container(border=True):
    st.markdown("**Das passiert beim Vorbereiten**")
    if plan.fehlend:
        titel = [k.datensatz(d).titel for d in plan.fehlend]
        st.markdown(f"1. **{zahl(len(plan.fehlend))} Datensätze herunterladen**, zusammen etwa "
                    f"**{zahl(plan.download_mb / 1000, 1)} GB**"
                    + (" (bei einigen ist die Größe unbekannt)" if plan.groesse_unbekannt else "")
                    + ". Je nach Internetverbindung dauert das einige Minuten bis über eine Stunde.")
        with st.expander("Welche Datensätze?"):
            st.markdown("\n".join(f"- {t}" for t in titel))
        st.caption(f"Frei auf diesem Rechner: {zahl(plan.frei_gb, 0)} GB. Entpackt brauchen die Daten ein Mehrfaches "
                   "des Downloads (mit allen Themen etwa 15 bis 25 GB).")
    else:
        st.markdown("1. Alle nötigen Daten sind schon geladen.")
    namen = [analysen.hole(a).thema_titel for a in plan.zu_rechnen]
    st.markdown(f"2. **{len(namen)} Themen berechnen:** {', '.join(namen)}. Das dauert einige Minuten.")
    if plan.von_hand:
        st.warning("Diese Daten lassen sich nicht automatisch laden und müssen auf der Seite „Daten laden“ von Hand "
                   "übernommen werden: " + ", ".join(k.datensatz(d).titel for d in plan.von_hand))

if not plan.genug_platz:
    st.error("Auf diesem Rechner ist vermutlich zu wenig Platz frei. Bitte erst Platz schaffen.", icon=":material/error:")
bestaetigt = True
if plan.download_mb > 500:
    bestaetigt = st.checkbox(f"Ja, etwa {zahl(plan.download_mb / 1000, 1)} GB herunterladen")

if st.button("Alles vorbereiten", type="primary", icon=":material/rocket_launch:",
             disabled=not bestaetigt or not plan.genug_platz,
             help=None if plan.genug_platz else "Erst Platz schaffen, dann geht es weiter."):
    with st.status("Bereite vor …", expanded=True) as status:
        balken = st.empty()
        schritte = vorbereiten.ausfuehren(k, melde=status.write, fortschritt=fortschritt(balken))
        balken.empty()
        fehler = [s for s in schritte if not s.ok]
        status.update(label="Fertig" if not fehler else f"Fertig, {len(fehler)} Schritte mit Problemen",
                      state="complete" if not fehler else "error", expanded=bool(fehler))
    for s in fehler:
        st.error(s.text, icon=":material/error:")
    if not fehler:
        st.success("Alles vorbereitet.", icon=":material/check_circle:")
        st.page_link("seiten/uebersicht.py", label="Zur Startseite", icon=":material/home:")
