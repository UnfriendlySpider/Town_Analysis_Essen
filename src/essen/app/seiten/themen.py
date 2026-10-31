"""Themen: ein Thema für ganz Essen lesen – Aussage, Karte, Rangliste, Lesehilfe und Grenzen. Rechnet nichts."""

import pandas as pd
import streamlit as st

from essen import (
    analysen,
    begriffe,
    bezirke,
    diagramme,
    einordnung,
    hilfetexte,
    karte,
    laden,
    zeitkarte,
    zeitreihen,
)
from essen.analysen.basis import Ergebnis
from essen.app.gemeinsam import (
    THEMA_SYMBOL,
    dunkel,
    grenzen_kasten,
    jahresbalken,
    katalog,
    klickkarte,
    kopf,
    lesehilfe,
    methodik_text,
    neu_gewaehlt,
    noch_nicht_vorbereitet,
    seitenhilfe,
    thema_marke,
)
from essen.app.zeitkarte import abschnitt as zeit_abschnitt
from essen.katalog import anbieter
from essen.text import datum, zahl

kopf("Themen")
seitenhilfe("themen")

ids = list(analysen.ALLE)
vorwahl = st.query_params.get("thema")
thema = st.pills("Thema", ids, format_func=lambda i: analysen.hole(i).thema_titel, selection_mode="single",
                 default=vorwahl if vorwahl in ids else ids[0], key="thema-wahl")
if thema is None:
    st.info("Bitte oben ein Thema wählen.", icon=":material/touch_app:")
    st.stop()
st.query_params["thema"] = thema
analyse = analysen.hole(thema)
st.subheader(f"{thema_marke(analyse)} {analyse.kurz}")

ergebnis = Ergebnis.laden(thema)
if ergebnis is None:
    noch_nicht_vorbereitet("Für dieses Thema")
    st.stop()

st.markdown(f"#### {ergebnis.kennzahl_text}")
abweichend = [f"{p.titel}: {p.beschriftung(ergebnis.parameter.get(p.name))}" for p in analyse.parameter
              if not p.selten and str(ergebnis.parameter.get(p.name)) != str(p.standard)]
st.caption(f"Berechnet am {datum(ergebnis.erstellt)}" + (" · mit erfundenen Testdaten" if ergebnis.testdaten else "")
           + (" · mit geänderten Einstellungen: " + "; ".join(abweichend) if abweichend else ""))

tabelle = ergebnis.tabelle
stellen = analyse.stellen
if {"einwohner", "einwohner_belastet"} <= set(tabelle.columns):
    alle, belastet = tabelle["einwohner"].sum(), tabelle["einwohner_belastet"].sum()
    if alle:
        st.markdown(einordnung.einwohner_satz(belastet, alle),
                    help=einordnung.EINWOHNER_HILFE + " Die Karte zeigt weiterhin Anteile der Fläche.")
zeit_moeglich = bool(zeitkarte.verfuegbar(analyse, ergebnis))
vorgabe = "verlauf" if st.query_params.get("ansicht") == "verlauf" else "heute"
verlauf_gewaehlt = zeit_moeglich and (st.session_state.get(f"ansicht-{thema}") or vorgabe) == "verlauf"
links, rechts = st.columns([3, 2], gap="medium")
with rechts:
    lesehilfe(analyse)
    # Im Verlauf hat die Karte eigene Stufen und eine eigene Legende
    if analyse.stufen and ergebnis.geometrie is not None and not verlauf_gewaehlt:
        werte = tabelle[analyse.kennzahl] if analyse.kennzahl in tabelle.columns else None
        st.html(karte.legende_html(analyse.stufen, analyse.kennzahl_titel, werte, analyse.einheit, stellen))
