# Entscheidungen

Kurze Begründungen für Festlegungen, die man später nicht aus Versehen umwerfen soll. Neue Entscheidungen
unten anhängen, alte nicht löschen, sondern als ersetzt markieren.

## E-001 Privat und lokal

Das Projekt ist privat. Die App hört nur auf `localhost` (in `.streamlit/config.toml` und beim Start durch
`essen app` gesetzt), Streamlits Nutzungsstatistik ist aus. Eine Veröffentlichung ist ein eigener späterer
Schritt mit Lizenzprüfung (Skill `lizenz-pruefen`, docs/fahrplan.md, Abschnitt „Vor einer Veröffentlichung“).

## E-002 Keine Daten im Repository

Das Repository enthält Code, Katalog und Doku, aber keine geladenen Daten. Jede Person lädt selbst aus der
Originalquelle, per Knopf in der App oder `essen laden`. Gründe: Die Daten bleiben aktuell, es gibt keine
Weitergabe im Sinne der Lizenzen, und das Repository bleibt klein. Jeder Abruf wird mit Adresse, Zeit,
Größe, Prüfsumme und Lizenz protokolliert.

## E-003 Der Katalog ist die einzige Quelle für Adressen und Lizenzen

Adressen, Lizenzen und Download-Angaben stehen nur in `katalog/*.yaml`. Code liest sie von dort.
`docs/datenquellen.md` wird daraus erzeugt (`essen katalog --doku`); ein Test prüft, dass sie aktuell ist.
Unbestätigte Angaben bekommen den Status `ungeprueft`, nie einen geratenen Status `geprueft`.

## E-004 Streamlit als Oberfläche, Logik im Paket

Stand der Prüfung: Oktober 2026, Versionen von PyPI.

| Framework | Version | Stärken | Schwächen | wann es besser wäre |
| --- | --- | --- | --- | --- |
| **Streamlit** (gewählt) | 1.65 | schnell gebaut, reines Python, Seiten, Tabellen, Fortschritt, Downloads, Agenten kennen es gut | jede Eingabe lässt das Skript neu laufen, Layout begrenzt | – |
| NiceGUI | 3.18 | ereignisgesteuert, echte Hintergrundaufgaben, eingebaute Leaflet-Karte | mehr Code für Tabellen und Diagramme | wenn die App sich wie ein Programm anfühlen soll, mit parallelen Downloads |
| Shiny for Python | 1.8 | reaktiv, rechnet nur Betroffenes neu | kleinere Gemeinschaft, Karten über Widgets | bei vielen voneinander abhängigen Filtern |
| Panel (HoloViz) | 1.9 | stärkste Werkzeuge für große Geodaten (Datashader, GeoViews) | steile Lernkurve | bei Rasterdaten mit Millionen Zellen im Browser |
| Dash | 4.4 | ausgereift für Produktiv-Dashboards | viel Callback-Code | bei einem öffentlichen Dauerbetrieb |
| marimo | 0.25 | reaktive Notebooks als .py-Dateien, als App startbar | eher Notizbuch als App | als Ergänzung, um neue Analysen zu erkunden |
| Gradio, Reflex, Taipy | 6.30, 0.10, 4.1 | Demos bzw. Full-Stack | passen nicht zum Zweck oder sind schwerer | – |
| statisch (Observable Framework, Evidence, Quarto) | – | kein Server, leicht zu hosten | kein „Jetzt laden“, keine Rechnung auf Abruf | für eine spätere öffentliche Nur-Lese-Fassung |

Weil Oberfläche und Logik getrennt sind (`docs/architektur.md`), kostet ein Wechsel nur die Dateien in
`src/essen/app/`. Die Analysen, der Katalog und die Kommandozeile bleiben.

## E-005 Karten: folium in der App, MapLibre für Export-Seiten

In der App zeichnet folium (Leaflet) die Karten. Damit lassen sich WMS-Dienste der Anbieter direkt
einblenden. folium lädt nur Leaflet nach, nicht jQuery oder Bootstrap (`karte.neue_karte`). Eigenständige
Seiten zum Weitergeben baut `bericht.py` mit MapLibre GL, wie im ersten Durchstich. Hintergrund ist immer
basemap.de grau (CC BY 4.0). Werte in Tooltips werden maskiert.

## E-006 Flächen und Raster

