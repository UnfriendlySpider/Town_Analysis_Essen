---
name: neue-analyse
description: Legt eine neue Analyse an, etwa eine Kennzahl je Stadtteil, je Messstation oder für die ganze Stadt, mit Modul, Registry, Tests mit erfundenen Daten, Methodik-Seite und Anbindung an App und Kommandozeile. Verwenden, wenn eine neue Auswertung, Kennzahl oder Karte zu einem Thema entstehen soll.
---

# Neue Analyse anlegen

Eine Analyse ist ein Modul in `src/essen/analysen/` mit einer Konstante `ANALYSE`. Sie liest nur geladene
Daten, rechnet und gibt ein `Ergebnis` zurück. Speichern, App, Kommandozeile und Export kommen vom Rahmen.
Vorbilder: `hitze_nacht.py` (Raster je Stadtteil), `hitzetage_station.py` (Zeitreihe einer Station),
`schnell.py` (Vektor je Stadtteil).

## 1. Vorher klären

- **Frage** in einem Satz, die die Kennzahl beantwortet („Welcher Anteil … ?“).
- **Daten:** stehen alle im Katalog? Sonst zuerst Skill `neue-datenquelle`. Sind sie inspiziert? Sonst Skill `daten-inspizieren`.
- **Raumbezug:** `stadtteil` (Tabelle je Stadtteil mit Geometrie), `station` oder `stadt`.
- **Methode:** Was wird gezählt, worauf bezogen, ab welcher Mindest-Bezugsgröße ist ein Wert belastbar? Fläche ist nicht Bevölkerung (E-007).

## 2. Modul anlegen

Vorlage kopieren und anpassen:

```bash
cp .claude/skills/neue-analyse/vorlage_analyse.py src/essen/analysen/MEIN_THEMA.py
cp .claude/skills/neue-analyse/vorlage_test.py tests/test_MEIN_THEMA.py
```

In `src/essen/analysen/__init__.py` importieren und in `ALLE` eintragen. Bausteine:

| Baustein | Wofür |
| --- | --- |
| `geo.lade_stadtteile(katalog)` | 50 Stadtteile mit `gebiet_id`, `name`, `nummer`, `flaeche_ha` in EPSG:25832 |
| `geo.vektordatei(id)`, `geo.lies_im_stadtgebiet(pfad, layer=…)` | Vektordaten im Stadtgebiet lesen, ZIPs werden entpackt |
| `laden.entpackt(id)`, `laden.dateien(id, "*.zip")` | Dateien eines Datensatzes |
| `kennzahlen.flaechen_nach_klasse(…)` | Fläche je Gebiet und Klasse aus Vektorflächen |
| `kennzahlen.flaechen_nach_klasse_raster(…)` | dasselbe aus einem Klassenraster |
| `kennzahlen.anteile`, `mindestbezug`, `gewichtetes_mittel` | Anteile, Mindestfläche, stadtweiter Wert |
| `kennzahlen.punkte_je_gebiet`, `flaechenanteil_je_gebiet`, `laenge_je_gebiet` | Zählungen |
| `DatenFehlen([ids])` | wenn Daten fehlen; nennt den Befehl zum Laden |

Regeln:
- Keine URLs, keine Downloads, keine Streamlit-Aufrufe in der Analyse.
- Zwischenstände über `kontext.melde("…")` mitteilen.
- Alles, was die Deutung einschränkt, in `hinweise` des Ergebnisses schreiben.
- Spaltennamen mit Einheit (`_ha`, `_pct`), Werte runden (eine Nachkommastelle).
- Für Karten `stufen` setzen: geprüfte Farbstufen verwenden (Skill `karte-gestalten`).

## 3. Testen

- Tests laufen nur mit erfundenen Daten. Entweder die Fixtures `mit_testdaten` und `kopie_testdaten` aus `tests/conftest.py` nutzen oder im Test kleine Daten mit bekannter Lösung bauen (Rechtecke, bekannte Flächen).
- Mindestens: richtige Werte für einen Fall mit bekannter Lösung, Verhalten bei fehlenden Daten (`DatenFehlen`), Mindestbezug.
- Braucht die Analyse neue Testdaten im Format der echten Dateien, `src/essen/testdaten.py` erweitern und klar als erfunden kennzeichnen.

```bash
uv run pytest tests/test_MEIN_THEMA.py
uv run pytest                      # alles, auch die App-Rauchtests
uv run essen --testdaten analyse MEINE-ID --export
```

## 4. Dokumentieren

- `docs/methodik/MEINE-ID.md` nach dem Muster von `hitze-nacht.md`: Frage, Daten, Rechenweg, Grenzen, Ergebnisdateien. In `ANALYSE.methodik` eintragen.
- Datensätze im Katalog: `analysen: [MEINE-ID]` ergänzen, dann `uv run essen katalog --doku`.
- `docs/fahrplan.md` aktualisieren.
- **Erklärfelder in `ANALYSE` (Pflicht, Test `test_jede_analyse_ist_erklaert`):** `thema_titel` (Name im Menü), `kurz` (ein Satz ohne Fachwörter), `richtung` (`hoch_schlecht`, `hoch_gut` oder `neutral`), `lesehilfe` (2–3 Sätze: so lesen Sie Karte und Zahl), `grenzen_kurz` (höchstens drei Punkte: was die Zahl nicht sagt). Parameter brauchen `hilfe`; Wahlwerte `beschriftungen`; selten nötige Parameter `selten=True`. Neue Fachwörter in `essen/begriffe.py` erklären und in `hilfetexte.THEMA_BEGRIFFE` dem Thema zuordnen.

## 5. In der App ansehen

`uv run essen app --testdaten`, Seite **Analysen**: Daten, Einstellungen (aus `parameter`), Berechnen,
Karte (bei `stufen` und Geometrie), Tabelle (aus `spalten`), Downloads. Screenshots nach Skill `app-erweitern`.
