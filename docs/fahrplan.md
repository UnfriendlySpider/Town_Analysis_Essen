# Fahrplan der Analysen

Was als Nächstes kommt, welche Daten es braucht und was noch offen ist. Reihenfolge nach Nutzen und
Datenlage. Neue Analysen nach dem Skill `neue-analyse` anlegen und hier abhaken.

## Stand

| Analyse | Status | Daten | nächster Schritt |
| --- | --- | --- | --- |
| `hitze-nacht` Nächtliche Überwärmung je Stadtteil | mit echten Daten gerechnet (10.10.2026), Kodierung belegt | Klimaanalyse Nacht (Raster LT_EXT/LT_TYP), Stadtteile | Abgleich mit der Karte des Anbieters im Klimaatlas |
| `hitze-tag` Wärmebelastung am Tag je Stadtteil | mit echten Daten gerechnet (10.10.2026) | Klimaanalyse Tag (Raster PET), Stadtteile | Abgleich mit der Karte des Anbieters |
| `versiegelung` Versiegelte Fläche je Stadtteil | mit echten Daten gerechnet (10.10.2026), stadtweit 36,5 % wie beim LANUK; Verlauf 2006–2018 aus Satellitendaten (11.10.2026, Gemeindewerte auf 0,01 Punkte getroffen) | Bodenversiegelung 2024 (0,5 m), optional Satellit 2006–2018 (20/10 m), Stadtteile | ältere Luftbild-Stände, falls das LANUK sie nachliefert (alle zwei Jahre) |
| `gruenanteil` Grünanteil je Stadtteil | mit echten Daten gerechnet (10.10.2026), Codes belegt | Landbedeckung NRW, Stadtteile | öffentlich zugängliches Grün (OSM) ergänzen |
| `laerm` Lärmbelastung je Stadtteil | mit echten Daten gerechnet und nachgerechnet (10.10.2026) | Lärmkarte Essen (8 Shapes, Straßen 2011, sonst 2016), Stadtteile | neuere Lärmkartierung für Essen finden |
| `starkregen` Überflutung bei Starkregen je Stadtteil | mit echten Daten gerechnet und nachgerechnet (10.10.2026) | Starkregengefahrenkarte Essen (3 Klassen, 2022), Stadtteile, optional Landbedeckung (Gewässer) | Gewässer abgezogen (12.10.2026, E-017): 3,0 % der Landfläche statt 3,5 % |
| `mehrfachbelastung` Mehrfachbelastung je Stadtteil | mit echten Daten gerechnet (11.10.2026), Regel in E-008 | Ergebnisse von hitze-nacht, laerm, starkregen | Luft als viertes Thema, sobald es eine Kennzahl je Stadtteil gibt |
| Einwohner (E-013) als Zusatz in `hitze-nacht`, `laerm`, `starkregen`, `mehrfachbelastung` | mit echten Daten gerechnet (11.10.2026), Lizenz und Kontrollsumme belegt | Zensus 2022, 100-m-Gitter | weitere Merkmale (Anteil ab 65 Jahren) für Betroffenheit |
| `luft-station` Luftqualität an den Messstationen | mit echten Daten gerechnet und gegengeprüft (11.10.2026) | UBA-Jahresbilanzen 2010–2025 (NO₂, PM₁₀, PM₂,₅) | Kennzahl je Stadtteil fehlt (für E-008) |
| `betroffenheit` Hitzebetroffenheit je Stadtteil | mit echten Daten gerechnet und nachgerechnet (11.10.2026), Klassen laut Methodik-Papier | Betroffenheitsanalyse (Baublöcke, Zensus 2022 + Planungshinweiskarte), Stadtteile | – |
| `hitzetage-station` Hitzetage an der Station Essen-Bredeney | mit echten Daten gerechnet und nachgerechnet (10.10.2026) | DWD Tageswerte 1935–2026 | Verlegung 1965 ist im Diagramm markiert; Trend getrennt vor und nach 1965 prüfen |
| `hitzetage-raster` Heiße Tage je Stadtteil (DWD-Raster, E-015) | mit echten Daten gerechnet und mit der Station gegengerechnet (11.10.2026) | DWD-Jahresraster heiße Tage, Sommertage (1951–2025), Jahresmittel (1881–2025), Stadtteile | Tropennächte gibt es nicht als Raster; Niederschlag (Raster `precipitation`) als Ergänzung zum Starkregen prüfen |
| `kuehlorte` Kühle Orte in der Nähe je Stadtteil | mit echten Daten gerechnet (11.10.2026), stadtweit 43,0 % der Fläche in 300 m | Kühle Orte (547 Punkte), Stadtteile, optional Zensus | Fußwege statt Luftlinie (OSM-Wegenetz); auf hitzebelastete Flächen beziehen |
| `jungbaeume` Jungbäume der Stadt je Stadtteil | mit echten Daten gerechnet (11.10.2026), 63 je km²; Verlauf nach Pflanzjahr 2008–2025 | Stadtbäume, Ebene Jungbäume (13.306), Stadtteile | Ebene „Weitere Standorte“ als eigenen Datensatz prüfen |
| `umweltzone` Umweltzone je Stadtteil | mit echten Daten gerechnet (11.10.2026), 77,0 % der Fläche | Umweltzone (3 Flächen, Stand 2024), Stadtteile | aktuellen Stand der Zone beim Anbieter prüfen |
| `planungshinweise` Handlungsbedarf bei Hitze je Stadtteil | mit echten Daten gerechnet und gegengerechnet (12.10.2026), 46,5 % der bebauten Fläche dringend | Planungshinweiskarte der Klimaanalyse NRW 2026, Stadtteile, optional Zensus | aus derselben Nachtrechnung wie hitze-nacht (r = 0,97), daher nicht in E-008 |
| `klimatope` Stadtklima nach Klimatopen je Stadtteil | mit echten Daten gerechnet (12.10.2026), 8,9 % dichte Klimatope | Klimatopkarte der Klimaanalyse NRW 2026, Stadtteile | Ausgleichsraum der Planungshinweiskarte (Bedeutung für die Kühlung) als eigenes Thema prüfen |
| `haushalte` Privathaushalte je Stadtteil | mit echten Daten gerechnet (11.10.2026), 18,3 % mit Kindern, 50,9 % Einpersonenhaushalte; Verlauf 2007–2025 | Privathaushalte nach Stadtteilen (Amt für Statistik), Stadtteile | Altersgrenze „Kinder“ beim Amt erfragen; neben Hitze und Lärm zeigen, wo viele Kinder betroffen sind |