Flächen werden in EPSG:25832 gerechnet. Rasterzellen zählen zu dem Gebiet, in dem ihr Mittelpunkt liegt.
Anteile werden erst ab einer Mindest-Bezugsfläche ausgewiesen (Hitze: 5 ha bebaut), weil sie sonst von
wenigen Zellen abhängen.

## E-007 Fläche zuerst, Menschen später

Die ersten Kennzahlen zählen Fläche. Eine Gewichtung mit dem Zensus-2022-Gitter folgt, wenn die Gitterdaten
geladen und geprüft sind (docs/fahrplan.md). Seit 11.10.2026 als Zusatz umgesetzt, siehe E-013.

## E-008 Mehrfachbelastung durch Zählen

Wenn mehrere Themen zusammengefasst werden, zählt die Mehrfachbelastung, in wie vielen Themen ein Gebiet in
der schlechtesten Klasse liegt (Vorgehen wie im Berliner Umweltgerechtigkeitsatlas). Keine Gewichtung der
Themen gegeneinander, weil dafür keine belastbare Grundlage besteht.

Festgelegt am 11.10.2026 (mit dem Menschen abgestimmt):

- **Themen:** Hitze in der Nacht (`hitze-nacht`), Lärm (`laerm`), Starkregen (`starkregen`); Luft kommt dazu,
  sobald es eine Kennzahl je Stadtteil gibt. Nicht gezählt werden Hitze am Tag, Versiegelung und Grünanteil:
  Über die 50 Stadtteile korrelieren sie mit Hitze in der Nacht zu 0,80, 0,91 und −0,92 (Versiegelung und Grün
  untereinander −0,97). Sie messen denselben Block „dichte Bebauung“ und würden ihn mehrfach zählen.
- **Schlechteste Klasse:** das oberste Fünftel der Stadtteile je Thema (bei 50 Stadtteilen die 10 mit den
  höchsten Werten, Gleichstand an der Grenze zählt mit). Das ist ein Vergleich innerhalb Essens, kein Grenzwert,
  und wird so beschriftet.
- Gezählt werden die Kennzahlen mit den Standard-Einstellungen der Analysen.

## E-009 Rasterkodierung nie stillschweigend raten

Ist unklar, wie ein Raster Klassen kodiert, bricht die Analyse mit einer Vorlage ab. Geprüfte Zuordnungen
liegen in `katalog/zuordnungen/` mit `geprueft: true`. Automatische Erkennung über Legenden ist erlaubt,
steht aber immer als Hinweis im Ergebnis.

## E-010 Deutsch

Code, Oberfläche und Doku sind deutsch. Bezeichner ohne Umlaute, Texte mit Umlauten.

## E-011 Erfundene Testdaten

Tests und Cloud-Sitzungen ohne Zugang zu den Portalen nutzen erfundene Testdaten im Format der echten
Dateien (`essen testdaten`). Sie liegen in einem eigenen Ordner, sind markiert, und App, Berichte und
Export-Seiten zeigen das deutlich an.

## E-012 uv und Python 3.12

uv verwaltet Python und Pakete (`uv sync`), das Lockfile hält die Versionen fest. Python 3.12, weil
rasterio, pyproj und numpy in den aktuellen Versionen mindestens 3.12 verlangen.

## E-013 Einwohner als Zusatz zur Fläche

Festgelegt am 11.10.2026 (mit dem Menschen abgestimmt). Löst den Teil „Menschen später“ von E-007 ein.

- Hauptkennzahl, Karte und Rangfolge bleiben flächenbezogen. Liegt das Zensus-2022-Gitter vor
  (`zensus-2022-gitter`), ergänzen die Analysen `einwohner`, `einwohner_belastet` und `anteil_einwohner_pct`.
- Verfahren (`essen.einwohner`): 100-m-Gitter, Einwohner gleichmäßig über die Zelle verteilt; eine Zelle gehört
  zu dem Stadtteil, in dem ihr Mittelpunkt liegt; belastet ist der Anteil der Zellfläche in der belasteten Fläche
  (bei Rastern: Anteil der Rasterzellen). Ein Anteil je Stadtteil erst ab 200 Einwohnern.
- Die Zahlen heißen „geschätzt“. Kontrollsumme Essen: 570.632 im Gitter gegen 571.039 laut Zensus 2022.
- Die Mehrfachbelastung bleibt nach E-008 flächenbezogen und nennt zusätzlich die Einwohner der Stadtteile.

## E-014 Diagramme, Klickkarte und Datenviewer

