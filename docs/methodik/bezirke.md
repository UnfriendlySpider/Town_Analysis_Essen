# Werte je Stadtbezirk

**Frage:** Wie steht ein Stadtbezirk (mehrere Stadtteile) in einem Thema da, und wie ein Stadtteil im Vergleich zu seinem Bezirk?

**Code:** `src/essen/bezirke.py` · **Anzeige:** „Mein Stadtteil“ (Satz und gestrichelter Strich je Thema), „Themen“ (Aufklapper „Nach Stadtbezirken“) · **Entscheidung:** E-018

## Rechenweg

1. Welcher Stadtteil zu welchem Bezirk gehört, steht in der Stadtteildatei der Stadt (Feld `STADTBEZ`, 1 bis 9; im Katalog `felder.bezirk`). Gelesen werden nur die Sachdaten.
2. Je Thema: das gespeicherte Ergebnis der Stadtteile, die Kennzahl und das Gewicht der Analyse (`Analyse.gewicht`), zum Beispiel die bebaute Fläche bei der Hitze in der Nacht, die Landfläche beim Starkregen, die Zahl der Haushalte bei den Haushalten.
3. Bezirkswert = Summe (Kennzahl × Gewicht) / Summe Gewicht über die Stadtteile des Bezirks mit Wert. Stadtteile ohne Wert (Mindestbezug) zählen nicht, genau wie beim stadtweiten Wert.

| Thema | Gewicht |
| --- | --- |
| Hitze in der Nacht | bebaute Fläche (`wirkraum_ha`) |
| Hitze am Tag, Versiegelung | bewertete Fläche (`bewertet_ha`) |
| Grün | bedeckte Fläche (`bedeckt_ha`) |
| Starkregen | Landfläche (`land_ha`, ohne Gewässerabzug die ganze Fläche) |
| Hitzebetroffenheit | Fläche der Baublöcke (`baubloecke_ha`) |
| Lärm, kühle Orte, Umweltzone, Jungbäume, heiße Tage | Fläche des Stadtteils (`flaeche_ha`) |
| Haushalte | Zahl der Haushalte (`haushalte`) |
| Mehrfachbelastung, Stationen | keine Bezirkswerte |

## Prüfung mit echten Daten (12.10.2026)

- 50 Stadtteile in 9 Bezirken: I 8, II 4, III 6, IV 8, V 4, VI 3, VII 5, VIII 6, IX 6 Stadtteile.
- Gegenprobe: das gewichtete Mittel der Bezirke ergibt den stadtweiten Wert (Starkregen 2,951 = 2,951; Haushalte 18,315 zu 18,32 und Jungbäume 63,284 zu 63,281, Unterschied durch gerundete Spalten).
- Hitze in der Nacht: Stadtbezirk I 79,1 %, V 73,4 %, IV 71,2 %; VIII 32,5 %, IX 31,6 %.

## Grenzen

- Ein Bezirk fasst sehr unterschiedliche Stadtteile zusammen; der Bezirkswert kann einen auffälligen Stadtteil verdecken.
- Die Spalten der Stadtteile sind auf eine Nachkommastelle gerundet gespeichert; Bezirkswerte können deshalb in der letzten Stelle vom genauen Wert abweichen.
- Die Bezirke heißen nur nach ihrer Nummer, weil keine Quelle ihre Namen nennt.
