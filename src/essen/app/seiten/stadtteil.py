"""Mein Stadtteil: alle Themen für einen Stadtteil, in Worten eingeordnet und auf der Karte gezeigt."""

import streamlit as st

from essen import analysen, bezirke, diagramme, einordnung, karte, steckbrief, zeitreihen
from essen.app.gemeinsam import (
    dunkel,
    katalog,
    klickkarte,
    kopf,
    neu_gewaehlt,
    noch_nicht_vorbereitet,
    seitenhilfe,
    stadtteile,
    thema_marke,
)
from essen.geo import DatenFehlen
from essen.text import zahl

# Farbe des Punkts wie das Abzeichen der Einordnung (Streamlit-Farbnamen → Farbwerte, im dunklen Thema die
# helleren Farben aus .streamlit/config.toml)
PUNKTFARBE = {"red": "#c4302b", "orange": "#df7d03", "gray": "#46524c", "blue": "#2f73a6", "green": "#3b8432"}
PUNKTFARBE_DUNKEL = {"red": "#f0876a", "orange": "#e9a23e", "gray": "#9aa59f", "blue": "#7aaed6", "green": "#8cc274"}

DUNKEL_MODUS = dunkel()

kopf("Mein Stadtteil")
seitenhilfe("stadtteil")


breit = steckbrief.tabelle()
if breit.empty:
    noch_nicht_vorbereitet("Für den Stadtteil-Vergleich")
    st.stop()

namen = dict(zip(breit["gebiet_id"].astype(str), breit["stadtteil"], strict=True))
liste = sorted(namen, key=namen.get)
vorwahl = st.query_params.get("stadtteil")
gebiet_id = st.selectbox("Stadtteil", liste, format_func=namen.get, index=liste.index(vorwahl) if vorwahl in namen else 0,
                         help="Tippen Sie die ersten Buchstaben, um zu suchen.")
st.query_params["stadtteil"] = gebiet_id
name = namen[gebiet_id]
zeilen = steckbrief.stadtteil(gebiet_id, katalog())

links, rechts = st.columns([3, 2], gap="medium")
with rechts:
    try:
        flaechen = stadtteile()
        gewaehlt = flaechen[flaechen["gebiet_id"].astype(str) == gebiet_id]
        m = karte.neue_karte(tuple(flaechen.to_crs("EPSG:4326").total_bounds))
        karte.umrisse(m, flaechen, "Stadtteile", beschriftung="name")
        if not gewaehlt.empty:
            karte.hervorheben(m, gewaehlt, name)
        geklickt = klickkarte(m, 380, "stadtteil-karte")
        if neu_gewaehlt(geklickt, "stadtteil-karte") and geklickt != gebiet_id and geklickt in namen:
            st.query_params["stadtteil"] = geklickt
            st.rerun()
        st.caption(f"{name} ist rot und mit kräftigem Rand hervorgehoben. Zeigen oder tippen Sie auf einen "
                   "Stadtteil, um seinen Namen zu sehen; ein Klick wählt ihn aus.")
    except DatenFehlen:
        st.caption("Für die Karte fehlen die Stadtteilgrenzen.")
        st.page_link("seiten/vorbereiten.py", label="Zu „Alles vorbereiten“", icon=":material/rocket_launch:")