Festgelegt am 11.10.2026 (mit dem Menschen abgestimmt: Brainstorming „Visualisierung und Datenviewer“).

- **Diagramme mit altair** (`essen.diagramme`), nicht plotly oder matplotlib: altair kommt mit Streamlit, ist
  jetzt direkte Abhängigkeit. Farben aus den geprüften Stufen (`farben.py`), Zahlen deutsch über `locale`.
  Flächen für altair (`mini_karte`) als GeoJSON-Werte übergeben, weil Streamlit GeoDataFrames in Tabellen
  umwandelt und die Geometrie verliert.
- **Klickkarte mit streamlit-folium** (`app.gemeinsam.klickkarte`): Ein Klick auf einen Stadtteil wählt ihn
  (Eigenschaft `gebiet_id` im GeoJSON). Das Paket lädt Leaflet über dieselbe Adresse wie bisher, keine neuen
  fremden Skripte. Karten ohne Klick bleiben bei `st.iframe`.
- **Datenviewer liest nur Ausschnitte** (`essen.vorschau`): höchstens 2.000 Objekte im Rechteck um Essen,
  Rasterbilder höchstens 800.000 Bildpunkte (nächster Nachbar, in Web-Mercator verzerrungsfrei für Leaflet),
  CSV höchstens 2.000 Zeilen, JSON höchstens 5 MB. ZIP-Archive werden nicht entpackt, sondern über `/vsizip/`
  gelesen. Raster ohne Farbtabelle und ohne passende Legende (unter 90 % Abdeckung) bekommen eine neutrale
  Skala mit Hinweis; Bedeutungen werden nicht geraten (E-009).
- **Punktebenen** (`essen.punktebenen`) zeigen Felder so, wie sie geliefert werden, nur umbenannt.

## E-015 Heiße Tage je Stadtteil aus den DWD-Jahresrastern

Festgelegt am 11.10.2026 (mit dem Menschen abgestimmt: Vergleichswerte über die Jahre je Stadtteil statt nur Bredeney).

- Bredeney ist die einzige Klimastation des DWD in Essen. Reihen je Stadtteil kommen deshalb aus den
  Jahresrastern des DWD (1 km, seit 1951; Jahresmittel seit 1881), flächengewichtet je Stadtteil
  (`hitzetage-raster`, Methodik `docs/methodik/hitzetage-raster.md`).
- Die Werte heißen überall **Modellwerte**. Die städtische Wärmeinsel ist darin laut DWD nicht enthalten; die
  App sagt das neben jedem Diagramm. Kleinräumige Hitze bleibt Sache der Klimaanalyse (`hitze-tag`, `hitze-nacht`).
- Nicht Teil der Mehrfachbelastung (E-008): Die Stadtteile unterscheiden sich kaum, und Hitze ist dort schon über
  `hitze-nacht` enthalten.
- Neue Download-Option `verzeichnis` mit `alle: true` lädt alle passenden Dateien eines Ordners (eine Datei je Jahr).


## E-016 Zeitliche Ansicht: Karten über die Jahre

Festgelegt am 11.10.2026 (mit dem Menschen abgestimmt: Jahrzehnt-Karten und Zeitschieber, dazu neue Quellen mit
mehreren Ständen).

- **Wo es einen Verlauf gibt, zeigt die App ihn als Karte**: auf der Seite „Themen“ über den Umschalter „Heute |
  Verlauf über die Jahre“, bei den heißen Tagen auch auf „Entwicklung über die Jahre“. Eine Analyse meldet ihre
  Werte über `Analyse.zeitachse` (`Zeitwert`) an. Grundlage sind die `jahreswerte` des Ergebnisses.
- **Gleiche Farbstufen für alle Zeitpunkte**, je Zeitwert fest gewählt, damit Farben zwischen den Jahren
  vergleichbar sind. Die Stufen der Ansicht „Heute“ gelten dafür nicht unbedingt.
- **Jahrzehnt-Mittel als Hauptansicht** bei langen Reihen (ab 30 Jahren), weil einzelne Jahre stark schwanken.
  Angebrochene Jahrzehnte heißen „2020–2025“, Jahrzehnte mit weniger als drei Jahren fallen weg. Bestandszahlen
  (aufsummiert, z. B. gepflanzte Bäume) und Reihen mit wenigen Ständen zeigen nur Einzeljahre (`jahrzehnte=False`).