## Oberfläche (11.10.2026)

Umgesetzt (E-014): Punktleiste „Wo steht mein Stadtteil?“, sortierte Balken je Thema, Legende mit Anzahl und
Mittel, Klickkarte, kleine Karten auf der Startseite, Streudiagramm mit vier Feldern und Heatmap, Trendlinien
und Vergleich 1961–1990, geschätzte Einwohner auf den Leseseiten, Datenviewer „Originaldaten ansehen“,
Punktebenen auf der Karte (kühle Orte, Jungbäume, Ladesäulen, Lastenrad-Stationen, Pegel).

Durchsicht der App (11.10.2026), umgesetzt: Links auf „Entwicklung über die Jahre“ nehmen das Thema mit
(`?thema=`); Randfälle dort abgefangen; „Alles vorbereiten“ ist bei Platzmangel gesperrt (`Plan.genug_platz`);
„Neu berechnen“ baut Downloads erst beim Klick und die Karte nur nach neuem Rechnen und meldet alle Fehler
lesbar. Legende, Zeitverlauf, Heatmap und Punktleiste sind im dunklen Thema lesbar. Belegter Platz, Dateilisten und
Layer sind gecacht; `Ergebnis.ansehen` liest ohne Kopie (Steckbrief, Prüfen auf vorhandene Ergebnisse).

