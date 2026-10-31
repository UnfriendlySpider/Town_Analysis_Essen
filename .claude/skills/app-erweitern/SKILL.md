---
name: app-erweitern
description: Erweitert die lokale Streamlit-App (src/essen/app/) um Seiten, Bedienelemente oder Anzeigen, ohne Logik in die Oberfläche zu verlagern, und prüft das Ergebnis mit AppTest und Screenshots. Verwenden bei jeder Änderung an der App, bei neuen Seiten oder wenn die App anders aussehen oder sich anders verhalten soll.
---

# Die App erweitern

Die App ist eine dünne Schicht über dem Paket (docs/architektur.md). Sie zeigt an, fragt ab und ruft
Funktionen aus `essen` auf. Was gerechnet, geladen oder gespeichert wird, gehört ins Paket, damit es auch
über die Kommandozeile und in Tests funktioniert.

## Aufbau

| Datei | Inhalt |
| --- | --- |
| `src/essen/app/start.py` | Seitenkonfiguration und Navigation (`st.navigation`) |
| `src/essen/app/gemeinsam.py` | Katalog (gecacht), Kopf mit Testdaten-Hinweis, Abzeichen, **Download-Knopf**, Datenzeile |
| `src/essen/app/seiten/*.py` | eine Datei je Seite |
| `.streamlit/config.toml` | nur localhost, keine Telemetrie, Thema hell und dunkel ([theme.light], [theme.dark]) |

Start immer über `uv run essen app` (setzt Adresse und Telemetrie zusätzlich). Mit `--testdaten` arbeitet
die App mit `data_test/`.

## Neue Seite

1. Datei `src/essen/app/seiten/NAME.py` anlegen. Oben `kopf("Titel", "Ein Satz, was die Seite tut")` aus `gemeinsam`.
2. In `start.py` als `st.Page("seiten/NAME.py", title=…, icon=":material/…:")` in die passende Gruppe eintragen.
3. Daten über Paketfunktionen holen: `katalog()`, `laden.vorhanden()`, `Ergebnis.laden()`, `analysen.ausfuehren()`.
4. Für Datensätze immer `download_knopf(k, ds, zusatz="NAME")` oder `daten_zeile(k, id)` nutzen, nicht selbst laden.
5. Karten mit `essen.karte` bauen und mit `st.iframe(karte.als_html(m), height=…)` einbetten (nicht `components.html`, das ist veraltet). Soll ein Klick einen Stadtteil wählen: `klickkarte(m, hoehe, schluessel)` und `neu_gewaehlt(…)` aus `gemeinsam` (E-014).
6. Diagramme mit `essen.diagramme` (altair) bauen; Flächen für altair als GeoJSON-Werte übergeben (`mini_karte`).

## Regeln

- Jeder Knopf und jedes Eingabefeld braucht einen eindeutigen `key`, wenn es mehrfach vorkommt (z. B. `f"laden-{ds.id}-{zusatz}"`).
- Lange Vorgänge mit `st.status` oder `st.progress` anzeigen; danach `st.rerun()`, damit der neue Stand erscheint.
- Fehler aus dem Paket (`DownloadFehler`, `DatenFehlen`, `ZuordnungFehlt`) mit `st.error(str(fehler))` zeigen; die Meldungen sind schon für Menschen geschrieben.
- Texte deutsch, kurz, ohne Fachjargon der Oberfläche. Zahlen in Tabellen mit `format="localized"`.
- HTML nur aus eigenen, maskierten Werten zusammensetzen. `st.iframe` mit HTML-Text führt Skripte aus.
- Keine neuen fremden Skripte oder Tracker. Netzwerkzugriffe nur über `essen.laden` oder Kartendienste aus dem Katalog.
- Die App bleibt auf `localhost`. `server.address` nicht ändern.
- **Zwei Bereiche:** Seiten unter „Essen entdecken“ sind für Menschen ohne Vorwissen. Sie lesen nur gespeicherte Ergebnisse, laden und rechnen nichts (fehlt etwas: `noch_nicht_vorbereitet()`), zeigen keine Pfade, YAML-Namen oder Kennungen und erklären Fachwörter (`essen.begriffe`). Laden, Rechnen und Prüfen gehören in die „Werkstatt“.
- **Jede Seite** beginnt mit `kopf("Titel")` und `seitenhilfe("schluessel")`; die Texte stehen in `essen.hilfetexte` (Anrede „Sie“). Test `test_hilfe_auf_jeder_seite`.
- Zahlen für Menschen einordnen: `essen.einordnung` (berücksichtigt, ob hoch gut oder schlecht ist), bei Themen `lesehilfe(analyse)` und `grenzen_kasten(analyse, hinweise)` aus `gemeinsam.py`.

## Prüfen

```bash
uv run pytest tests/test_cli_und_app.py        # jede Seite läuft ohne Ausnahme (AppTest)
uv run python .claude/skills/app-erweitern/screenshots.py          # Screenshots nach data_test/screenshots/
uv run python .claude/skills/app-erweitern/screenshots.py --echt   # mit echten Daten nach data/screenshots/
WARTEN_MS=8000 uv run python .claude/skills/app-erweitern/screenshots.py --seiten stadtteil   # länger warten
uv run python .claude/skills/app-erweitern/screenshots.py --dunkel # Dunkelmodus, Bilder *-dunkel.png
```

`screenshots.py` startet die App mit Testdaten auf einem freien Port, ruft jede Seite auf und speichert
Bilder. Es braucht Playwright mit Chromium (in Cloud-Sitzungen meist vorinstalliert). Sind CDN und
basemap.de gesperrt, hängt es Leaflet aus einer lokalen Kopie ein (`npm pack leaflet@1.9.3`) und ersetzt die
Kacheln durch eine graue Fläche. Die Bilder ansehen: abgeschnittene Spalten, Umbrüche, englische
Platzhalter, fehlende Testdaten-Hinweise.

Klickpfade lassen sich ohne Browser mit `streamlit.testing.v1.AppTest` prüfen: Einstieg `start.py` laden,
`at.switch_page("seiten/NAME.py")`, Knöpfe über `at.button` finden und `.click().run()`.