with links:
    ansicht = "heute"
    if zeit_moeglich:
        ansicht = st.segmented_control("Ansicht", ["heute", "verlauf"], default=vorgabe, key=f"ansicht-{thema}",
                                       format_func={"heute": "Heute", "verlauf": "Verlauf über die Jahre"}.get,
                                       label_visibility="collapsed") or "heute"
    elif analyse.raumbezug == "stadtteil":
        stand = zeitkarte.datenstand(katalog(), analyse)
        st.caption(":material/history: Für dieses Thema gibt es nur einen Datenstand"
                   + (f" ({stand})" if stand else "") + ", deshalb keinen Verlauf über die Jahre.")
    if ansicht == "verlauf":
        zeit_abschnitt(analyse, ergebnis, key=f"themen-zk-{thema}", markiert=st.query_params.get("stadtteil"),
                       bei_klick=lambda g: st.query_params.__setitem__("stadtteil", g))
    elif ergebnis.geometrie is not None and analyse.stufen:
        m = karte.neue_karte(tuple(ergebnis.geometrie.to_crs("EPSG:4326").total_bounds))
        karte.kennzahl_flaechen(m, ergebnis.geometrie, analyse.kennzahl, analyse.stufen, analyse.spalten,
                                name=analyse.kennzahl_titel)
        geklickt = klickkarte(m, 520, f"themen-karte-{thema}")
        if neu_gewaehlt(geklickt, f"themen-karte-{thema}"):
            st.query_params["stadtteil"] = geklickt
        auswahl_zeile = tabelle[tabelle["gebiet_id"].astype(str) == st.query_params.get("stadtteil", "")] \
            if "gebiet_id" in tabelle.columns else tabelle.iloc[0:0]
        if len(auswahl_zeile):
            z = auswahl_zeile.iloc[0]
            with st.container(border=True, horizontal=True, vertical_alignment="center"):
                wert = z[analyse.kennzahl]
                st.markdown(f"**{z['stadtteil']}**: {zahl(wert, stellen)} {analyse.einheit}" if pd.notna(wert)
                            else f"**{z['stadtteil']}**: kein Wert")
                st.page_link("seiten/stadtteil.py", label="Alle Themen für diesen Stadtteil",
                             icon=":material/arrow_forward:", query_params={"stadtteil": str(z["gebiet_id"])})
                if thema in zeitreihen.JE_STADTTEIL:
                    st.page_link("seiten/zeitreihen.py", label="Verlauf über die Jahre", icon=":material/show_chart:",
                                 query_params={"thema": thema, "stadtteil": str(z["gebiet_id"])})
        else:
            st.caption("Klicken Sie auf einen Stadtteil, um ihn auszuwählen.")
    elif "jahr" in tabelle.columns and analyse.kennzahl in tabelle.columns:
        jahresbalken(tabelle, analyse, hoehe=380)
        st.page_link("seiten/zeitreihen.py", label="Verlauf mit Trend und Grenzwerten ansehen",
                     icon=":material/show_chart:", query_params={"thema": thema})

if "stadtteil" in tabelle.columns and analyse.kennzahl in tabelle.columns and "gebiet_id" in tabelle.columns:
    st.markdown("#### Alle Stadtteile im Vergleich")
    st.caption("Sortiert vom höchsten zum niedrigsten Wert, in den Farben der Karte. Die gestrichelte Linie ist das "
               "Mittel der Stadtteile. **Ein Klick auf einen Balken** zeigt alle Themen für diesen Stadtteil.")
    balken = diagramme.balken_sortiert(tabelle, analyse.kennzahl, analyse.stufen, analyse.kennzahl_titel,
                                       analyse.einheit, stellen, markiert=st.query_params.get("stadtteil"),
                                       dunkel=dunkel())
    auswahl = st.altair_chart(balken, width="stretch", on_select="rerun", key=f"balken-{thema}")
    gewaehlt = (auswahl.get("selection", {}).get("stadtteil") or [{}])[0].get("gebiet_id") if auswahl else None
    if gewaehlt:
        st.switch_page("seiten/stadtteil.py", query_params={"stadtteil": str(gewaehlt)})

    if analyse.zusammensetzung:
        with st.expander("Wie sich die Fläche aufteilt", icon=":material/stacked_bar_chart:"):
            st.caption("Ein Balken je Stadtteil, zusammen 100 % der Bezugsfläche. Sortiert nach dem ersten Teil.")
            st.altair_chart(diagramme.anteile_gestapelt(tabelle, analyse.zusammensetzung,
                                                        markiert=st.query_params.get("stadtteil"), dunkel=dunkel()),
                            width="stretch")
            st.html(karte.legende_html_eintraege(diagramme.legende_zusammensetzung(analyse.zusammensetzung)))

    je_bezirk = bezirke.je_bezirk(katalog(), thema, ergebnis)
    if not je_bezirk.empty:
        with st.expander("Nach Stadtbezirken", icon=":material/location_city:"):
            st.caption("Die neun Stadtbezirke fassen mehrere Stadtteile zusammen. Gerechnet wird wie für ganz Essen: "
                       "gewichtet mit der Bezugsgröße, nicht als einfaches Mittel der Stadtteile (E-018).")
            st.dataframe(je_bezirk[["name", "wert", "stadtteile"]].sort_values("wert", ascending=False),
                         hide_index=True, width="stretch",
                         column_config={"name": st.column_config.TextColumn("Stadtbezirk"),
                                        "wert": st.column_config.NumberColumn(
                                            f"{analyse.kennzahl_titel} ({analyse.einheit})", format="localized"),
                                        "stadtteile": st.column_config.NumberColumn("Stadtteile mit Wert")})

