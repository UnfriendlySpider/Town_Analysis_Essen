"""Originaldaten ansehen: Dateien eines geladenen Datensatzes als Karte, Tabelle, Bild oder JSON (nur Ausschnitte)."""

import contextlib

import streamlit as st

from essen import analysen, diagramme, karte, laden, legenden, pfade, vorschau
from essen.app.gemeinsam import (
    abzeichen,
    belegt,
    datensatz_wahl,
    geladene_datensaetze,
    kartenhoehe,
    katalog,
    kopf,
    seitenhilfe,
    stadtteile,
)
from essen.geo import ESSEN_BBOX_WGS84, DatenFehlen
from essen.katalog import anbieter
from essen.text import datum, groesse, mehrzahl, zahl

kopf("Originaldaten ansehen")
seitenhilfe("originaldaten")
k = katalog()


@st.cache_data(show_spinner=False, max_entries=8)
def _layer(pfad: str, stempel: float):
    return vorschau.layer(pfad)


@st.cache_data(show_spinner="Lese einen Ausschnitt …", max_entries=8)
def _vektor(pfad: str, layer: str | None, stempel: float):
    return vorschau.vektor_probe(pfad, layer)


@st.cache_data(show_spinner="Lese das Rasterbild … große Dateien brauchen einige Sekunden", max_entries=6)
def _raster(pfad: str, datensatz: str, stempel: float):
    return vorschau.raster_vorschau(pfad, legende=legenden.aus_pfad(laden.ordner(datensatz)))


@st.cache_data(show_spinner=False, max_entries=8)
def _tabelle(pfad: str, stempel: float):
    return vorschau.tabelle_probe(pfad)


def _fehlwert(wert) -> str:
    return "keiner" if wert is None else zahl(wert, 0 if float(wert).is_integer() else 2)


@st.cache_data(show_spinner=False, max_entries=8)
def _dateiliste(kennung: str, ordner: str, abrufzeit: str, geaendert: float):
    """Gemerkt, bis neu geladen, entpackt oder aufgeräumt wird (Abrufzeit, Änderungszeit des Ordners)."""
    return vorschau.dateiliste(kennung)


@st.cache_data(show_spinner=False, max_entries=8)
def _json(pfad: str, stempel: float):
    return vorschau.json_vorschau(pfad)


def _umrisse(m) -> None:
    if laden.vorhanden("stadtteile"):
        with contextlib.suppress(DatenFehlen, ValueError):
            karte.umrisse(m, stadtteile(), "Stadtteile", beschriftung="name")


geladen = geladene_datensaetze(k)
if not geladen:
    st.info("Noch nichts geladen. Unter „Daten laden“ einen Datensatz herunterladen.", icon=":material/info:")
    st.page_link("seiten/datenkatalog.py", label="Zu „Daten laden“", icon=":material/database:")
    st.stop()

wahl = datensatz_wahl(k, geladen, "Datensatz (nur geladene)")
ds = k.datensatz(wahl)
abruf = laden.lese_abruf(ds)

with st.container(border=True):
    st.markdown(f"**{ds.titel}**")
    st.caption(f"{anbieter(k, ds)} · {ds.format} · {ds.raumbezug}")
    abzeichen(k, ds)
    st.write(ds.beschreibung)
    if abruf:
        st.caption(f"Geladen am {datum(abruf.datum)} · {groesse(belegt(ds, abruf))}"
                   + (f" · Stand der Quelle {datum(abruf.stand_quelle)}" if abruf.stand_quelle else "")
                   + (" · mit erfundenen Testdaten" if abruf.testdaten else ""))
    st.page_link("seiten/daten_erklaert.py", label="Was ist das? In Worten erklärt", icon=":material/dataset:",
                 query_params={"datensatz": ds.id})
    nutzer = analysen.nutzer(ds.id)
    if nutzer:
        st.markdown("Genutzt von: " + ", ".join(a.thema_titel or a.titel for a in nutzer))
    else:
        st.markdown("Noch von keiner Analyse genutzt.")
        st.page_link("seiten/schnellanalyse.py", label="Schnell auf die Stadtteile verteilen", icon=":material/bolt:",
                     query_params={"datensatz": ds.id})

dateien = _dateiliste(ds.id, str(pfade.daten()), abruf.zeit if abruf else "",
                      laden.ordner(ds).stat().st_mtime)
with st.expander(f"Alle Dateien ({zahl(len(dateien))})", icon=":material/folder_open:"):
    tabelle = vorschau.tabelle_dateien(dateien)
    tabelle["bytes"] = tabelle["bytes"].map(groesse)
    st.dataframe(tabelle, hide_index=True, width="stretch",
                 column_config={"datei": st.column_config.TextColumn("Datei", width="large"),
                                "art": "Art", "bytes": "Größe",
                                "im_archiv": st.column_config.CheckboxColumn("im ZIP", help="nicht entpackt, direkt "
                                                                             "aus dem Archiv gelesen")})
    st.caption("Begleitdateien (zum Beispiel .shx, .prj, .dbf eines Shapefiles) gehören zu einer Hauptdatei und "
               "werden mit ihr gelesen.")

ansehbar = [d for d in dateien if d.art in vorschau.ANSEHBAR]
if not ansehbar:
    st.info("In diesem Datensatz gibt es keine Datei, die hier angezeigt werden kann (zum Beispiel nur PDFs).",
            icon=":material/info:")
    st.stop()
datei = st.selectbox("Datei", ansehbar, key=f"datei-{ds.id}",
                     format_func=lambda d: f"{d.name} · {vorschau.ARTEN[d.art]} · {groesse(d.bytes)}")
stempel = vorschau.stempel(datei.pfad)

