---
name: lizenz-pruefen
description: Prüft vor einer Weitergabe, einem Export oder einer Veröffentlichung die Lizenzen aller verwendeten Daten und erzeugt korrekte Quellenangaben. Verwenden, wenn Ergebnisse geteilt, als Datei oder Seite weitergegeben oder veröffentlicht werden sollen, oder wenn eine Lizenz unklar ist.
---

# Lizenzen prüfen und Quellen angeben

Für das private Arbeiten auf dem eigenen Rechner gelten keine Lizenzpflichten. Sie greifen, sobald etwas
das Haus verlässt: eine exportierte HTML-Seite, eine CSV an Bekannte, ein Screenshot in sozialen Medien,
eine Veröffentlichung. Diese Anleitung ersetzt keine Rechtsberatung.

## 1. Welche Daten stecken drin?

- Jedes Ergebnis nennt seine Datensätze: `data/processed/ANALYSE/ergebnis.json`, Feld `quellen`.
- Dazu immer die Hintergrundkarte (`basemap-de`, CC BY 4.0) bei Karten.
- Für jeden Datensatz: `uv run essen info ID` zeigt Lizenz und Quellenangabe.

## 2. Ampel je Datensatz

| Lizenz im Katalog | Weitergabe | Pflicht |
| --- | --- | --- |
| `dl-de-zero-2.0`, `cc0-1.0` | ja | keine; Quelle trotzdem nennen |
| `dl-de-by-2.0` | ja | Bereitsteller, Lizenz mit Link, Verweis auf den Datensatz, „Daten geändert“ bei Bearbeitung |
| `cc-by-4.0` | ja | Urheber, Lizenz mit Link, Hinweis auf Änderungen |
| `cc-by-sa-4.0`, `odbl-1.0` | ja | wie BY, abgeleitete Daten unter derselben Lizenz |
| `cc-by-nc-4.0` | nur nicht kommerziell | wie BY; keine Werbung, kein Verkauf, kein bezahltes Angebot |
| `pruefen`, `gemischt`, `widerspruechlich`, `nutzungsbedingungen` | erst klären | beim Anbieter nachfragen oder die Lizenz der einzelnen Ressource lesen |

Besonderheiten aus dem Katalog: Starkregenkarte des BKG mit Jahr des letzten Datenbezugs, Landbedeckung NRW
mit Copernicus-Vermerk, Marktstammdatenregister mit Pflichtvermerk der Bundesnetzagentur, OpenStreetMap mit
„© OpenStreetMap-Mitwirkende“.

## 3. Quellenangaben erzeugen

- Einzeln: `uv run essen info ID` (letzte Zeile).
- Alle geladenen Daten: App, Seite **Methodik und Lizenzen**, Reiter **Quellenangaben**.
- Im Code: `essen.katalog.quellenangabe(katalog, ds, abgerufen, geaendert=True)`.
- Exportseiten (`essen analyse ID --export`) schreiben die Angaben automatisch in die Fußzeile. Vor dem Weitergeben die Fußzeile lesen.

## 4. Vor einer Veröffentlichung zusätzlich

- Testdaten? Die Seite trägt dann den Hinweis „Testlauf mit erfundenen Testdaten“ und darf so nicht als Ergebnis gezeigt werden.
- Modellwerte als Modellwerte benennen, Grenzen der Methode nennen (docs/methodik/).
- Datenschutz: keine Daten zu einzelnen Personen oder Adressen veröffentlichen.
- Ungeklärte Lizenzen im Katalog als `pruefen` lassen, bis eine schriftliche Antwort vorliegt; die Antwort als Hinweis eintragen.
- Die Liste in docs/fahrplan.md, Abschnitt „Vor einer Veröffentlichung“, abarbeiten.
