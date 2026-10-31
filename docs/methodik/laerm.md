# Lärmbelastung je Stadtteil

**Frage:** Welcher Anteil der Fläche eines Stadtteils liegt nachts oder ganztags über der Lärmschwelle?

**Code:** `src/essen/analysen/laerm.py` · **Aufruf:** `uv run essen analyse laerm [-p zeitraum=ganztags] [-p schwelle_db=60]`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Bezugsflächen, 50 Stadtteile |
| `laermkarte-essen` | Lärmkarte der Stadt Essen: acht Shapes (Straßen 2011; Eisenbahn DB, Ruhrbahn, Industrieanlagen 2016; je ganztags L_DEN und nachts L_Night), EPSG:4647 |

## Rechenweg

1. Je Quelle und Zeitraum gibt es eine Datei mit Isophonen-Flächen in 5-dB-Stufen. Welche Datei, welches Feld den Pegel trägt und wie es zu lesen ist, steht in `katalog/zuordnungen/laermkarte-essen.yaml`. Die Dateien sind verschieden aufgebaut:

   | Quelle | Feld | Aufbau |
   | --- | --- | --- |
   | Straßen | `WERT` (45 bis 75) | verschachtelt: jede Stufe liegt ganz in der nächstniedrigeren, Fläche heißt „mindestens X dB(A)“ |
   | Eisenbahn (DB) | `KLASSE` (X,01) | verschachtelt, Untergrenze als „über X“ geschrieben |
   | Ruhrbahn | `ISOV1`, `ISOV2` | getrennte Bänder mit Unter- und Obergrenze |
   | Industrieanlagen | `WERT` | getrennte Bänder; `WERT` als Untergrenze gelesen wie bei den Straßen (gleicher Dateiaufbau) |

2. Je Datei werden alle Flächen mit Untergrenze ab der Schwelle genommen und vereinigt. Das ergibt für verschachtelte Flächen und für Bänder dasselbe: die Fläche mit mindestens der Schwelle. Untergrenzen außerhalb der 5-dB-Stufen führen zum Abbruch (E-009).
3. Die Flächen der vier Quellen werden vereinigt, nicht addiert: gezählt wird die Fläche, an der **mindestens eine Quelle** über der Schwelle liegt. Pegel verschiedener Quellen addieren sich energetisch (zwei gleich laute Quellen ergeben 3 dB mehr); das lässt sich aus Stufenkarten nicht nachrechnen.
4. Schwelle: Standard sind 55 dB(A) nachts und 65 dB(A) ganztags, die Auslösewerte der ersten Stufe für die Lärmaktionsplanung laut Umweltbundesamt. Wählbar sind 55 bis 70 dB(A); darunter sind nicht alle Dateien vollständig (die Straßenkarte ganztags hat unter 55 dB(A) nur 29 ha).
5. Je Stadtteil: Fläche über der Schwelle (alle Quellen zusammen) und Anteil je Quelle, bezogen auf die ganze Fläche des Stadtteils. Unter 5 ha Fläche bleibt der Anteil leer (Parameter `min_flaeche_ha`).
6. Der stadtweite Wert ist das flächengewichtete Mittel der Stadtteile.

## Prüfung mit echten Daten (10.10.2026)

- Nachts über 55 dB(A): stadtweit 18,4 %; ganztags über 65 dB(A): 16,3 %.
- Unabhängige Gegenrechnung (je Datei andere Auswahl: verschachtelte Dateien nur die Stufe selbst, Bänder alle ab der Schwelle; Schnitt mit dem ganzen Stadtgebiet statt je Stadtteil): 3.872,6 ha = 18,42 % nachts, 3.436,4 ha = 16,34 % ganztags.
- Lage der Stufen geprüft: Straßen und DB je Stufe zu 100 % in der darunter, Ruhrbahn und Industrie zu unter 2 % überlappend.
- Am stärksten belastet (nachts): Ostviertel 61,2 % (davon Eisenbahn 30,9 %, Industrie 15,6 %), Südviertel 44,3 %, Karnap 43,3 %, Stadtkern 43,1 %, Dellwig 41,4 % (fast nur Eisenbahn). Am wenigsten: Fischlaken 1,4 %, Burgaltendorf und Heidhausen je 3,6 %.
- Zusammenhang mit anderen Themen über die 50 Stadtteile: Korrelation mit dem versiegelten Anteil 0,69, mit dem Grünanteil −0,75. Lärm misst also etwas Eigenes, hängt aber an der Bebauung.
- Rechenzeit etwa 5 Sekunden.
- Einwohner (Zensus-Gitter, optional, 11.10.2026): geschätzt 107.200 von 570.632 (18,8 %) wohnen nachts über 55 dB(A). Gegenrechnung mit Zellmittelpunkten statt Flächenanteil: 104.905. Verfahren nach E-013.

## Grenzen

- **Alter:** Straßen 2011, übrige Quellen 2016. Neuere Kartierungen für Essen sind im Portal nicht zu finden (`laermkarten-nrw` enthält Essen nicht).
- Lärmkarten sind Modellrechnungen, keine Messungen.
- Bei den Industrieanlagen ist `WERT` als Untergrenze gelesen, abgeleitet aus dem gleichen Dateiaufbau wie bei den Straßen; eine Legende des Anbieters fehlt. Wäre `WERT` die Obergrenze, läge die Industriefläche um eine Stufe niedriger. Stadtweit macht Industrie allein 196 ha der 3.873 ha aus (nachts, vor dem Vereinigen).
- Bezug ist die Fläche, nicht die Zahl der Betroffenen (E-007). Ein Stadtteil mit einer großen Straße durch Wald hat laute Fläche, aber wenige Betroffene (Schuir: 17,6 % laut bei 89,5 % Grün).

## Ergebnis

`data/processed/laerm/`: `tabelle.csv`, `gebiete.geojson`, `ergebnis.json`. Mit `--export` zusätzlich `data/export/laerm.html`.