- **Abspielen im Browser** (`app/zeitkarte.py`, Streamlit-Komponente v2): Die Flächen gehen einmal als SVG-Pfade
  in den Browser (EPSG:25832, vereinfacht auf 30 m, 40–120 KB), umgefärbt wird dort. Keine Kartenkacheln, keine
  fremden Skripte, kein Neuladen je Bild. Farben der Oberfläche kommen aus dem Thema (hell und dunkel).
- **Methodenbrüche bleiben sichtbar**: Reihen aus anderer Quelle werden nicht an die Hauptkennzahl angehängt. Die
  Versiegelung 2006 bis 2018 (Satellit, mittlerer Versiegelungsgrad) steht getrennt von 2024 (Luftbild, ja/nein),
  der Auflösungswechsel 2018 steht unter der Karte. Bei den Jungbäumen steht dabei, dass gefällte Bäume fehlen.
- Themen mit nur einem Datenstand sagen das („nur ein Datenstand (2024)“), statt einen Verlauf vorzutäuschen.
- **Zwischenspeicher für gespeicherte Ergebnisse** (`Ergebnis.laden`): Ergebnisse bleiben im Speicher, bis sich
  Inode, Zeit oder Größe einer ihrer Dateien ändert, und werden als Kopie herausgegeben. Das Paket bleibt frei von
  Streamlit. Die Seiten laden damit 4- bis 20-mal schneller (Mein Stadtteil 6,0 → 0,7 s).


## E-017 Starkregen: Gewässer abziehen, Bezug Landfläche

Festgelegt am 12.10.2026 (mit dem Menschen abgestimmt: Fahrplanpunkt „Gewässer mit der Landbedeckung abziehen“).

- Die Starkregengefahrenkarte der Stadt stuft Bäche, Teiche, Ruhr und Baldeneysee als tiefe Wasserflächen ein.
  Das ist kein Einstau an Land und hob die Stadtteile an der Ruhr an (Abgleich: 124 von 730 ha ab 25 cm).
- **Standard:** Die Gewässer der Landbedeckung NRW (Gruppe `wasser` der geprüften Zuordnung, Layer
  `lb_binnengewaesser`) werden von den Flächen ab 5 und ab 25 cm abgezogen. Bezug der Anteile ist die
  **Landfläche** des Stadtteils (Fläche ohne Gewässer), damit ein Stadtteil mit viel Wasser nicht künstlich
  kleinere Anteile bekommt. Auch die geschätzten Einwohner (E-013) beziehen sich auf die tiefe Fläche an Land.
- Die Landbedeckung ist **optional**: Fehlt sie, rechnet die Analyse wie vorher mit der ganzen Fläche und sagt das
  im Hinweis. Mit `-p gewaesser=mitzaehlen` lässt sich die alte Rechnung bewusst wählen.
- Die Mehrfachbelastung (E-008) übernimmt den neuen Standard; ihre Rangfolge kann sich dadurch an der Ruhr ändern.
  Die Referenzwerte werden nach Prüfung neu festgeschrieben.


## E-018 Werte je Stadtbezirk

Festgelegt am 12.10.2026 (mit dem Menschen abgestimmt: Fahrplanpunkt „Werte je Stadtbezirk“).

- **Gerechnet wie der Wert für ganz Essen:** Jede Analyse nennt ihr Gewicht (`Analyse.gewicht`), mit dem sie auch
  den stadtweiten Wert bildet (Bezugsfläche, bei Haushalten die Zahl der Haushalte). Der Bezirkswert ist das
  damit gewichtete Mittel der Stadtteile, bei Anteilen also Summe der belasteten Fläche durch Summe der
  Bezugsfläche – nicht das einfache Mittel der Prozente. Gegenprobe: über alle Bezirke ergibt sich wieder der
  stadtweite Wert.
- **Ohne Gewicht keine Bezirkswerte:** Mehrfachbelastung (Zählung von Themen, E-008) und Stationen.
- **Zuordnung** aus der Stadtteildatei (Feld `STADTBEZ`, im Katalog `felder.bezirk`), nicht aus einer
  Verschneidung mit den Bezirksgrenzen. Fehlt das Feld, gibt es keine Bezirkswerte.
- **Namen nur als Nummer** („Stadtbezirk I“ bis „IX“): Keine der Quellen nennt die Bezirksnamen; sie werden nicht
  ergänzt, solange es dafür keinen Beleg gibt.
- Nur Ergebnisse, kein neues Rechnen: `essen.bezirke` liest gespeicherte Tabellen der Stadtteile.
