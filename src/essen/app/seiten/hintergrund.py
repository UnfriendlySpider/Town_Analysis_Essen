"""Methodik, Lizenzen und Quellenangaben."""

import pandas as pd
import streamlit as st

from essen import analysen, laden, pfade
from essen.app.gemeinsam import katalog, kopf, seitenhilfe
from essen.katalog import lizenz_tabelle

kopf("Methodik und Lizenzen")
seitenhilfe("methodik")
k = katalog()

methodik, lizenzen, angaben, ueber = st.tabs(["Methodik", "Lizenzen", "Quellenangaben", "Über die App"])

with methodik:
    dateien = sorted((pfade.docs() / "methodik").glob("*.md"))
    if not dateien:
        st.caption("Noch keine Methodik-Seiten in docs/methodik/.")
    titel = {a.methodik.rsplit("/", 1)[-1]: a.thema_titel or a.titel for a in analysen.ALLE.values() if a.methodik}
    for datei in sorted(dateien, key=lambda d: titel.get(d.name, d.stem).lower()):
        with st.expander(titel.get(datei.name, datei.stem.replace("-", " ").capitalize()),
                         expanded=len(dateien) == 1):
            st.markdown(datei.read_text(encoding="utf-8"))

with lizenzen:
    st.markdown("Für das private Projekt auf dem eigenen Rechner gilt keine Pflicht. Sie greifen, sobald Ergebnisse "
                "geteilt oder veröffentlicht werden.")
    st.dataframe(pd.DataFrame(lizenz_tabelle(k)), hide_index=True, width="stretch",
                 column_config={"Text": st.column_config.LinkColumn("Text", display_text="Lizenztext")})

with angaben:
    zeilen = laden.quellenangaben(k)
    if not zeilen:
        st.caption("Noch nichts geladen.")
    else:
        st.markdown("Quellenangaben aller geladenen Daten, zum Beispiel für eine Fußzeile:")
        st.code("\n".join(zeilen), language=None, wrap_lines=True)

with ueber:
    st.markdown(f"""
- **Läuft lokal:** Die App hört nur auf `localhost`. Andere Geräte im Netz erreichen sie nicht.
- **Keine Daten im Projekt:** Alles Geladene liegt in `{pfade.relativ(pfade.daten())}/` und wird nicht weitergegeben.
- **Netzverkehr:** Downloads gehen direkt an die Anbieter. Karten laden Kacheln von basemap.de (BKG), die
  Kartenbibliothek Leaflet von cdn.jsdelivr.net und eingeblendete Kartendienste vom jeweiligen Anbieter.
- **Keine Nutzungsstatistik:** Die Telemetrie von Streamlit ist abgeschaltet.
- **Aufbau und Erweiterung:** `docs/architektur.md`, Anleitungen für Agenten in `AGENTS.md`.
""")
