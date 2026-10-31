"""Bausteine, die mehrere Seiten der App teilen: Katalog, Hinweise, Lizenz-Abzeichen, Download-Knopf.

Regel für die App: Seiten zeigen nur an und rufen Funktionen aus dem Paket auf.
Gerechnet, geladen und gespeichert wird in essen.laden, essen.analysen usw.
"""

from __future__ import annotations

import streamlit as st

from essen import begriffe, einordnung, hilfetexte, katalog as kat, laden, pfade, vorbereiten
from essen.katalog import STATUS, THEMEN, Datensatz, Katalog
from essen.text import datum, groesse, megabyte

LIZENZ_FARBE = {
    "dl-de-zero-2.0": "green", "cc0-1.0": "green",
    "dl-de-by-2.0": "blue", "cc-by-4.0": "blue",
    "cc-by-sa-4.0": "violet", "odbl-1.0": "violet",
    "cc-by-nc-4.0": "orange",
}
STATUS_FARBE = {"geprueft": "green", "ungeprueft": "yellow", "manuell": "gray", "dienst": "blue"}
STATUS_KURZ = {"geprueft": "Download geprüft", "ungeprueft": "Download ungeprüft", "manuell": "von Hand",
               "dienst": "nur Kartendienst"}


@st.cache_resource(show_spinner=False)
def _katalog_gecacht(stempel: float) -> Katalog:
    return kat.lade()


def katalog() -> Katalog:
    """Der Katalog, neu gelesen, sobald sich eine YAML-Datei ändert."""
    stempel = max((p.stat().st_mtime for p in pfade.katalog().glob("*.yaml")), default=0.0)
    return _katalog_gecacht(stempel)


@st.cache_data(show_spinner=False, max_entries=200)
def _belegt_gecacht(kennung: str, ordner: str, abrufzeit: str) -> int:
    return laden.belegter_platz(kennung)


def belegt(ds: Datensatz, abruf: laden.Abruf) -> int:
    """Belegter Platz eines geladenen Datensatzes. Gemerkt bis zum nächsten Abruf, weil das Zählen großer
    entpackter Ordner Sekunden dauern kann."""
    return _belegt_gecacht(ds.id, str(pfade.daten()), abruf.zeit)


def mobil() -> bool:
    """True auf Handys (laut Browserkennung). Streamlit kennt die Bildschirmbreite nicht; die Kennung reicht, um
    Karten niedriger zu machen, damit man auf kleinen Bildschirmen noch an ihnen vorbei scrollen kann."""
    kennung = (st.context.headers or {}).get("User-Agent", "")
    return "Mobi" in kennung or "Android" in kennung


def kartenhoehe(standard: int) -> int:
    """Höhe für Karten und eingebettete Seiten: auf Handys höchstens 380 Pixel."""
    return min(standard, 380) if mobil() else standard


def dunkel() -> bool:
    """True, wenn die App im dunklen Thema läuft (Menü oben rechts → Einstellungen → Darstellung)."""
    return getattr(st.context.theme, "type", None) == "dark"


@st.cache_resource(show_spinner=False, max_entries=2)
def _stadtteile_gecacht(stempel: tuple):
    from essen.geo import lade_stadtteile

    return lade_stadtteile(katalog()).gdf


def stadtteile():
    """Stadtteilgrenzen (GeoDataFrame in EPSG:25832), einmal gelesen und neu, sobald sie neu geladen wurden.

    Nicht verändern: alle Seiten teilen sich dasselbe Objekt. Fehlen sie, kommt DatenFehlen."""
    abruf = laden.lese_abruf("stadtteile")
    return _stadtteile_gecacht((str(pfade.daten()), abruf.zeit if abruf else ""))


@st.cache_resource(show_spinner=False, max_entries=64)
def _mini_karte_gecacht(analyse_id: str, erstellt: str, ordner: str):
    from essen import analysen, diagramme
    from essen.analysen.basis import Ergebnis

    analyse, ergebnis = analysen.hole(analyse_id), Ergebnis.laden(analyse_id)
    return diagramme.mini_karte(ergebnis.geometrie, analyse.kennzahl, analyse.stufen, analyse.einheit, analyse.stellen)


@st.cache_data(show_spinner=False, max_entries=32)
def zeitkarte_daten(analyse_id: str, feld: str, jahrzehnte: bool, erstellt: str, ordner: str) -> dict:
    """Daten für die Karte über die Jahre (essen.zeitkarte.daten), je Ergebnisstand einmal vorbereitet."""
    from essen import analysen, zeitkarte
    from essen.analysen.basis import Ergebnis

    analyse = analysen.hole(analyse_id)
    zeitwert = next(z for z in analyse.zeitachse if z.feld == feld)
    return zeitkarte.daten(Ergebnis.laden(analyse_id), zeitwert, jahrzehnte)


