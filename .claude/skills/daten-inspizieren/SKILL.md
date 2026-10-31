---
name: daten-inspizieren
description: Untersucht geladene oder unbekannte Geodaten (Layer, Felder, Wertebereiche, Rasterklassen, Legenden) mit `essen inspizieren`, deutet den Bericht und hält Erkenntnisse im Katalog fest. Verwenden, bevor mit neuen Daten gerechnet wird, wenn eine Analyse Daten nicht erkennt oder wenn jemand einen Inspektionsbericht schickt.
---

# Daten inspizieren

Ziel: verstehen, was in einer Datei steckt, bevor eine Analyse damit rechnet. Niemals Feldbedeutungen oder
Rasterkodierungen raten (docs/entscheidungen.md, E-009).

## 1. Bericht erzeugen

```bash
uv run essen laden ID                      # falls noch nicht geladen
uv run essen inspizieren ID                # Bericht nach data/inspektion/ID.md
uv run essen inspizieren PFAD/zur/datei    # beliebige Datei oder ZIP
```

In der App: Seite **Inspektion**. Der Bericht deckt ab:

| Teil | Inhalt |
| --- | --- |
| ZIP | Dateien, Größen, Kompression |
| Vektor | je Layer Geometrie, Koordinatensystem, Anzahl (gesamt und im Stadtgebiet), je Feld Typ, Füllgrad, häufigste Werte oder Spanne |
| Raster | Größe, Bänder, Typ, Fehlwert, Farbdeutung, Farbtabelle, Ausschnitt Essen; Klassenraster (bis 64 Werte) mit Häufigkeiten und Farben, sonst Verteilung |
| Tabellen | Trennzeichen, Spalten, Probe |
| Legenden | Werte, Beschriftungen und Farben aus `.qml`, `.sld`, `.lyrx`, auch aus begleitenden Datensätzen (`begleitend` im Katalog) |

## 2. Deuten

Fragen, die der Bericht beantworten soll:

- **Koordinatensystem:** EPSG:25832 erwartet. Andere Systeme sind in Ordnung, die Funktionen rechnen um.
- **Abdeckung:** Gibt es Objekte im Stadtgebiet? „im Stadtgebiet: 0“ heißt meist falscher Layer oder falsches Koordinatensystem.
- **Schlüssel:** Welches Feld ist Name, welches Nummer? Technische Kennungen (FID, OBJECTID, GlobalID) sind keine Fachnummern.
- **Klassen im Raster:** Passen die Werte zu einer Legende? Farben der Farbtabelle mit den Farben der Legende abgleichen. Stetige Werte zwischen 5 und 35 sehen nach Temperatur aus, 50 bis 350 nach Zehntelgrad.
- **Begleitende Beschreibung:** PDF-Dokumente stehen im Bericht nur als Hinweis; sie müssen gelesen werden (Read-Werkzeug oder vom Menschen).

## 3. Festhalten

- Erkenntnisse über den Aufbau als `hinweise` beim Datensatz in `katalog/datensaetze.yaml` eintragen, z. B. Layernamen und Feldbedeutungen. Bekannte Felder unter `felder` (z. B. `{name: STADTTEILE}`).
- Wertezuordnungen (z. B. Rasterwert → Temperaturklasse) als Datei in `katalog/zuordnungen/ID.yaml` anlegen. Format in `docs/katalog.md`. `geprueft: true` erst nach Abgleich mit der Legende des Anbieters. Eine Vorlage schreibt die Analyse `hitze-nacht` nach `data/zuordnungen/`, wenn sie die Kodierung nicht erkennt.
- Danach `uv run essen katalog --pruefen` und `--doku`.

## 4. Wenn ein Mensch einen Bericht schickt

Die Person hat die Daten lokal, der Agent oft nicht. Dann:
1. Bericht lesen, Layer/Felder/Werte mit dem Katalog abgleichen.
2. Unklare Punkte als Fragen formulieren (welche Legende, welche Einheit).
3. Zuordnung oder Katalogeintrag vorbereiten und kenntlich machen, was belegt ist und was nicht.
4. Mit Testdaten im gleichen Aufbau prüfen (`src/essen/testdaten.py` anpassen, falls nötig), damit der Fall künftig getestet ist.
