"""Private Analyse öffentlicher Geo-, Umwelt- und Stadtdaten für Essen.

Aufbau (siehe docs/architektur.md):
    katalog      Quellen, Datensätze und Lizenzen aus katalog/*.yaml
    laden        Downloads aus der Originalquelle mit Protokoll
    geo          Stadtteile, Stadtgebiet, Koordinatensysteme
    inspizieren  unbekannte Dateien untersuchen
    kennzahlen   Flächenanteile und Zählungen je Gebiet
    analysen     fertige Auswertungen (Registry in analysen/__init__.py)
    karte        Karten für die App (folium)
    bericht      eigenständige HTML-Seiten zum Weitergeben
    app          lokale Streamlit-App
    cli          Kommandozeile `essen`
"""

__version__ = "0.2.0"