def kopf(titel: str, text: str | None = None) -> None:
    st.title(titel)
    if text:
        st.caption(text)
    testdaten_hinweis()


def testdaten_hinweis() -> None:
    if pfade.ist_testdaten():
        st.warning("Testdaten aktiv: Alle Gebiete und Werte sind erfunden. Für echte Daten die App ohne "
                   "`--testdaten` starten.", icon=":material/science:")


def seitenleiste() -> None:
    with st.sidebar:
        if not vorbereiten.ist_vorbereitet():
            st.info("Noch nicht alle Themen sind berechnet. Einmal **Alles vorbereiten** lädt die Daten und rechnet "
                    "alles aus.", icon=":material/rocket_launch:")
            st.page_link("seiten/vorbereiten.py", label="Alles vorbereiten", icon=":material/rocket_launch:")
        st.caption("Die **Werkstatt** ist für Fortgeschrittene: Daten einzeln laden, mit anderen Einstellungen "
                   "rechnen, Daten untersuchen.")
        st.caption("Die App läuft nur auf diesem Rechner. Daten kommen direkt von den Behörden und Portalen.")


# -------------------------------------------------------------------- Karten

def klickkarte(m, hoehe: int, schluessel: str) -> str | None:
    """Zeigt eine folium-Karte und gibt die gebiet_id des zuletzt angeklickten Gebiets zurück (sonst None).

    Verschieben und Zoomen lösen keinen Neulauf aus, nur ein Klick auf eine Fläche."""
    from streamlit_folium import st_folium

    antwort = st_folium(m, height=kartenhoehe(hoehe), use_container_width=True, key=schluessel,
                        returned_objects=["last_active_drawing"])
    zeichnung = (antwort or {}).get("last_active_drawing") or {}
    gebiet = (zeichnung.get("properties") or {}).get("gebiet_id")
    return str(gebiet) if gebiet not in (None, "") else None


def neu_gewaehlt(gebiet_id: str | None, schluessel: str) -> bool:
    """True genau dann, wenn auf der Karte gerade ein anderes Gebiet angeklickt wurde als beim letzten Lauf.

    st_folium meldet den letzten Klick bei jedem Neulauf wieder; ohne diese Prüfung würde eine Auswahl über
    das Auswahlfeld sofort vom alten Klick überschrieben."""
    alt = st.session_state.get(f"klick-{schluessel}")
    st.session_state[f"klick-{schluessel}"] = gebiet_id
    return gebiet_id is not None and gebiet_id != alt


# -------------------------------------------------------------------- Hilfe und Erklärungen

def seitenhilfe(seite: str, offen: bool = False) -> None:
    """Kasten „So funktioniert diese Seite“ mit Zweck, Schritten und erklärten Begriffen (Texte: essen.hilfetexte)."""
    hilfe = hilfetexte.HILFE[seite]
    st.markdown(hilfe.wozu)
    with st.expander("So funktioniert diese Seite", icon=":material/help:", expanded=offen):
        st.markdown("\n".join(f"{nummer}. {schritt}" for nummer, schritt in enumerate(hilfe.schritte, 1)))
        for begriff in hilfe.begriffe:
            st.markdown(f"**{begriff}:** {begriffe.erklaere(begriff)}")
        st.caption("Alle Fachwörter erklärt die Seite „Begriffe erklärt“.")


def lesehilfe(analyse, text: str | None = None) -> None:
    """Kasten „So lesen Sie das“: Richtung (gut oder schlecht), Lesehilfe der Analyse oder ein eigener Text."""
    with st.container(border=True):
        st.markdown(f"**:material/visibility: So lesen Sie das**  \n{text or analyse.lesehilfe}")
        farbe = {"hoch_schlecht": "orange", "hoch_gut": "green"}.get(analyse.richtung, "gray")
        st.markdown(f":{farbe}[**{einordnung.richtung_text(analyse)}**]")


# Darstellung je Thema: Symbol und Farbe (Farbe passend zu den Kartenstufen in essen.farben)
THEMA_SYMBOL = {
    "hitze-nacht": ":material/bedtime:", "hitze-tag": ":material/wb_sunny:", "versiegelung": ":material/grid_on:",
    "gruenanteil": ":material/park:", "laerm": ":material/volume_up:", "starkregen": ":material/water_drop:",
    "betroffenheit": ":material/elderly:", "mehrfachbelastung": ":material/stacks:",
    "hitzetage-station": ":material/thermostat:", "hitzetage-raster": ":material/thermostat:",
    "luft-station": ":material/air:", "kuehlorte": ":material/ac_unit:", "jungbaeume": ":material/forest:",
    "haushalte": ":material/family_restroom:",
    "umweltzone": ":material/directions_car:", "planungshinweise": ":material/report:",
    "klimatope": ":material/apartment:",
}
_STUFEN_FARBE = {"waerme": "orange", "gruen": "green", "neutral": "blue"}


