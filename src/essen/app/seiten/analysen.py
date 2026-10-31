"""Analysen: Daten prüfen und nachladen, Einstellungen wählen, rechnen, Ergebnis ansehen und mitnehmen."""

import streamlit as st

from essen import analysen, bericht, diagramme, karte
from essen.analysen.basis import Ergebnis, veraltet
from essen.analysen.hitze_nacht import ZuordnungFehlt
from essen.app.gemeinsam import (
    daten_zeile,
    jahresbalken,
    kartenhoehe,
    katalog,
    kopf,
    methodik_text,
    seitenhilfe,
)
from essen.geo import DatenFehlen
from essen.text import datum

kopf("Neu berechnen")
seitenhilfe("neu_berechnen")
k = katalog()

# ?thema= wie auf den anderen Seiten; ?analyse= gilt weiter für ältere Links
vorwahl = st.query_params.get("thema") or st.query_params.get("analyse")
ids = list(analysen.ALLE)
analyse_id = st.selectbox("Thema", ids, format_func=lambda i: analysen.ALLE[i].thema_titel,
                          index=ids.index(vorwahl) if vorwahl in ids else 0)
st.query_params.pop("analyse", None)
st.query_params["thema"] = analyse_id
analyse = analysen.hole(analyse_id)
st.markdown(f"**Frage:** {analyse.frage}")

st.subheader("Daten")
for kennung in analyse.benoetigt:
    daten_zeile(k, kennung, pflicht=True)
for kennung in analyse.optional:
    daten_zeile(k, kennung, pflicht=False)

werte = {}


def eingabe(p) -> None:
    schluessel = f"param-{analyse.id}-{p.name}"
    if p.optionen:
        werte[p.name] = st.selectbox(p.titel, p.optionen, index=list(p.optionen).index(p.standard), help=p.hilfe or None,
                                     format_func=p.beschriftung, key=schluessel)
    elif p.typ == "zahl":
        werte[p.name] = st.number_input(p.titel, value=float(p.standard), help=p.hilfe or None, key=schluessel)
    elif p.typ == "ganzzahl":
        werte[p.name] = st.number_input(p.titel, value=int(p.standard), step=1, help=p.hilfe or None, key=schluessel)
    else:
        werte[p.name] = st.text_input(p.titel, value=str(p.standard), help=p.hilfe or None, key=schluessel)


haeufig = [p for p in analyse.parameter if not p.selten]
selten = [p for p in analyse.parameter if p.selten]
if haeufig or selten:
    st.subheader("Einstellungen")
    if not haeufig:
        st.caption("Für dieses Thema gibt es keine wichtigen Einstellungen; die Standardwerte passen.")
    for p in haeufig:
        eingabe(p)
    if selten:
        with st.expander("Weitere Einstellungen (selten nötig)", icon=":material/tune:"):
            for p in selten:
                eingabe(p)

fehlend = analyse.fehlende_daten(werte)
if st.button("Berechnen", type="primary", icon=":material/play_arrow:", disabled=bool(fehlend),
             help=("Erst diese Daten laden (oben unter „Daten“): " + ", ".join(k.datensatz(d).titel for d in fehlend)
                   if fehlend else None)):
    with st.status("Rechne …", expanded=True) as status:
        try:
            analysen.ausfuehren(k, analyse.id, werte, melde=status.write)
            status.update(label="Fertig", state="complete", expanded=False)
        except (DatenFehlen, ZuordnungFehlt, ValueError, FileNotFoundError) as fehler:
            status.update(label="Abgebrochen", state="error", expanded=True)
            st.error(str(fehler), icon=":material/error:")
            if isinstance(fehler, ZuordnungFehlt):
                st.page_link("seiten/inspektion.py", label="Zu „Daten untersuchen“", icon=":material/search:")
        except Exception as fehler:  # noqa: BLE001 - z. B. kaputte Datei; lieber eine Meldung als ein Traceback
            status.update(label="Abgebrochen", state="error", expanded=True)
            st.error(f"Die Berechnung ist an einem unerwarteten Fehler gescheitert: {fehler}. Oft hilft es, die Daten "
                     "neu zu laden (unter „Daten laden“ mit „Neu laden“) und dann noch einmal zu rechnen.",
                     icon=":material/error:")



@st.cache_data(show_spinner=False, max_entries=8)
def _karte_html(analyse_id: str, erstellt: str, testdaten: bool) -> str:
    """Karte eines Ergebnisses als HTML; neu gebaut erst, wenn neu gerechnet wurde, nicht bei jeder Einstellung."""
    thema, gespeichert = analysen.hole(analyse_id), Ergebnis.ansehen(analyse_id)
    m = karte.neue_karte(tuple(gespeichert.geometrie.to_crs("EPSG:4326").total_bounds))
    karte.kennzahl_flaechen(m, gespeichert.geometrie, thema.kennzahl, thema.stufen, thema.spalten,
                            name=thema.kennzahl_titel)
    return karte.als_html(m)


