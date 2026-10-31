# Hitzetage und Tropennächte an der Station Essen-Bredeney

**Frage:** Wie oft wird es in Essen heiß, und hat das zugenommen?

**Code:** `src/essen/analysen/hitzetage_station.py` · **Aufruf:** `uv run essen analyse hitzetage-station`

## Daten

| Datensatz | Rolle |
| --- | --- |
| `dwd-klima-essen-aktuell` | Tageswerte der letzten rund 500 Tage, noch nicht vollständig geprüft |
| `dwd-klima-essen-historisch` | geprüfte Tageswerte seit Beginn der Reihe (optional, für lange Reihen nötig) |

Beide kommen vom Climate Data Center des DWD (CC BY 4.0). Die Stations-ID 01303 für Essen-Bredeney ist im Katalog eingetragen und noch in der Stationsliste (`dwd-stationen-kl`) zu bestätigen.

## Rechenweg

1. Aus jedem ZIP wird `produkt_klima_tag_*.txt` gelesen (Semikolon, Fehlwert −999). Genutzt werden TXK (Tageshöchstwert), TNK (Tagestiefstwert), TMK (Tagesmittel) und RSK (Niederschlag), alle in 2 m Höhe.
2. Historische und aktuelle Werte werden zusammengeführt. Wo sich beide überschneiden, gilt der geprüfte historische Wert.
3. Kenntage nach den Definitionen des DWD:

   | Kenntag | Bedingung |
   | --- | --- |
   | Sommertag | Höchstwert ab 25 °C |
   | heißer Tag | Höchstwert ab 30 °C |
   | Tropennacht | Tiefstwert ab 20 °C |
   | Frosttag | Tiefstwert unter 0 °C |
   | Eistag | Höchstwert unter 0 °C |

4. Ein Jahr gilt als vollständig, wenn an mindestens 95 % der Tage Höchst- und Tiefstwert vorliegen. Das laufende Jahr ist nie vollständig.
5. Die Kennzahl vergleicht das Mittel der heißen Tage im Bezugszeitraum 1991 bis 2020 (einstellbar) mit dem Mittel der letzten zehn vollständigen Jahre.

## Grenzen

- Eine einzelne Station am südlichen Stadtrand in 150 m Höhe. Die Innenstadt ist wärmer, besonders nachts. Für die räumliche Verteilung ist die Klimaanalyse da.
- Der Tagestiefstwert bezieht sich auf den Kalendertag, nicht auf die Nacht von abends bis morgens. Tropennächte werden so leicht unterschätzt.
- Stationsverlegungen und Messwechsel stehen in den Metadaten im ZIP und sind nicht korrigiert. Wichtig für lange Reihen: Am 12.07.1965 wurde die Station von 120 m auf 153,5 m Höhe und rund 2 km nach Osten verlegt.
- Es fehlen die Jahre 1937 und 1945 bis 1947. Unvollständige Jahre (auch das laufende) zählen nicht in Mittelwerten und Ranglisten.
- Nachgerechnet am 10.10.2026: 2022 mit 47 Sommertagen, 13 heißen Tagen und 2 Tropennächten stimmt mit einer Zählung direkt aus der Rohdatei überein.
