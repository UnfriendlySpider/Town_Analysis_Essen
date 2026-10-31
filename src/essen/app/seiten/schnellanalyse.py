"""Schnellanalyse: einen beliebigen geladenen Vektordatensatz auf die Stadtteile verteilen."""

import streamlit as st

from essen import karte, laden, pfade
from essen.analysen import schnell
from essen.analysen.basis import Ergebnis
from essen.app.gemeinsam import datensatz_wahl, kartenhoehe, katalog, kopf, seitenhilfe
from essen.geo import DatenFehlen, hat_vektordaten
from essen.text import datum

kopf("Schnellanalyse")
seitenhilfe("schnellanalyse")
k = katalog()

if not laden.vorhanden("stadtteile"):
    st.warning("Dafür werden die Stadtteilgrenzen gebraucht. Laden Sie sie unter „Daten laden“ "
               "(Eintrag „Stadtteilgrenzen Essen“) oder mit „Alles vorbereiten“.", icon=":material/warning:")
    st.page_link("seiten/datenkatalog.py", label="Zu „Daten laden“", icon=":material/database:",
                 query_params={"suche": "Stadtteilgrenzen"})
    st.stop()

kandidaten = [ds for ds in k.datensaetze.values() if ds.id != "stadtteile" and hat_vektordaten(ds.id)]
if not kandidaten:
    st.info("Noch kein Datensatz mit Flächen, Linien oder Punkten geladen (GeoPackage, GeoJSON, Shape …). "
            "Laden Sie zuerst einen unter „Daten laden“.", icon=":material/info:")
    st.page_link("seiten/datenkatalog.py", label="Zu „Daten laden“", icon=":material/database:")
    st.stop()

wahl = datensatz_wahl(k, kandidaten)


@st.cache_data(show_spinner="Lese die Layer …", max_entries=16)
def _layer_liste(kennung: str, ordner: str, abrufzeit: str) -> list[tuple[str, str]]:
    return schnell.layer_liste(kennung)


try:
    abruf = laden.lese_abruf(wahl)
    layer_liste = _layer_liste(wahl, str(pfade.daten()), abruf.zeit if abruf else "")
except Exception as fehler:  # noqa: BLE001 - kaputte oder unbekannte Datei: verständlich melden statt abstürzen
    st.error(f"Die Daten lassen sich nicht als Vektordaten lesen: {fehler}. Unter „Daten untersuchen“ sehen Sie, "
             "was in der Datei steckt.", icon=":material/error:")
    st.page_link("seiten/inspektion.py", label="Zu „Daten untersuchen“", icon=":material/search:",
                 query_params={"datensatz": wahl})
    st.stop()
if not layer_liste:
    st.warning("Die Datei enthält keine Ebene mit Flächen, Linien oder Punkten. Bitte einen anderen Datensatz "
               "wählen.", icon=":material/warning:")
    st.stop()
layer = st.selectbox("Layer", layer_liste, format_func=lambda eintrag: f"{eintrag[0]} ({eintrag[1]})")

if st.button("Verteilen", type="primary", icon=":material/bolt:"):
    with st.status("Verteile auf die Stadtteile …", expanded=True) as status:
        try:
            st.session_state["schnell"] = schnell.verteile(k, wahl, layer[0], melde=status.write)
            st.session_state["schnell"].speichern()
            status.update(label="Fertig", state="complete", expanded=False)
        except (ValueError, DatenFehlen) as fehler:
            status.update(label="Abgebrochen", state="error")
            st.error(str(fehler), icon=":material/error:")
        except Exception as fehler:  # noqa: BLE001 - kaputte Datei: Meldung statt Traceback
            status.update(label="Abgebrochen", state="error")
            st.error(f"Die Schnellanalyse ist fehlgeschlagen: {fehler}", icon=":material/error:")

ergebnis = st.session_state.get("schnell")
if not (ergebnis and ergebnis.parameter.get("datensatz") == wahl):
    ergebnis = Ergebnis.laden(f"schnell-{wahl}")  # früher gespeichertes Ergebnis, auch nach dem Neuladen der Seite
    if ergebnis is not None:
        st.caption(f"Zuletzt verteilt am {datum(ergebnis.erstellt)}. „Verteilen“ rechnet neu.")
if ergebnis and ergebnis.parameter.get("datensatz") == wahl and ergebnis.geometrie is not None:
    kennzahl = ergebnis.parameter["kennzahl"]
    stufen, spalten = schnell.stufen_fuer(ergebnis), schnell.spalten_fuer(ergebnis)
    titel = schnell.KENNZAHL_TITEL[kennzahl]
    st.markdown(f"### {ergebnis.kennzahl_text}")
    for hinweis in ergebnis.hinweise:
        st.markdown(f"- {hinweis}")
    links, rechts = st.columns([3, 2])
    with links:
        m = karte.neue_karte(tuple(ergebnis.geometrie.to_crs("EPSG:4326").total_bounds))
        karte.kennzahl_flaechen(m, ergebnis.geometrie, kennzahl, stufen, spalten, name=titel)
        st.iframe(karte.als_html(m), height=kartenhoehe(520))
        st.html(karte.legende_html(stufen, f"{titel} (Stufen nach Quintilen)"))
    with rechts:
        tabelle = ergebnis.tabelle.drop(columns=["gebiet_id"]).dropna(axis=1, how="all")
        tabelle = tabelle.sort_values(kennzahl, ascending=False)
        titel_spalten = schnell.SPALTEN_TITEL
        konfig = {s: (st.column_config.TextColumn(titel_spalten.get(s, s), pinned=True) if s == "stadtteil" else
                      st.column_config.NumberColumn(titel_spalten.get(s, s), format="localized"))
                  for s in tabelle.columns}
        st.dataframe(tabelle, hide_index=True, width="stretch", height=560, column_config=konfig)
