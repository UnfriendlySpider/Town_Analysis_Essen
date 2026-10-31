# Luftqualität an den Essener Messstationen

**Frage:** Wie haben sich Stickstoffdioxid und Feinstaub an den Essener Messstationen entwickelt, gemessen an den Grenzwerten?

**Code:** `src/essen/analysen/luft_station.py` · **Aufruf:** `uv run essen analyse luft-station [-p schadstoff=pm10]`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `uba-jahresbilanzen` | Jahresbilanzen des Umweltbundesamts (API `annualbalances`) für NO₂, PM₁₀ und PM₂,₅, 2010 bis 2025, alle Stationen in Deutschland; dazu die Stationsliste |

## Rechenweg

1. Essener Stationen sind alle Stationen, deren Ort („station city“) „Essen“ enthält (17 für NO₂ seit 2010, darunter Essen-Vogelheim). Die Spalten der Stationsliste werden über ihre Namen in `indices` gefunden, nicht über die Position.
2. Jede Jahresbilanz nennt in `headers`, welcher Wert was ist (z. B. „Jahresmittelwert in µg/m³“). Die Analyse sucht das Jahresmittel über diesen Text; fehlt er oder ist er nicht eindeutig, bricht sie ab (E-009). Die Stationsnummer der Bilanz ist die `station id` der Stationsliste (alle 570 Nummern der NO₂-Bilanz 2024 gefunden).
3. Je Jahr: höchstes Jahresmittel einer Essener Station, Mittel der Stationen, Zahl der Stationen und wie viele über den Vergleichswerten liegen.
4. Vergleichswerte (Jahresmittel in µg/m³):

   | Stoff | Grenzwert bis 2029 (2008/50/EG) | Grenzwert ab 2030 ((EU) 2024/2881) | WHO-Richtwert 2021 |
   | --- | --- | --- | --- |
   | NO₂ | 40 | 20 | 10 |
   | PM₁₀ | 40 | 20 | 15 |
   | PM₂,₅ | 25 | 10 | 5 |

## Prüfung mit echten Daten (11.10.2026)

- NO₂: höchstes Jahresmittel 60 µg/m³ (2010) → 34 µg/m³ (2025, Kruppstraße 117). Stationen über 40 µg/m³: 10 von 13 (2010), 2 (2019), 0 (2020), je 1 (2021 bis 2023), 0 seit 2024. 2025 lagen 10 von 12 Stationen über dem Wert ab 2030 und alle 12 über dem WHO-Richtwert.
- PM₁₀: seit 2010 keine Station über 40 µg/m³; 2025 höchstens 25 µg/m³ (Gladbecker Straße), 1 von 4 über 20.
- PM₂,₅: seit 2010 keine Station über 25 µg/m³; 2025 höchstens 12 µg/m³ (Vogelheim), 2 von 3 über 10.
- Gegenprobe: Werte für 2024 direkt aus der API-Abfrage (DENW043 22, DENW399 39, DENW215 33 µg/m³) stimmen mit der Tabelle überein.

## Grenzen

- Stationen messen an ihrem Ort, meist an stark befahrenen Straßen. Die Werte gelten nicht für ganze Stadtteile; deshalb geht Luft (noch) nicht in die Mehrfachbelastung ein (E-008 verlangt eine Kennzahl je Stadtteil).
- Die Stationen wechseln: Das höchste Jahresmittel hängt auch davon ab, welche Stationen gerade messen (z. B. Kruppstraße erst ab 2020).
- Jahresbilanzen gibt es nur für abgeschlossene, geprüfte Jahre; das Vorjahr ist ab Juni vollständig.

## Ergebnis

`data/processed/luft-station/`: `tabelle.csv` (ein Jahr je Zeile, dazu eine Spalte `wert_<Station>` je Station), `ergebnis.json`.
