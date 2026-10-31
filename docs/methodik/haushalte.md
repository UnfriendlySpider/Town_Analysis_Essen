# Privathaushalte je Stadtteil

**Frage:** In welchen Stadtteilen leben viele Familien mit Kindern, wo viele Menschen allein, und wie hat sich das seit 2007 verändert?

**Code:** `src/essen/analysen/haushalte.py` · **Aufruf:** `uv run essen analyse haushalte`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `stadtteile` | Flächen und Namen, 50 Stadtteile, Nummer im Feld `STADTT` |
| `privathaushalte-stadtteile` | CSV des Amts für Statistik: je Stadtteil und Jahr (2007 bis 2025) Haushalte insgesamt, Einpersonenhaushalte, Haushalte mit Kindern, Personen in Privathaushalten |

Laut Datensatzseite gilt jeweils der Stichtag 31.12. Die Stadt bildet die Haushalte aus den Meldedaten, zum Beispiel aus Familienbeziehungen, Namen und gleicher Adresse. Menschen in Heimen und Einrichtungen zählen nicht. Die Datei ist in Windows-1252 kodiert.

## Rechenweg

1. Die CSV wird gelesen (Semikolon, erst UTF-8, sonst Windows-1252). Fehlt eine der nötigen Spalten oder steht dort keine Zahl, bricht die Analyse mit einer Meldung ab.
2. Je Zeile werden berechnet:
   - Anteil der Haushalte mit Kindern (`HH_MIT_KINDERN / INSGESAMT`)
   - Anteil der Einpersonenhaushalte (`HH_EINE_PERSON / INSGESAMT`)
   - Personen je Haushalt (`BEVOELKERUNG_IN_HH / INSGESAMT`)
3. Die Spalte `Stadtteil` (Nummer 1 bis 50) wird der Nummer der Stadtteilgrenzen zugeordnet. Die Namen kommen aus den Grenzen, nicht aus der CSV.
4. Die Tabelle je Stadtteil zeigt den Stand des letzten Jahres. Die Änderung ist die Differenz zum ersten Jahr in Prozentpunkten.
5. Die Werte aller Jahre liegen in `jahreswerte.csv`. Daraus entsteht auf der Seite „Themen“ der Verlauf über die Jahre, als Karte je Jahrzehnt oder je Jahr.
6. Der stadtweite Wert ist die Summe aller Haushalte mit Kindern geteilt durch alle Haushalte, nicht das Mittel der Stadtteile.

## Prüfung mit echten Daten (11.10.2026)

- 950 Zeilen: 50 Stadtteile × 19 Jahre. Alle Nummern passen zu den Grenzen.
- Die Teilmengen sind stimmig: Einpersonenhaushalte und Haushalte mit Kindern sind nie mehr als alle Haushalte.
- 2025 lebten 588.765 Menschen in 313.736 Privathaushalten. In 18,3 % der Haushalte leben Kinder (2007: 19,2 %), 50,9 % sind Einpersonenhaushalte (2007: 45,9 %). Im Schnitt leben 1,88 Personen in einem Haushalt (2007: 1,94).
- Den höchsten Anteil an Haushalten mit Kindern haben Vogelheim (26,0 %), Katernberg (25,5 %) und Horst (24,3 %), den niedrigsten Südviertel (12,3 %), Stadtkern und Westviertel (je 12,8 %).
- Die meisten Einpersonenhaushalte gibt es im Stadtkern (66,6 %), im Südviertel (65,7 %) und in Holsterhausen (64,6 %).
- Seit 2007 ist der Anteil der Haushalte mit Kindern am stärksten in Bedingrade (−4,4 Prozentpunkte) und Stoppenberg (−4,1) gesunken. Am stärksten gestiegen ist er im Westviertel (+1,4).

## Grenzen

- Haushalte werden aus den Meldedaten geschätzt, nicht gezählt oder erfragt.
- Die Quelle sagt nicht, bis zu welchem Alter jemand als Kind zählt. Die Spalten `HH_EINE_PERSON_25B69` (vermutlich Alleinlebende von 25 bis 69 Jahren), `HH_MIT_3OM_KINDERN` und `HH_ALLEINERZIEHEND` sind nicht beschrieben und werden nicht genutzt (E-009).
- Ein Anteil sagt nichts über die Zahl: Ein großer Stadtteil mit kleinem Anteil kann mehr Familien haben als ein kleiner mit großem Anteil.
- Nicht Teil der Mehrfachbelastung (E-008). Die Zahl beschreibt, wer in einem Stadtteil wohnt, nicht wie stark er belastet ist.

## Ergebnis

`data/processed/haushalte/`: `tabelle.csv`, `jahreswerte.csv`, `gebiete.geojson`, `ergebnis.json`.
