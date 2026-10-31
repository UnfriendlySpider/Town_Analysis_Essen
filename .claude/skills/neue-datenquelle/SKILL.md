---
name: neue-datenquelle
description: Nimmt eine neue Datenquelle oder einen neuen Datensatz für Essen in den Katalog auf (katalog/*.yaml), prüft Adresse, Download und Lizenz und erzeugt die Doku neu. Verwenden, wenn neue offene Daten gefunden, Angaben korrigiert oder Download-Adressen bestätigt werden sollen.
---

# Neue Datenquelle oder neuen Datensatz aufnehmen

Der Katalog ist die einzige Stelle für Adressen und Lizenzen (docs/entscheidungen.md, E-003). Felder und
erlaubte Werte stehen in `docs/katalog.md`.

## 1. Einordnen

- **Quelle** (`katalog/quellen.yaml`): ein Anbieter, Portal oder eine Schnittstelle, z. B. „LANUK“ oder „Open-Data-Portal Stadt Essen“. Gibt es sie schon? `grep -n "id:" katalog/quellen.yaml`.
- **Datensatz** (`katalog/datensaetze.yaml`): eine konkrete Datei oder Abfrage, die man laden und auswerten kann. Verweist mit `quelle:` auf eine Quelle.
- Erst die Quelle anlegen, dann den Datensatz.

## 2. Angaben recherchieren

Für jeden Datensatz klären und belegen:

| Frage | Woher |
| --- | --- |
| Seite des Datensatzes | Portal des Anbieters, nicht ein Suchergebnis |
| Download | Datei-URL, Download-Ordner (OpenGeodata.NRW: `index.json` im Ordner), WFS mit Typname oder API |
| Lizenz | Angabe auf der Datensatzseite oder in den Metadaten; Wortlaut der Pflichtangabe übernehmen |
| Format, Raumbezug, Stand, Größe | Datensatzseite, `index.json` (`size` in Bytes) |

Regeln:
- Nie URLs, Dateinamen oder Lizenzen raten. Was nicht belegt ist, kommt als Hinweis in `hinweise`, nicht in die Felder.
- OpenGeodata.NRW: lieber `art: verzeichnis` mit `ordner` und `muster` als eine feste Datei-URL, weil sich Dateinamen mit jedem Stand ändern. Das Muster so eng wie nötig (`"*Nacht*GeoPackage*.zip"`).
- WFS: Typnamen mit `uv run essen dienst ID` abfragen (dafür den Dienst zuerst unter `dienste` eintragen).
- Kartendienste (WMS) zusätzlich unter `dienste` eintragen, dann erscheinen sie auf der Kartenseite der App.

## 3. Eintragen

Vorlage für einen Datensatz:

```yaml
- id: kurze-kennung                # Kleinbuchstaben, Ziffern, Bindestriche
  titel: Lesbarer Titel
  quelle: id-der-quelle
  bereitsteller: Wer in der Quellenangabe steht
  themen: [gruen]                  # erstes Thema = Gruppe in Übersichten
  beschreibung: Ein bis drei Sätze, was drin ist.
  format: GeoPackage im ZIP
  raumbezug: NRW, 10-m-Raster
  stand: 2026
  lizenz: dl-de-by-2.0
  namensnennung: "Wortlaut, falls vorgeschrieben, {jahr} wird ersetzt"
  seite: https://…
  download:
    art: verzeichnis               # datei | verzeichnis | wfs | api | manuell | keiner
    ordner: https://…/             # mit / am Ende
    muster: "*.zip"
    groesse_mb: 120
  status: ungeprueft               # geprueft nur mit Beleg
  geprueft: ""                     # bei geprueft: "JJJJ-MM-TT: wie geprüft"
  hinweise:
    - Offene Fragen und Besonderheiten
  erklaerung:                      # für „Daten erklärt“: einfache Sprache, Anrede „Sie“, nur Belegtes
    herkunft: "Wer erhebt die Daten, wie entstehen sie, wie aktuell?"
    inhalt: "Was steht drin, in Worten?"
    nutzen: "Wofür kann man sie nutzen, welches Thema der App nutzt sie?"
    lesen: "Wie deutet man sie richtig, wo sind die Grenzen? Unbekanntes als unbekannt nennen."
```

Bei unklarer Lizenz `lizenz: pruefen` setzen. Eine neue Lizenz in `katalog/lizenzen.yaml` nur mit Link
auf den Lizenztext anlegen.

## 4. Prüfen

```bash
uv run essen katalog --pruefen      # muss 0 Fehler melden
uv run essen info ID                # sieht der Eintrag richtig aus?
uv run essen laden ID               # wenn das Netz es erlaubt
uv run essen inspizieren ID         # Inhalt ansehen (Skill daten-inspizieren)
```

- Hat der Download geklappt: `status: geprueft` und unter `geprueft` Datum und Art der Prüfung eintragen.
- Ist das Portal gesperrt (Cloud-Sitzung, 403): `status: ungeprueft` lassen, nicht umgehen (docs/cloud.md).
- Neue Hosts erscheinen in `uv run essen katalog --domains`; bei Bedarf in docs/cloud.md ergänzen.

## 5. Abschließen

```bash
uv run essen katalog --doku         # docs/datenquellen.md neu schreiben
uv run pytest tests/test_katalog.py
```

Wenn der Datensatz eine geplante Analyse ermöglicht, `docs/fahrplan.md` anpassen.
