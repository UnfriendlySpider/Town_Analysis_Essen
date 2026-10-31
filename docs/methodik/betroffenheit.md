# Hitzebetroffenheit je Stadtteil

**Frage:** Welcher Anteil der Wohnblöcke eines Stadtteils ist für Hitze empfindlich und zugleich stark hitzebelastet?

**Code:** `src/essen/analysen/betroffenheit.py` · **Aufruf:** `uv run essen analyse betroffenheit`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `klimaanalyse-betroffenheit` | Betroffenheitsanalyse der Klimaanalyse NRW 2026 (LANUK), GeoPackage, Baublöcke |

## Was der Anbieter gerechnet hat

Laut Methodik-Papier des LANUK (Stand 03/2026):

1. Aus dem Zensus 2022 je Baublock: Hochaltrige (ab 80) und Kleinkinder (unter 6) je Fläche, durchschnittliche Nettokaltmiete (Ersatz für Armutsgefährdung). Jeder Wert wird **je Gemeinde** in Dezile eingeteilt; Dezil 8 sensitiv, 9 hoch, 10 extrem sensitiv (bei der Miete: niedrige Miete = hohes Dezil).
2. Gesamtbetrachtung: sensitiv = Hochaltrige 8–10 oder Kinder 10 oder Miete 10; hoch sensitiv = Hochaltrige 8–10 und (Kinder 10 oder Miete 10); extrem sensitiv = alle drei.
3. Überlagerung mit der Planungshinweiskarte: Layer `_HP` enthält nur die Baublöcke mit Handlungspriorität 1 oder 2 (dringender Handlungsbedarf wegen Hitze), `_komplett` alle Baublöcke im Siedlungsbereich.

## Rechenweg

1. Beide Layer für die Gemeinde Essen lesen (Feld `gemeind`); die Dezile gelten je Gemeinde. Codes in `senstvt` und Text in `Betroffenheit` werden gegeneinander geprüft (`katalog/zuordnungen/klimaanalyse-betroffenheit.yaml`).
2. Je Stadtteil: Baublockfläche (`_komplett`), davon sensitiv (ab Klasse 2), davon mit Handlungsbedarf (`_HP`) und davon sensitiv **und** mit Handlungsbedarf.
3. Kennzahl: Anteil der Baublockfläche, die sensitiv und hitzebelastet ist. Unter 5 ha Baublockfläche bleibt der Anteil leer.

## Prüfung mit echten Daten (11.10.2026)

- Essen: 11.180 Baublöcke mit 9.117,4 ha, davon 5.583 Blöcke (3.888,1 ha) mit dringendem Handlungsbedarf. `_HP` liegt vollständig in `_komplett`, beide überschneidungsfrei.
- Stadtweit 9,4 % der Baublockfläche sensitiv und hitzebelastet; 19,2 % sensitiv; 42,6 % mit Handlungsbedarf. Gegenrechnung ohne Stadtteile: 856,7 ha von 9.117,4 ha = 9,4 %.
- Am höchsten: Südostviertel 39,3 %, Frohnhausen 30,9 %, Altendorf 28,7 %, Bochold 26,5 %, Rüttenscheid 25,5 %, Holsterhausen 25,0 %. Am niedrigsten: Byfang 0,0 %, Heidhausen und Margarethenhöhe je 0,3 %.
- Über die Stadtteile korreliert der Handlungsbedarf mit `hitze-nacht` zu 0,96, die Betroffenheit zu 0,67: Die Sensitivität fügt also etwas Eigenes hinzu.

## Grenzen

- **Relativ innerhalb Essens:** Dezile je Gemeinde. „Sensitiv“ heißt „im obersten Bereich Essens“, nicht „über einer festen Grenze“.
- Bezug ist Baublockfläche, nicht die Zahl der Menschen; ein großer, dünn bewohnter Block zählt mehr als ein kleiner, dichter.
- Die Nettokaltmiete ist nur ein Ersatz für Armutsgefährdung.
- Hitzebelastung ist ein Modellergebnis der Planungshinweiskarte (Klimaanalyse NRW 2026).
- Nicht in der Mehrfachbelastung (E-008): Der Handlungsbedarf ist fast dasselbe wie die Hitze in der Nacht.

## Ergebnis

`data/processed/betroffenheit/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/betroffenheit.html`.