def thema_farbe(analyse) -> str:
    """Farbname für Markdown und Abzeichen (orange, green, blue, gray) aus den Kartenstufen oder der Richtung."""
    from essen.farben import FARBSTUFEN

    if analyse.stufen:
        for name, farben in FARBSTUFEN.items():
            if tuple(analyse.stufen.farben) == tuple(farben):
                return _STUFEN_FARBE[name]
    return {"hoch_schlecht": "orange", "hoch_gut": "green"}.get(analyse.richtung, "blue")


def thema_marke(analyse) -> str:
    """„:orange[:material/bedtime:]“ – farbiges Symbol eines Themas für Überschriften und Beschriftungen."""
    return f":{thema_farbe(analyse)}[{THEMA_SYMBOL.get(analyse.id, ':material/insights:')}]"


def kennzahl_kachel(analyse, ergebnis, mini_karte: bool = True) -> None:
    """Kachel mit der stadtweiten Kennzahl eines Themas: Symbol, Wert, Satz, kleine Karte, Link zum Thema."""
    from essen.text import zahl

    with st.container(border=True, height="stretch"):
        stellen = analyse.stellen
        wert = "–" if ergebnis.kennzahl_stadt is None else f"{zahl(ergebnis.kennzahl_stadt, stellen)} {analyse.einheit}"
        st.metric(f"{thema_marke(analyse)} **{analyse.thema_titel}**", wert, help=analyse.kurz)
        st.caption(ergebnis.kennzahl_text)
        if (mini_karte and ergebnis.geometrie is not None and analyse.stufen
                and analyse.kennzahl in ergebnis.geometrie.columns):
            st.altair_chart(_mini_karte_gecacht(analyse.id, ergebnis.erstellt, str(pfade.daten())), width="content")
        st.page_link("seiten/themen.py", label="Mehr dazu", icon=":material/arrow_forward:",
                     query_params={"thema": analyse.id})


def grenzen_kasten(analyse, hinweise: list[str] | None = None) -> None:
    """„Was diese Zahl nicht sagt“: die wichtigsten Grenzen, darunter alle Hinweise des Ergebnisses."""
    with st.container(border=True):
        st.markdown("**:material/info: Was diese Zahl nicht sagt**")
        st.markdown("\n".join(f"- {g}" for g in analyse.grenzen_kurz))
        if hinweise:
            with st.expander("Alle Hinweise zur Berechnung"):
                st.markdown("\n".join(f"- {h}" for h in hinweise))


def methodik_text(analyse) -> str | None:
    """Die Methodik-Seite einer Analyse (docs/methodik/…), falls es sie gibt."""
    if not analyse.methodik:
        return None
    pfad = pfade.docs() / analyse.methodik
    return pfad.read_text(encoding="utf-8") if pfad.exists() else None


def geladene_datensaetze(k: Katalog) -> list[Datensatz]:
    return [ds for ds in k.datensaetze.values() if laden.vorhanden(ds)]


def datensatz_wahl(k: Katalog, datensaetze: list[Datensatz], titel: str = "Datensatz") -> str:
    """Auswahl eines Datensatzes, vorgewählt und gemerkt über ?datensatz= (für Links zwischen den Seiten)."""
    ids = [ds.id for ds in datensaetze]
    vorwahl = st.query_params.get("datensatz")
    wahl = st.selectbox(titel, ids, index=ids.index(vorwahl) if vorwahl in ids else 0,
                        format_func=lambda i: k.datensatz(i).titel)
    st.query_params["datensatz"] = wahl
    return wahl


def jahresbalken(tabelle, analyse, hoehe: int = 320) -> None:
    """Balken je Jahr für Stationsanalysen; nur vollständige Jahre (das laufende fehlt)."""
    from essen import diagramme

    voll = tabelle[tabelle["vollstaendig"].astype(bool)] if "vollstaendig" in tabelle.columns else tabelle
    st.bar_chart(voll, x="jahr", y=analyse.kennzahl, color=diagramme.MARKIERT, height=hoehe, x_label="Jahr",
                 y_label=analyse.kennzahl_titel)


def noch_nicht_vorbereitet(was: str = "Für diese Seite") -> None:
    """Einheitlicher Hinweis auf Leseseiten, wenn Ergebnisse fehlen."""
    st.info(f"{was} sind die Daten noch nicht vorbereitet. Ein Klick auf **Alles vorbereiten** lädt sie bei den "
            "Behörden und berechnet alle Themen; danach erscheinen hier die Ergebnisse.", icon=":material/rocket_launch:")
    st.page_link("seiten/vorbereiten.py", label="Zu „Alles vorbereiten“", icon=":material/rocket_launch:")