Paket 3 (Einsteiger, 11.10.2026), umgesetzt: Meldungen nennen den nächsten Schritt mit Link; „Daten laden“ statt
„Datenkatalog“; einheitlicher Testdaten-Vermerk; Startseite ohne doppelten Hinweis und mit leerem Zustand;
Themen ohne Auswahl mit Hinweis; Schnellanalyse mit Fortschritt und gespeichertem Ergebnis; überall `?thema=`
(`?analyse=` bleibt gültig), Vergleich mit `?a=`/`?b=`; Methodik nach Thementiteln; Texte für Maus und Touch.
GDAL-Warnung zu Punkten mit vier Werten (Stadtteilgrenzen) in der App still, Höhenwerte werden beim Lesen
abgeschnitten.

Werte je Stadtbezirk (12.10.2026, E-018), umgesetzt: `essen.bezirke`, gewichtet wie der stadtweite Wert
(`Analyse.gewicht`); „Mein Stadtteil“ zeigt Bezirk und Bezirkswert je Thema, „Themen“ eine Tabelle je Bezirk.
Bezirke heißen nur „Stadtbezirk I“ bis „IX“ (keine Quelle nennt Namen). Methodik: `docs/methodik/bezirke.md`.

Klimatope und Planungshinweise (12.10.2026), umgesetzt: zwei neue Themen mit geprüften Zuordnungen (Methodik-PDFs
des LANUK, Kreuztabellen an den echten Daten), gestapelte Balken für Anteile (`Analyse.zusammensetzung`), Kasten
„Dazu passend“ bei der Hitze in der Nacht (`Analyse.verwandt`).

Offen: Bezirksnamen mit Beleg ergänzen (z. B. aus einer Veröffentlichung der Stadt); Viewer für File-Geodatabases
und RGB-Raster mit eigenen Testdaten absichern. Leaflet-Karten fangen auf dem Handy das Wischen ab (eine Geste zum Verschieben
mit zwei Fingern gibt es in Leaflet nicht eingebaut); die Karten sind dort deshalb niedriger.

Paket 5 (12.10.2026), umgesetzt: Zeitkarte per Tastatur (Tab, Enter/Leertaste) und Touch bedienbar, Werte auch
bei Fokus, `aria-label` je Stadtteil, `aria-pressed` am Abspielknopf, Schriftgrößen in rem; Texte ohne reine
Farbangaben; auf Handys niedrigere Karten (`gemeinsam.kartenhoehe`, erkannt an der Browserkennung);
`screenshots.py --breite 390` zeigt die Handyansicht mit Touch und mobiler Kennung.

Paket 6 (12.10.2026), umgesetzt: Tests für `essen.text`, Tooltip-Maskierung (E-005), Karte und Start mit
Ergebnissen; `screenshots.py` meldet Ausnahmen, Fehlermeldungen und Zeitüberschreitungen selbst (Code 1).
Paket 4 (12.10.2026), umgesetzt: Fachlogik aus den Seiten ins Paket (`schnell.stufen_fuer`,
`einordnung.einwohner_satz`, `katalog.lizenz_tabelle`/`quellen_tabelle`/`anbieter`, `laden.quellenangaben`,
`laden.einlesen_bytes`, `vorschau.stempel`, `zeitreihen.stellen`/`erstes_jahr`); gemeinsame Bausteine
`methodik_text`, `geladene_datensaetze`, `datensatz_wahl`, `jahresbalken`; Tabellen mit deutschem Zahlenformat.

## Daten erklärt (Paket 7, 11.10.2026)

Umgesetzt: Seite „Daten erklärt“ unter „Essen entdecken“. Jeder Datensatz in Worten: woher, was drin, wofür, wie
lesen; dazu „Auf einen Blick“ (Anbieter, Lizenz in einem Satz, Gebiet, Stand) und die Themen, die ihn nutzen.
Texte im Katalog (`erklaerung`), Steckbrief in `essen.datenerklaerung`, Übersicht in `docs/daten-erklaert.md`
(`essen katalog --doku`). Links von Themen, „Daten laden“ und „Originaldaten ansehen“ („Was ist das?“).

