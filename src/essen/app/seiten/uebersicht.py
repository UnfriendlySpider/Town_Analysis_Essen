"""Start: Was möchten Sie wissen? Fragen als Einstieg, darunter die wichtigsten Ergebnisse für Essen."""

import streamlit as st

from essen import analysen, diagramme, steckbrief, vorbereiten
from essen.analysen.basis import Ergebnis
from essen.app.gemeinsam import (
    geladene_datensaetze,
    katalog,
    kennzahl_kachel,
    kopf,
    noch_nicht_vorbereitet,
    seitenhilfe,
)
from essen.text import datum, zahl

k = katalog()
KERN = ["hitze-nacht", "gruenanteil", "laerm", "starkregen", "hitzetage-raster", "luft-station"]
vorhanden = [(a, e) for a in KERN if (e := Ergebnis.ansehen(a)) is not None]
berechnet = [e for a in analysen.ALLE if (e := Ergebnis.ansehen(a)) is not None]

# -------------------------------------------------------------------- Kopfbereich

text, bild = st.columns([1.7, 1], gap="large", vertical_alignment="center")
with text:
    kopf("Daten für Essen")
    seitenhilfe("start")
    with st.container(horizontal=True, gap="small"):
        st.badge(f"{zahl(len(berechnet))} Themen berechnet", icon=":material/check_circle:",
                 color="green" if berechnet else "gray")
        anzahl_stadtteile = len(steckbrief.tabelle())
        if anzahl_stadtteile:
            st.badge(f"{zahl(anzahl_stadtteile)} Stadtteile", icon=":material/location_city:", color="blue")
        if berechnet:
            st.badge(f"Stand {datum(max(e.erstellt for e in berechnet))}", icon=":material/schedule:", color="gray")
    with st.container(horizontal=True, gap="small"):
        st.page_link("seiten/stadtteil.py", label="Mein Stadtteil ansehen", icon=":material/location_city:")
        st.page_link("seiten/karte.py", label="Zur Karte", icon=":material/map:")
with bild:
    gruen = Ergebnis.laden("gruenanteil")
    if gruen is not None and gruen.geometrie is not None:
        a = analysen.hole("gruenanteil")
        st.altair_chart(diagramme.mini_karte(gruen.geometrie, a.kennzahl, a.stufen, a.einheit, 0, hoehe=300,
                                             breite=360), width="content")
        st.caption(f"Essen und seine {zahl(len(gruen.geometrie))} Stadtteile, eingefärbt nach ihrem Grünanteil.")
    else:
        with st.container(border=True):
            st.caption(":material/map: Hier erscheint eine kleine Karte von Essen, sobald das Thema Grün berechnet "
                       "ist.")

if not vorbereiten.ist_vorbereitet():
    noch_nicht_vorbereitet("Für einen Teil der Themen")

# -------------------------------------------------------------------- Fragen

st.subheader("Was möchten Sie wissen?")
FRAGEN = [
    ("Wie steht mein Stadtteil da?", "Hitze, Grün, Lärm und mehr für einen Stadtteil, verglichen mit ganz Essen.",
     "seiten/stadtteil.py", None, ":green[:material/location_city:]"),
    ("Wo ist es nachts am heißesten?", "Welche Stadtteile in Sommernächten kaum abkühlen.",
     "seiten/themen.py", {"thema": "hitze-nacht"}, ":orange[:material/bedtime:]"),
    ("Wo ist es grün, wo laut?", "Karten zu Grün, versiegeltem Boden, Lärm und Starkregen.",
     "seiten/themen.py", {"thema": "gruenanteil"}, ":green[:material/park:]"),
    ("Welche Stadtteile trifft es mehrfach?", "Wo Hitze, Lärm und Starkregen zusammenkommen.",
     "seiten/themen.py", {"thema": "mehrfachbelastung"}, ":orange[:material/stacks:]"),
    ("Wird es in meinem Stadtteil heißer?", "Heiße Tage je Stadtteil und Luftmesswerte über die Jahre.",
     "seiten/zeitreihen.py", {"thema": "hitzetage-raster"}, ":orange[:material/show_chart:]"),
    ("Hängt das eine mit dem anderen zusammen?", "Zum Beispiel: Sind Stadtteile mit wenig Grün nachts wärmer?",
     "seiten/vergleich.py", None, ":blue[:material/scatter_plot:]"),
]
for reihe in [FRAGEN[i:i + 3] for i in range(0, len(FRAGEN), 3)]:
    spalten = st.columns(3)
    for spalte, (frage, beschreibung, seite, parameter, symbol) in zip(spalten, reihe, strict=False):
        with spalte.container(border=True, height="stretch"):
            st.markdown(f"#### {symbol} {frage}")
            st.markdown(beschreibung)
            st.page_link(seite, label="Ansehen", icon=":material/arrow_forward:", query_params=parameter)

# -------------------------------------------------------------------- Kennzahlen

if vorhanden:  # sonst steht der Hinweis auf „Alles vorbereiten“ schon oben
    st.subheader("Essen in Zahlen")
for reihe in [vorhanden[i:i + 3] for i in range(0, len(vorhanden), 3)]:
    spalten = st.columns(3)
    for spalte, (kennung, ergebnis) in zip(spalten, reihe, strict=False):
        with spalte:
            kennzahl_kachel(analysen.hole(kennung), ergebnis)
if vorhanden:
    st.caption("Die kleinen Karten zeigen die Stadtteile: je dunkler, desto höher der Wert. Zeigen oder tippen Sie "
               "auf einen Stadtteil, um Namen und Wert zu sehen.")
    st.caption(f"Berechnet am {datum(max(e.erstellt for _, e in vorhanden))}. Die Zahlen beruhen auf Daten und "
               "Modellrechnungen von Land, Stadt und Bund; was sie jeweils nicht sagen, steht beim Thema.")

with st.expander("Über diese App"):
    geladen = geladene_datensaetze(k)
    st.markdown(f"""
Die App wertet öffentlich zugängliche Daten über Essen aus: von der Stadt Essen, dem Land NRW (zum Beispiel der
Klimaanalyse NRW 2026), dem Deutschen Wetterdienst, dem Umweltbundesamt und der Volkszählung 2022. Sie kennt
{zahl(len(k.datensaetze))} Datensätze aus {zahl(len(k.quellen))} Quellen, davon sind {zahl(len(geladen))} geladen.

Die App läuft nur auf diesem Rechner. Es werden keine Daten weitergegeben. Wer Ergebnisse teilen möchte, findet die
nötigen Quellenangaben in der Werkstatt unter „Methodik und Lizenzen“.
""")