with links:
    st.markdown(f"### {name} im Vergleich mit den anderen Stadtteilen")
    groesse = steckbrief.flaeche_ha(gebiet_id)
    if groesse:
        alltag = einordnung.flaeche_alltag(groesse)
        st.markdown(f"{name} ist {zahl(groesse)} Hektar groß" + (f" – {alltag}." if alltag else "."))
    bezirk = zeilen["bezirk"].dropna().iloc[0] if "bezirk" in zeilen and zeilen["bezirk"].notna().any() else None
    bezirk_name = bezirke.name(int(bezirk)) if bezirk is not None else ""
    if bezirk_name:
        st.markdown(f":material/location_city: {name} gehört zum **{bezirk_name}**.")
    st.caption(f"In jeder Punktreihe ist jeder graue Punkt ein Stadtteil. Der große Punkt ist {name}, der senkrechte "
               "Strich das Mittel der Stadtteile" + (f", der gestrichelte Strich der Wert des {bezirk_name}"
                                                    if bezirk_name else "") + ". Weiter rechts heißt: höherer Wert.")
    for z in zeilen.itertuples():
        analyse = analysen.hole(z.analyse_id)
        e = einordnung.einordnen(analyse, name, None if z.wert != z.wert else z.wert, z.rang, z.von,
                                 z.mittel_stadtteile, z.rang_mitte)
        with st.container(border=True):
            st.markdown(f"{thema_marke(analyse)} **{analyse.thema_titel}**"
                        + (f" &nbsp; :{e.farbe}-badge[{e.text}]" if e else ""))
            if e:
                st.markdown(e.satz)
                werte = breit[["gebiet_id", "stadtteil", z.analyse_id]].rename(columns={z.analyse_id: "wert"})
                st.altair_chart(diagramme.punktleiste(werte, gebiet_id, analyse.einheit,
                                                      analyse.stellen, z.mittel_stadtteile,
                                                      (PUNKTFARBE_DUNKEL if DUNKEL_MODUS else PUNKTFARBE).get(
                                                          e.farbe, diagramme.DUNKEL), dunkel=DUNKEL_MODUS,
                                                      bezirk=z.wert_bezirk, bezirk_name=bezirk_name),
                                width="stretch")
                if z.wert_bezirk == z.wert_bezirk:
                    st.caption(f"Im {bezirk_name}: {zahl(z.wert_bezirk, analyse.stellen)} {analyse.einheit} "
                               "(gewichtet wie der Wert für ganz Essen).")
                if analyse.zusammensetzung:
                    zeile = steckbrief.zeile(z.analyse_id, gebiet_id)
                    if zeile is not None:
                        st.altair_chart(diagramme.anteile_gestapelt(
                            zeile.to_frame().T, analyse.zusammensetzung, markiert=gebiet_id, dunkel=DUNKEL_MODUS,
                            hoehe_je_zeile=28), width="stretch")
                        st.html(karte.legende_html_eintraege(diagramme.legende_zusammensetzung(
                            analyse.zusammensetzung)))
                menschen = steckbrief.einwohner_belastet(z.analyse_id, gebiet_id)
                if menschen:
                    st.markdown(einordnung.einwohner_satz(menschen["belastet"], menschen["einwohner"],
                                                          im_stadtteil=True), help=einordnung.EINWOHNER_HILFE)
                if z.analyse_id == "mehrfachbelastung":
                    with st.container(horizontal=True, gap="small"):
                        for titel, oben in steckbrief.mehrfach_themen(gebiet_id):
                            st.badge(titel, icon=":material/check_circle:" if oben else ":material/radio_button_unchecked:",
                                     color="red" if oben else "gray",
                                     help="Im obersten Fünftel: etwa die 10 Stadtteile mit den höchsten Werten" if oben
                                     else "Nicht im obersten Fünftel")
            else:
                st.markdown("Für diesen Stadtteil gibt es keinen Wert (zu wenig Fläche).")
            st.caption(analyse.kurz)
            with st.container(horizontal=True, gap="small"):
                st.page_link("seiten/themen.py", label="Mehr zum Thema", icon=":material/arrow_forward:",
                             query_params={"thema": z.analyse_id})
                if z.analyse_id in zeitreihen.JE_STADTTEIL:
                    st.page_link("seiten/zeitreihen.py", label="Verlauf über die Jahre", icon=":material/show_chart:",
                                 query_params={"thema": z.analyse_id, "stadtteil": gebiet_id})

with st.expander("Alle Zahlen als Tabelle", icon=":material/table:"):
    tabelle = zeilen.assign(thema=[analysen.hole(a).thema_titel for a in zeilen["analyse_id"]])
    st.dataframe(
        tabelle[["thema", "kennzahl", "wert", "einheit", "mittel_stadtteile", "rang", "von", "erstellt"]].round(
            {"wert": 1, "mittel_stadtteile": 1}),
        hide_index=True, width="stretch",
        column_config={
            "thema": st.column_config.TextColumn("Thema", width="medium"),
            "kennzahl": st.column_config.TextColumn("Was gezählt wird", width="large"),
            "wert": st.column_config.NumberColumn("Wert", format="localized"),
            "einheit": st.column_config.TextColumn("Einheit", width="small"),
            "mittel_stadtteile": st.column_config.NumberColumn("Mittel der Stadtteile", format="localized"),
            "rang": st.column_config.NumberColumn("Rang", help="1 = höchster Wert aller Stadtteile"),
            "von": st.column_config.NumberColumn("von"),
            "erstellt": st.column_config.DateColumn("berechnet am", format="DD.MM.YYYY"),
        },
    )
    st.caption("Alle Werte beziehen sich auf Fläche, nicht auf Einwohner. Rang 1 ist der höchste Wert.")