grenzen_kasten(analyse, ergebnis.hinweise)

verwandt = [analysen.hole(a) for a in analyse.verwandt if a in analysen.ALLE]
if verwandt:
    with st.container(border=True):
        st.markdown(":material/link: **Dazu passend**")
        for a in verwandt:
            st.page_link("seiten/themen.py", label=f"{a.thema_titel}: {a.kurz}",
                         icon=THEMA_SYMBOL.get(a.id, ":material/insights:"), query_params={"thema": a.id})

namen = hilfetexte.THEMA_BEGRIFFE.get(thema, ())
if namen:
    with st.expander("Begriffe zu diesem Thema", icon=":material/menu_book:"):
        for name in namen:
            st.markdown(f"**{name}:** {begriffe.erklaere(name)}")

with st.expander("Wie wurde gerechnet? (ausführlich)", icon=":material/calculate:"):
    text = methodik_text(analyse)
    if text:
        st.markdown(text)
    st.page_link("seiten/analysen.py", label="Mit anderen Einstellungen berechnen (Werkstatt)",
                 icon=":material/calculate:", query_params={"thema": thema})

with st.expander("Woher kommen die Zahlen?", icon=":material/source:"):
    st.markdown("Diese Daten der Behörden stecken in diesem Thema. „Was ist das?“ erklärt jeden Datensatz in Worten; "
                "in der Werkstatt sehen Sie ihn so, wie er geliefert wurde – als Karte, Tabelle oder Bild.")
    k = katalog()
    for kennung in (*analyse.benoetigt, *analyse.optional):
        if kennung not in k.datensaetze:
            continue
        ds = k.datensatz(kennung)
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.markdown(f"**{ds.titel}** ({anbieter(k, ds)})"
                        + ("" if laden.vorhanden(ds) else " · noch nicht geladen"))
            st.page_link("seiten/daten_erklaert.py", label="Was ist das?", icon=":material/dataset:",
                         query_params={"datensatz": kennung})
            if laden.vorhanden(ds):
                st.page_link("seiten/originaldaten.py", label="Ansehen", icon=":material/table_view:",
                             query_params={"datensatz": kennung})

with st.expander("Alle Werte als Tabelle", icon=":material/table:"):
    sichtbar = [s.feld for s in analyse.spalten if s.feld in tabelle.columns]
    titel = {s.feld: (f"{s.titel} (%)" if s.art == "prozent" else s.titel) for s in analyse.spalten}
    st.dataframe(tabelle[sichtbar].rename(columns=titel), hide_index=True, width="stretch",
                 column_config={titel[s.feld]: st.column_config.NumberColumn(format="localized")
                                for s in analyse.spalten if s.feld in sichtbar and s.art != "text"})
    st.download_button("Tabelle herunterladen (CSV)", tabelle.to_csv(index=False).encode("utf-8"), f"{thema}.csv",
                       "text/csv", icon=":material/download:")