def lizenz_abzeichen(k: Katalog, ds: Datensatz) -> None:
    lizenz = k.lizenz_von(ds)
    st.badge(lizenz.kurz, color=LIZENZ_FARBE.get(lizenz.id, "red" if lizenz.pruefen else "gray"),
             help=lizenz.hinweis)


def abzeichen(k: Katalog, ds: Datensatz) -> None:
    with st.container(horizontal=True, gap="small"):
        lizenz_abzeichen(k, ds)
        st.badge(STATUS_KURZ[ds.status], color=STATUS_FARBE[ds.status], help=STATUS[ds.status])
        if ds.download.groesse_mb:
            st.badge(megabyte(ds.download.groesse_mb), color="gray")
        for thema in ds.themen:
            st.badge(THEMEN[thema], color="gray")


def fortschritt(platz):
    balken = platz.progress(0.0, text="Starte …")

    def melde(geladen: int, gesamt: int | None, text: str) -> None:
        if gesamt:
            balken.progress(min(1.0, geladen / gesamt), text=f"{text}: {groesse(geladen)} von {groesse(gesamt)}")
        else:
            balken.progress(0.0, text=f"{text}{': ' + groesse(geladen) if geladen else ''}")
    return melde


def download_knopf(k: Katalog, ds: Datensatz, zusatz: str = "") -> None:
    """Zeigt Stand und Knopf zum Laden eines Datensatzes. Für manuelle Datensätze: Link und Datei-Übernahme."""
    schluessel = f"{ds.id}-{zusatz}"
    abruf = laden.lese_abruf(ds)
    geladen = laden.vorhanden(ds)
    if geladen:
        st.markdown(f":material/check_circle: Geladen am {datum(abruf.datum)}, {groesse(belegt(ds, abruf))}"
                    + (" · mit erfundenen Testdaten" if abruf.testdaten else ""))
    if not ds.ladbar:
        if ds.download.art == "keiner":
            st.caption("Nichts zu laden: wird als Kartendienst direkt angezeigt.")
            return
        st.link_button("Zur Quelle", ds.seite, icon=":material/open_in_new:", width="stretch")
        datei = st.file_uploader("Von Hand geladene Datei übernehmen", key=f"hoch-{schluessel}",
                                 help=ds.download.hinweis or None)
        if datei is not None and st.button("Übernehmen", key=f"uebernehmen-{schluessel}", width="stretch"):
            laden.einlesen_bytes(ds, datei.name, bytes(datei.getbuffer()))
            st.toast(f"{ds.titel}: Datei übernommen", icon=":material/check:")
            st.rerun()
        return

    bestaetigt = True
    if ds.gross and not geladen:
        bestaetigt = st.checkbox(f"Ich habe Platz für {megabyte(ds.download.groesse_mb)}", key=f"platz-{schluessel}")
    kandidaten = st.session_state.get(f"kandidaten-{ds.id}")
    auswahl = None
    if kandidaten:
        auswahl = st.selectbox("Mehrere Dateien passen, bitte wählen", kandidaten, key=f"wahl-{schluessel}")
    beschriftung = "Neu laden" if geladen else "Herunterladen"
    if st.button(beschriftung, key=f"laden-{schluessel}", type="secondary" if geladen else "primary",
                 icon=":material/download:", disabled=not bestaetigt, width="stretch"):
        platz = st.empty()
        try:
            laden.hole(k, ds, fortschritt=fortschritt(platz), erzwingen=geladen, datei=auswahl)
        except laden.MehrereDateien as fehler:
            st.session_state[f"kandidaten-{ds.id}"] = [d.name for d in fehler.kandidaten]
            st.rerun()
        except laden.DownloadFehler as fehler:
            platz.empty()
            st.error(str(fehler), icon=":material/error:")
            return
        st.session_state.pop(f"kandidaten-{ds.id}", None)
        st.toast(f"{ds.titel}: geladen", icon=":material/check:")
        st.rerun()


def daten_zeile(k: Katalog, kennung: str, pflicht: bool = True) -> None:
    """Kompakte Zeile für Seiten, die bestimmte Datensätze brauchen (z. B. Analysen)."""
    ds = k.datensatz(kennung)
    links, rechts = st.columns([3, 1.4], vertical_alignment="center")
    with links:
        zeichen = ":material/check_circle:" if laden.vorhanden(ds) else (":material/radio_button_unchecked:")
        st.markdown(f"{zeichen} **{ds.titel}**" + ("" if pflicht else " · optional"))
        st.caption(f"{kat.anbieter(k, ds)} · {ds.format}"
                   + (f" · {megabyte(ds.download.groesse_mb)}" if ds.download.groesse_mb else ""))
    with rechts:
        download_knopf(k, ds, zusatz="zeile")
