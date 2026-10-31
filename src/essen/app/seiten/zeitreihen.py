"""Entwicklung über die Jahre: heiße Tage je Stadtteil, an der Station Bredeney und Luftqualität, mit Trend."""

import streamlit as st

from essen import analysen, diagramme, einordnung, zeitkarte, zeitreihen
from essen.analysen.basis import Ergebnis
from essen.analysen.hitzetage_raster import ESSEN_ID
from essen.app.gemeinsam import (
    THEMA_SYMBOL,
    dunkel,
    grenzen_kasten,
    katalog,
    kopf,
    lesehilfe,
    noch_nicht_vorbereitet,
    seitenhilfe,
)
from essen.app.zeitkarte import abschnitt as zeit_abschnitt
from essen.text import zahl

kopf("Entwicklung über die Jahre")
seitenhilfe("zeitreihen")

THEMEN = {"hitzetage-raster": "Heiße Tage in Ihrem Stadtteil",
          "hitzetage-station": "Messstation Bredeney" + (f" (seit {j})" if (j := zeitreihen.erstes_jahr("hitzetage-station"))
                                                          else ""),
          "luft-station": "Luftqualität an den Messstationen"}
vorhanden = [a for a in THEMEN if Ergebnis.ansehen(a) is not None]
if not vorhanden:
    noch_nicht_vorbereitet("Für die Entwicklung über die Jahre")
    st.stop()

mit_karte = [a for a in analysen.ALLE.values() if a.zeitachse and a.id not in THEMEN
             and zeitkarte.verfuegbar(a, Ergebnis.ansehen(a.id))]
if mit_karte:
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.caption("Als Karte über die Jahre auch:")
        for a in mit_karte:
            st.page_link("seiten/themen.py", label=a.thema_titel, icon=THEMA_SYMBOL.get(a.id),
                         query_params={"thema": a.id, "ansicht": "verlauf"})

vorwahl_thema = st.query_params.get("thema")
analyse_id = st.segmented_control("Was möchten Sie sehen?", vorhanden, format_func=THEMEN.get,
                                  default=vorwahl_thema if vorwahl_thema in vorhanden else vorhanden[0],
                                  key="zeitreihe-thema") or vorhanden[0]
st.query_params["thema"] = analyse_id
analyse = analysen.hole(analyse_id)
ergebnis = Ergebnis.laden(analyse_id)


@st.cache_data(ttl=3600, show_spinner="Berechne …", max_entries=6)
def luft(schadstoff: str, _stempel: str) -> Ergebnis:
    """Luftqualität für einen anderen Schadstoff rechnen, ohne das gespeicherte Ergebnis zu ersetzen (unter 1 s)."""
    return analysen.ausfuehren(katalog(), "luft-station", {"schadstoff": schadstoff}, melde=lambda m: None,
                               speichern=False)


# -------------------------------------------------------------------- Auswahl der Reihen

