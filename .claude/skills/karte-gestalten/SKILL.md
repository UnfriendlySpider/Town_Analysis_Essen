---
name: karte-gestalten
description: Gestaltet Karten, Farbstufen und Legenden für Kennzahlen (folium in der App, MapLibre-Seiten für den Export) und prüft Farben mit einem Skript und die Darstellung per Screenshot. Verwenden bei neuen Karten, Farbskalen, Legenden, Tooltips oder Export-Seiten.
---

# Karten gestalten

Zwei Wege, eine Regel: Die Rechnung liefert Werte, die Karte zeigt sie. Keine Rechnung in Karten-Code.

| Wo | Technik | Code |
| --- | --- | --- |
| App | folium (Leaflet), eingebettet mit `st.iframe` | `src/essen/karte.py` |
| Seite zum Weitergeben | MapLibre GL, eine HTML-Datei | `src/essen/bericht.py` |

Hintergrund ist immer basemap.de grau mit Vermerk „© GeoBasis-DE / BKG (Jahr) CC BY 4.0“. folium lädt nur
Leaflet nach (`neue_karte` setzt `default_js`/`default_css`), keine weiteren fremden Skripte.

## Farbstufen

- Eine Kennzahl mit Richtung (mehr ist schlechter oder besser): **eine Farbe, hell nach dunkel**, fünf Stufen. Keine Regenbögen.
- Abweichungen um einen Mittelwert: zwei Farben mit grauer Mitte.
- Fehlende oder nicht belastbare Werte: `KEINE_DATEN` (#d9ddd8) mit eigenem Legendeneintrag, der den Grund nennt („zu wenig bebaut“).
- Nur geprüfte Stufenfolgen aus `src/essen/farben.py` verwenden: `waerme` (Hitze, Belastung), `gruen` (Vegetation), `neutral` (ohne Wertung). Eine neue Folge zuerst prüfen:

```bash
uv run python .claude/skills/karte-gestalten/farben_pruefen.py "#a8cbe6,#7aaed6,#4f91c2,#2f73a6,#1d5582"
```

Das Skript prüft durchgehende Helligkeit, Abstand der Nachbarstufen bei normalem Sehen (≥ 8 in OKLab × 100)
und bei Protanopie, Deuteranopie, Tritanopie (≥ 6), Abstand zur Farbe für fehlende Werte (≥ 8) und den
Kontrast der hellsten Stufe zum Hintergrund. Erst wenn alles „OK“ ist, in `farben.py` eintragen;
`tests/test_farben.py` prüft alle Einträge.

Grenzen der Stufen: runde, sprechende Werte (0, 20, 40, 60, 80 %), nicht automatisch berechnete Quantile.
Ausnahme ist die Schnellanalyse, die Quintile zeigt und das in der Legende sagt.

## Analyse an Karten anbinden

In `ANALYSE` setzen:
- `kennzahl`: die Spalte, die die Farbe bestimmt,
- `stufen = Stufen(grenzen=…, farben=FARBSTUFEN[…], texte=…, keine_daten_text=…)`,
- `spalten`: was Tooltip, Tabelle und Export zeigen (`Spalte(feld, titel, art, stellen, balken)`); `art` ist `text`, `zahl`, `prozent` oder `flaeche`.

Dann zeigen die Seite **Analysen**, die Seite **Karte** und `essen analyse ID --export` die Kennzahl ohne
weiteren Code. Tooltips formatieren deutsch und maskieren HTML (`karte.kennzahl_flaechen`).

## Lesbarkeit

- Legende immer neben der Karte, mit Einheit und dem Eintrag für fehlende Werte.
- Farbe nie allein: Tooltip und Tabelle nennen die Zahl.
- Flächen mit weißen Grenzen (1 px), Hervorhebung dunkel (2,5 px).
- Titel sagt, was die Farbe bedeutet („Anteil der bebauten Fläche über 20 °C“).

## Ansehen und prüfen

Karten nie ungesehen abgeben. Mit Testdaten:

```bash
uv run essen --testdaten analyse hitze-nacht --export     # data_test/export/hitze-nacht.html
python3 .claude/skills/app-erweitern/screenshots.py        # Screenshots aller App-Seiten
```

Auf den Screenshots prüfen: Passt der Ausschnitt? Überdecken sich Beschriftungen? Stimmen Legende und
Flächenfarben überein? Ist der Testdaten-Hinweis sichtbar? Auf schmalen Bildschirmen (390 px) lesbar?