try:
    if datei.art == "vektor":
        ebenen = _layer(datei.pfad, stempel)
        name = None
        if len(ebenen) > 1:
            name = st.selectbox("Ebene", [e[0] for e in ebenen], key=f"ebene-{ds.id}-{datei.name}",
                                format_func=lambda e: f"{e} ({dict(ebenen)[e] or 'ohne Geometrie'})")
        elif ebenen:
            name = ebenen[0][0]
        probe = _vektor(datei.pfad, name, stempel)
        spalten = st.columns(4)
        spalten[0].metric("Objekte in der Datei", "–" if probe.gesamt is None else zahl(probe.gesamt))
        spalten[1].metric("hier gezeigt", zahl(len(probe.daten)))
        spalten[2].metric("Geometrie", probe.geometrie or "keine")
        spalten[3].metric("Koordinatensystem", probe.crs or "unbekannt")
        if probe.begrenzt or probe.nur_essen:
            st.caption(("Nur Objekte im Rechteck um Essen. " if probe.nur_essen else "")
                       + (f"Gezeigt werden die ersten {zahl(vorschau.MAX_OBJEKTE)}; die Datei enthält mehr."
                          if probe.begrenzt else ""))
        reiter = st.tabs(["Karte", "Tabelle", "Felder"] if probe.geometrie else ["Tabelle", "Felder"])
        if probe.geometrie:
            with reiter[0]:
                if len(probe.daten):
                    m = karte.neue_karte(ESSEN_BBOX_WGS84)
                    _umrisse(m)
                    karte.objekte(m, probe.daten, name or datei.name)
                    st.iframe(karte.als_html(m), height=kartenhoehe(560))
                    st.caption("Zeigen oder tippen Sie auf ein Objekt, um seine ersten Felder zu sehen.")
                else:
                    st.info("Im Rechteck um Essen liegen keine Objekte dieser Ebene.")
        with reiter[-2]:
            st.dataframe(probe.daten.drop(columns="geometry", errors="ignore"), width="stretch", height=480)
        with reiter[-1]:
            st.dataframe(probe.felder, hide_index=True, width="stretch")
            st.caption("Die Bedeutung der Felder steht meist in der Beschreibung des Anbieters. Nicht raten: "
                       "Unklares unter „Daten untersuchen“ prüfen.")

    elif datei.art == "raster":
        bild = _raster(datei.pfad, ds.id, stempel)
        info = bild.info
        st.markdown(f"{zahl(info['breite'])} × {zahl(info['hoehe'])} Zellen zu {zahl(info['zellgroesse'], 2)} · "
                    f"Werttyp {info['typ']}, {mehrzahl(info['baender'], 'Band', 'Bänder')}"
                    + f" · {info['crs']} · Fehlwert {_fehlwert(info['nodata'])}")
        links, rechts = st.columns([3, 1.2], gap="medium")
        with rechts:
            deckkraft = st.slider("Deckkraft", 0.2, 1.0, 0.8, 0.05, key=f"deck-{ds.id}")
            st.caption(bild.hinweis)
            if bild.legende:
                st.html(karte.legende_html_eintraege(bild.legende))
        with links:
            m = karte.neue_karte(ESSEN_BBOX_WGS84)
            karte.rasterbild(m, bild.bild, bild.grenzen, datei.name, deckkraft)
            _umrisse(m)
            st.iframe(karte.als_html(m), height=kartenhoehe(560))
            if info["faktor"] > 1:
                st.caption(f"Vergröbert: etwa jede {zahl(info['faktor'], 0)}. Zelle in jeder Richtung, nur das "
                           "Rechteck um Essen.")
        st.markdown("**Verteilung der Werte im Rechteck um Essen**")
        if bild.werte.empty:
            st.caption("Nur Fehlwerte im Ausschnitt.")
        else:
            st.altair_chart(diagramme.werte_verteilung(bild.werte, bild.stetig), width="stretch")

    elif datei.art == "tabelle":
        daten, trenner = _tabelle(datei.pfad, stempel)
        st.caption(f"Trennzeichen „{trenner}“, {zahl(len(daten.columns))} Spalten. Gezeigt werden höchstens die ersten "
                   f"{zahl(vorschau.MAX_ZEILEN)} Zeilen.")
        reiter = st.tabs(["Tabelle", "Felder"])
        with reiter[0]:
            st.dataframe(daten, width="stretch", height=480)
        with reiter[1]:
            from essen.inspizieren import feldtabelle

            st.dataframe(feldtabelle(daten), hide_index=True, width="stretch")

    elif datei.art == "json":
        inhalt = _json(datei.pfad, stempel)
        if inhalt.daten is None:
            st.warning(f"Die Datei ist zu groß für die Vorschau (über {groesse(vorschau.MAX_JSON_BYTES)}). "
                       "„Daten untersuchen“ beschreibt ihren Aufbau.")
        else:
            if inhalt.tabelle is not None:
                st.markdown("**Als Tabelle**")
                st.dataframe(inhalt.tabelle, width="stretch", height=360)
            st.markdown("**Aufbau**")
            st.json(inhalt.daten, expanded=2)
except Exception as fehler:  # noqa: BLE001 - kaputte oder ungewöhnliche Dateien: Meldung statt Absturz
    st.error(f"Die Datei lässt sich nicht als Vorschau anzeigen: {fehler}. Wählen Sie eine andere Datei, oder lassen "
             "Sie unter „Daten untersuchen“ einen Bericht erstellen.", icon=":material/error:")

st.page_link("seiten/inspektion.py", label="Ausführlichen Bericht zu diesem Datensatz (Daten untersuchen)",
             icon=":material/search:", query_params={"datensatz": ds.id})