if analyse_id in zeitreihen.JE_STADTTEIL:
    gebiete = zeitreihen.stadtteile(analyse_id, ergebnis)
    stadtteile = [g for g in gebiete if gebiete[g] != "Essen gesamt"]
    essen_id = ESSEN_ID if ESSEN_ID in gebiete else None
    kennwerte = {k: v for k, v in zeitreihen.REIHEN[analyse_id].items() if k in ergebnis.jahreswerte.columns}
    if not stadtteile or not kennwerte:
        st.info("Für dieses Thema sind keine Jahreswerte je Stadtteil gespeichert. Bitte unter „Neu berechnen“ "
                "noch einmal rechnen.", icon=":material/info:")
        st.page_link("seiten/analysen.py", label="Zu „Neu berechnen“", icon=":material/calculate:",
                     query_params={"thema": analyse_id})
        st.stop()
    erster_kennwert = "heisse_tage" if "heisse_tage" in kennwerte else next(iter(kennwerte))
    vorwahl = st.query_params.get("stadtteil")
    spalte_a, spalte_b = st.columns([1.2, 2], gap="medium")
    with spalte_a:
        gebiet = st.selectbox("Ihr Stadtteil", stadtteile, format_func=gebiete.get,
                              index=stadtteile.index(vorwahl) if vorwahl in stadtteile else 0, key="zeitreihe-gebiet")
        st.query_params["stadtteil"] = gebiet
    with spalte_b:
        kennwert = st.segmented_control("Welche Zahl?", list(kennwerte), format_func=kennwerte.get,
                                        default=erster_kennwert, key="zeitreihe-kennwert") or erster_kennwert
    with st.expander("Vergleichen mit …", icon=":material/compare_arrows:"):
        vergleich = st.multiselect("Weitere Stadtteile oder ganz Essen", [g for g in gebiete if g != gebiet],
                                   default=[essen_id] if essen_id else [], format_func=gebiete.get,
                                   key="zeitreihe-vergleich")
        ohne_station = Ergebnis.ansehen("hitzetage-station") is None
        station = st.toggle("Messstation Bredeney dazu (gemessen, nicht gerechnet)", key="zeitreihe-station",
                            disabled=ohne_station,
                            help="Die Messreihe der Station ist noch nicht berechnet. Sie entsteht unter "
                                 "„Alles vorbereiten“ oder „Neu berechnen“." if ohne_station else None)
    reihe = zeitreihen.stadtteil_reihe(kennwert, [gebiet, *vergleich], station=station, ergebnis=ergebnis)
else:
    if analyse_id == "luft-station":
        p = next(p for p in analyse.parameter if p.name == "schadstoff")
        schadstoff = st.segmented_control("Schadstoff", p.optionen, format_func=p.beschriftung,
                                          default=ergebnis.parameter.get("schadstoff", p.standard),
                                          key="zeitreihe-stoff", help=p.hilfe) or p.standard
        if schadstoff != ergebnis.parameter.get("schadstoff"):
            ergebnis = luft(schadstoff, ergebnis.erstellt)
    moeglich = zeitreihen.moegliche_reihen(analyse_id, ergebnis)
    standard = [k for k in moeglich if not k.startswith("wert_")][:2]
    with st.expander("Weitere Reihen wählen (z. B. einzelne Messstationen)", icon=":material/tune:"):
        auswahl = st.multiselect("Reihen", list(moeglich), default=standard, format_func=moeglich.get,
                                 key=f"reihen-{analyse_id}")
    if not auswahl:
        st.info("Bitte mindestens eine Reihe wählen.")
        st.stop()
    reihe = zeitreihen.zeitreihe(analyse_id, auswahl, ergebnis)

jahre = reihe.daten["jahr"].dropna()
if jahre.empty:
    st.info("Für diese Auswahl gibt es keine Werte. Bitte andere Reihen wählen.", icon=":material/info:")
    st.stop()
erstes, letztes = int(jahre.min()), int(jahre.max())
if erstes < letztes:
    von, bis = st.slider("Zeitraum", erstes, letztes, (erstes, letztes), key=f"zeitraum-{analyse_id}")
else:
    von, bis = erstes, letztes
    st.caption(f"Werte gibt es nur für {erstes}.")
daten = reihe.daten[(reihe.daten["jahr"] >= von) & (reihe.daten["jahr"] <= bis)]

# -------------------------------------------------------------------- Diagramm

links, rechts = st.columns([3, 1.3], gap="medium")
with links:
    stellen = zeitreihen.stellen(analyse_id, reihe.einheit)
    st.altair_chart(diagramme.zeitverlauf(daten, reihe.einheit, zeitreihen.trendlinien(daten), reihe.vergleich,
                                          reihe.marken, stellen=stellen, dunkel=dunkel()), width="stretch")
    st.caption("Gestrichelte Linien in der Farbe einer Reihe zeigen ihren Trend."
               + (" Helle Punkte: unvollständige Jahre (zum Beispiel das laufende); sie zählen nicht zum Trend."
                  if not reihe.daten["vollstaendig"].all() else "")
               + (" Die gepunktete senkrechte Linie markiert eine Änderung an der Station." if reihe.marken else ""))