Offen: Texte nach jedem neuen Datenstand gegenlesen (Stand, Lücken); Erklärungen für neue Datensätze gleich
beim Eintragen schreiben (Skill `neue-datenquelle`).

## Zeitliche Ansicht (11.10.2026, E-016)

Umgesetzt: Karte über die Jahre mit Abspielen, Schieber und kleinen Karten je Jahrzehnt für heiße Tage, Sommertage
und Jahresmittel (seit 1951 bzw. 1881), Versiegelung (Satellit 2006–2018), Jungbäume (Pflanzjahr) und Haushalte
(2007–2025). Themen mit einem Stand sagen das.

Offen, weil Daten fehlen: Lärm (nur 2011/2016 für verschiedene Quellen, keine neuere Runde für Essen),
Klimaanalyse (ein Stand 2026; „typisch/extrem“ sind Szenarien, keine Jahre), Starkregen, Kühle Orte, Zensus
(nur 2022). Möglich mit neuen Quellen: ältere Stände der Landbedeckung NRW (Grünanteil), Zensus 2011 im Gitter,
Treibhausgasbilanz 1990–2019 (nur ganze Stadt).

## Als Nächstes

| Analyse | Frage | Daten im Katalog | Hürde |
| --- | --- | --- | --- |
| Solarausbau | Wie viel Photovoltaik je Stadtteil? | `mastr-essen` | Export mit open-mastr, dann Schnellanalyse über Punkte |

## Offene Fragen

Geklärt am 10.10.2026 (Belege im Katalog und in `katalog/zuordnungen/`): Kodierung des Nachtrasters (Temperatur in °C, Klassen nach Grenzen), `KT_R02_2` (Klimatop-Code) und `gridcode` (konstant 2), Stadtteilnummer (`STADTT`, nicht `FID`), DWD-Station 01303, Lizenz der Stadtteilgrenzen (DL-DE BY 2.0 auf der Datensatzseite), Lärm- und Starkregen-Quellen (Phase 4).

- **Lizenzen offen** (Stand 11.10.2026): Wahlergebnisse (Bundestagswahl 2025 ohne Angabe; dieselbe Stelle veröffentlicht die Europawahl 2024 im Portal unter DL-DE BY 2.0), VRR-GTFS (widersprüchlich), RVR-Klimaanalyse (CC BY-NC laut Metadaten, „Rechte bei den Kommunen“ laut Dienst), KoMonitor, nextbike NRW. Geklärt: Zensus-Gitter (DL-DE BY 2.0 laut Datensatzbeschreibung), Sensor.Community (ODbL für die Datenbank, DbCL 1.0 für die Inhalte laut Fußzeile).
- **Lärm:** Die städtischen Karten sind von 2011 (Straße) und 2016 (Schiene, Ruhrbahn, Industrie). Gibt es neuere Runden für Essen?

## Vor einer Veröffentlichung

Das Projekt ist privat (E-001). Soll später etwas öffentlich werden, vorher:

1. Lizenzen aller verwendeten Datensätze klären, besonders `pruefen`, `gemischt`, `widerspruechlich` und `cc-by-nc-4.0` (Skill `lizenz-pruefen`).
2. Quellenangaben vollständig und sichtbar anbringen, bei bearbeiteten Daten mit „Daten geändert“.
3. Methodik und Grenzen jeder Kennzahl öffentlich verständlich beschreiben (docs/methodik/).
4. Rangfolgen von Stadtteilen nur mit Einordnung zeigen; Fläche nicht als Bevölkerung ausgeben.
5. Keine Testdaten, keine Daten zu einzelnen Personen oder Adressen.
6. Eine statische Fassung ohne Server prüfen (E-004), statt die lokale App ins Netz zu stellen.

Der ausführliche Plan dazu steht im Projektplan „Umwelt-Dashboard Essen“, Abschnitt „Später: vor einer Veröffentlichung“.