ergebnis = Ergebnis.laden(analyse.id)
if not ergebnis:
    st.info("Noch kein Ergebnis. Daten laden und auf Berechnen klicken.", icon=":material/info:")
    st.stop()

st.subheader("Ergebnis")
st.markdown(f"### {ergebnis.kennzahl_text}")
st.caption(f"Berechnet am {datum(ergebnis.erstellt)}" + (" · mit erfundenen Testdaten" if ergebnis.testdaten else ""))
gruende = veraltet(analyse, ergebnis, werte)
if gruende:
    st.warning("Dieses Ergebnis passt nicht mehr ganz: " + "; ".join(gruende) + ". Zum Aktualisieren auf Berechnen klicken.",
               icon=":material/update:")
for hinweis in ergebnis.hinweise:
    st.markdown(f"- {hinweis}")

tabelle = ergebnis.tabelle
spalten_konfig = {}
balkenfarbe = analyse.stufen.farben[2] if analyse.stufen else diagramme.MARKIERT
for s in analyse.spalten:
    titel = f"{s.titel} (%)" if s.art == "prozent" else s.titel
    if s.art == "prozent" and s.balken:
        spalten_konfig[s.feld] = st.column_config.ProgressColumn(titel, min_value=0, max_value=100, format="localized",
                                                                 color=balkenfarbe, width="medium")
    elif s.art == "text":
        spalten_konfig[s.feld] = st.column_config.TextColumn(titel, width="medium", pinned=True)
    else:
        spalten_konfig[s.feld] = st.column_config.NumberColumn(titel, format="localized", width="small")
if "vollstaendig" in tabelle.columns:
    spalten_konfig["vollstaendig"] = st.column_config.CheckboxColumn("vollständig", width="small",
                                                                     help="Jahr mit Werten an mindestens 95 % der Tage")

if ergebnis.geometrie is not None and analyse.stufen:
    st.iframe(_karte_html(analyse.id, ergebnis.erstellt, ergebnis.testdaten), height=kartenhoehe(540))
    st.html(karte.legende_html(analyse.stufen, analyse.kennzahl_titel, tabelle.get(analyse.kennzahl), analyse.einheit,
                               analyse.stellen))
    sichtbar = [s.feld for s in analyse.spalten if s.feld in tabelle.columns]
    st.dataframe(tabelle.sort_values(analyse.kennzahl, ascending=False, na_position="last")[sichtbar],
                 hide_index=True, width="stretch", height=420, column_config=spalten_konfig)
else:
    if "jahr" in tabelle.columns and analyse.kennzahl in tabelle.columns:
        jahresbalken(tabelle, analyse)
        st.caption("Nur vollständige Jahre. Das laufende Jahr fehlt.")
    sichtbar = [s.feld for s in analyse.spalten if s.feld in tabelle.columns]
    sichtbar += ["vollstaendig"] if "vollstaendig" in tabelle.columns else []
    st.dataframe(tabelle.sort_values(sichtbar[0], ascending=False)[sichtbar], hide_index=True, width="stretch",
                 column_config=spalten_konfig)

st.subheader("Mitnehmen")
knoepfe = st.columns(3)
# Die Dateien entstehen erst beim Klick (aufrufbare `data`), nicht bei jedem Neulauf der Seite.
knoepfe[0].download_button("Tabelle (CSV)", lambda: tabelle.to_csv(index=False).encode("utf-8"), f"{analyse.id}.csv",
                           "text/csv", icon=":material/table:", width="stretch", on_click="ignore")
if ergebnis.geometrie is not None:
    knoepfe[1].download_button("Gebiete (GeoJSON)",
                               lambda: ergebnis.geometrie.to_crs("EPSG:4326").to_json(drop_id=True),
                               f"{analyse.id}.geojson", "application/geo+json", icon=":material/polyline:",
                               width="stretch", on_click="ignore")
    if bericht.hat_seite(analyse, ergebnis):
        knoepfe[2].download_button("Seite mit Karte (HTML)",
                                   lambda: bericht.html_seite(k, analyse, ergebnis).encode("utf-8"),
                                   f"{analyse.id}.html", "text/html", icon=":material/web:", width="stretch",
                                   on_click="ignore",
                                   help="Eigenständige Seite mit Karte und Tabelle. Vor dem Weitergeben die Lizenzen prüfen.")

if (text := methodik_text(analyse)):
    with st.expander("So ist gerechnet"):
        st.markdown(text)