with rechts:
    lesehilfe(analyse, zeitreihen.LESEHILFE.get(analyse_id))
    if analyse_id in zeitreihen.JE_STADTTEIL:
        grenzen_kasten(analyse)

# -------------------------------------------------------------------- Auf der Karte

if analyse_id in zeitreihen.JE_STADTTEIL:
    st.subheader("Auf der Karte")

    def _waehle(gebiet_id: str) -> None:
        if gebiet_id in stadtteile:
            st.session_state["zeitreihe-gebiet"] = gebiet_id
            st.query_params["stadtteil"] = gebiet_id

    zeit_abschnitt(analyse, ergebnis, key="zeitreihe-zk", markiert=gebiet, feld=kennwert, bei_klick=_waehle)

# -------------------------------------------------------------------- Früher und heute, Trend

if analyse_id in zeitreihen.JE_STADTTEIL or analyse_id == "hitzetage-station":
    vergleich_tabelle, letzte = zeitreihen.frueher_heute(reihe.daten)
    if not vergleich_tabelle.empty:
        st.subheader("Früher und heute")
        spalten = st.columns(min(3, len(vergleich_tabelle)))
        for nummer, z in enumerate(vergleich_tabelle.itertuples()):
            with spalten[nummer % len(spalten)].container(border=True):
                einheit = " °C" if reihe.einheit == "°C" or z.reihe.startswith("Jahresmittel") else ""
                st.metric(z.reihe, f"{zahl(z.mittel_heute, 1)}{einheit}",
                          f"{'+' if z.differenz > 0 else ''}{zahl(z.differenz, 1)} gegenüber 1961–1990",
                          delta_color="inverse", help=f"Mittel {letzte - 9}–{letzte}; 1961–1990 im Schnitt "
                                                      f"{zahl(z.mittel_frueher, 1)}{einheit}")
                if analyse_id in zeitreihen.JE_STADTTEIL:
                    st.caption(einordnung.frueher_heute_satz(z.reihe, zeitreihen.ART[kennwert], z.mittel_frueher,
                                                             z.mittel_heute,
                                                             *zeitreihen.BEZUG, letzte))
        zeitraum_hinweis = " Dieser Vergleich nutzt immer die ganze Reihe, unabhängig vom gewählten Zeitraum."
        if analyse_id == "hitzetage-station":
            st.caption("1961–1990 ist der übliche Vergleichszeitraum des Wetterdienstes. Die Station wurde 1965 "
                       "verlegt (rund 2 km nach Osten und gut 30 m höher); frühe und späte Jahre sind nur bedingt "
                       "vergleichbar." + zeitraum_hinweis)
        else:
            st.caption("1961–1990 ist der übliche Vergleichszeitraum des Wetterdienstes. Modellwerte aus dem "
                       "1-km-Raster des Wetterdienstes; sie zeigen den großräumigen Verlauf, nicht die Hitze in "
                       "einzelnen Straßen." + zeitraum_hinweis)

st.subheader("Trend")
t = zeitreihen.trend(daten)
if t.empty:
    st.caption("Zu wenige vollständige Jahre für einen Trend (mindestens 5).")
else:
    for z in t.itertuples():
        richtung = einordnung.richtung_wort(z.je_10_jahre)
        st.markdown(f"- **{z.reihe}:** im Schnitt {zahl(abs(z.je_10_jahre), zeitreihen.stellen(analyse_id, reihe.einheit))} "
                    f"{reihe.einheit} {richtung} je 10 Jahre ({z.von} bis {z.bis}, {z.jahre} vollständige Jahre)")
    st.caption("Der Trend ist eine Gerade durch alle vollständigen Jahre im gewählten Zeitraum. Er beschreibt den "
               "Verlauf im Schnitt, er erklärt ihn nicht. Bei Messstationen ändern sich auch Lage und Zahl der "
               "Messpunkte.")
