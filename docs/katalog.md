# Der Datenkatalog

Drei Dateien in `katalog/` beschreiben alles, was das Projekt über Datenquellen weiß. Nach jeder Änderung:

```bash
uv run essen katalog --pruefen   # Fehler und Warnungen
uv run essen katalog --doku      # docs/datenquellen.md neu schreiben
uv run pytest tests/test_katalog.py
```

## lizenzen.yaml

Schlüssel ist die Lizenzkennung (`dl-de-by-2.0`). Felder: `name`, `kurz`, `url`, `namensnennung`,
`kommerziell`, `bearbeitung`, `gleiche_bedingungen`, `pruefen` (true bei unklaren Rechten), `hinweis`.
Neue Lizenzen nur mit Link auf den Lizenztext anlegen.

## quellen.yaml

Liste `quellen`, ein Eintrag je Anbieter, Portal oder Schnittstelle.

| Feld | Pflicht | Inhalt |
| --- | --- | --- |
| `id` | ja | Kennung aus Kleinbuchstaben, Ziffern und Bindestrichen |
| `name`, `kurz` | ja, nein | Name und Untertitel |
| `ebene` | ja | `stadt`, `region`, `land`, `bund`, `mobilitaet`, `community` |
| `themen` | ja | Liste aus `klima`, `luft`, `laerm`, `wasser`, `gruen`, `energie`, `geo`, `bevoelkerung`, `mobilitaet`, `wahlen`, `wirtschaft`, `verwaltung`, `kultur` |
| `beschreibung` | ja | ein bis drei Sätze |
| `lizenz`, `lizenz_hinweis` | ja, nein | Kennung aus lizenzen.yaml und Freitext |
| `zugang`, `aktualitaet` | nein | z. B. `[WMS, WFS]`, `stündlich` |
| `konto`, `konto_hinweis` | nein | `ohne`, `registrierung`, `auf-anfrage`, `oeffentlicher-schluessel`, `bedingt`, `unklar` |
| `eignung` | nein | 1 eingeschränkt, 2 mittel, 3 hoch |
| `endpunkte`, `links` | nein | Listen aus `{titel, url}`; Platzhalter wie `<id>` sind hier erlaubt |
| `beispiele`, `hinweise`, `kontakt` | nein | Listen aus Text |

Liste `luecken`: bekannte fehlende Daten mit `art`, `titel`, `text`, `weg`.

## datensaetze.yaml

Liste `datensaetze`, ein Eintrag je Datensatz, den das Projekt laden, ansehen oder auswerten kann.

| Feld | Pflicht | Inhalt |
| --- | --- | --- |
| `id` | ja | Kennung, wird zum Ordnernamen unter `data/raw/` |
| `titel`, `beschreibung` | ja | |
| `quelle` | ja | `id` aus quellen.yaml |
| `bereitsteller` | nein | wer in der Quellenangabe steht, sonst der Name der Quelle |
| `themen` | ja | das erste Thema bestimmt die Gruppe in Übersichten |
| `format`, `raumbezug`, `stand` | nein | Freitext |
| `lizenz` | ja | Kennung aus lizenzen.yaml |
| `namensnennung` | nein | vorgeschriebener Wortlaut, `{jahr}` wird ersetzt |
| `seite` | ja | Seite des Datensatzes beim Anbieter |
| `download` | ja | siehe unten |
| `dienste` | nein | Kartendienste: `{art: wms|wfs|xyz|ogcapi, url, titel, ebenen}` |
| `felder` | nein | Hinweise zum Aufbau, z. B. `{name: STADTTEILE, nummer: …}` |
| `status` | ja | `geprueft`, `ungeprueft`, `manuell`, `dienst` |
| `geprueft` | bei Status geprueft | wann und wie geprüft, z. B. `"2026-10-10: index.json gelesen"` |
| `analysen` | nein | Analysen, die den Datensatz nutzen |
| `begleitend` | nein | Datensätze mit Beschreibung oder Legende dazu |
| `hinweise` | nein | Liste aus Text: Besonderheiten, offene Fragen |
| `erklaerung` | nein (Warnung, wenn sie fehlt) | Der Datensatz in Worten für die App-Seite „Daten erklärt“ und `docs/daten-erklaert.md`: `herkunft` (wer, wie entstanden), `inhalt` (was drinsteht), `nutzen` (wofür), `lesen` (richtig deuten, Grenzen). Einfache Sprache, Anrede „Sie“, nichts erfinden: Unbelegtes als unbekannt benennen. |

### download

| `art` | Pflichtfelder | Verhalten |
| --- | --- | --- |
| `datei` | `url` | lädt die Datei; `datei` legt den Namen fest |
| `dateien` | `urls` (Liste) | lädt alle Dateien in denselben Ordner, z. B. mehrere Ressourcen eines Datensatzes im Essener Portal; `essen laden ID --datei NAME` lädt eine davon nach |
| `verzeichnis` | `ordner` (mit `/` am Ende), `muster` | liest `index.json` oder die Linkliste des Ordners und nimmt die Datei, die zum Muster passt (`*` und `?`); bei mehreren fragt die App, mit `alle: true` lädt sie alle passenden (z. B. eine Datei je Jahr) |
| `wfs` | `url`, `typname` | GetFeature (WFS 2.0) für das Stadtgebiet in EPSG:25832; `format` z. B. `application/json`, `parameter` für Zusätze |
| `api` | `url` | lädt JSON; Platzhalter `{heute}`, `{gestern}`, `{vor_7_tagen}`, `{vor_30_tagen}`, `{bbox_wgs84}`, `{bbox_25832}` |
| `manuell` | `hinweis` | kein automatischer Download; die App zeigt Link und Datei-Übernahme, die Kommandozeile `essen einlesen ID DATEI` |
| `keiner` | – | nur ansehen (Kartendienst) |

`groesse_mb` ist optional. Ab 500 MB fragt die App vor dem Laden nach.

### Status richtig setzen

- `geprueft`: Die Adresse wurde bestätigt, z. B. weil der Dateiname im `index.json` steht oder ein Download geklappt hat. Immer mit Vermerk unter `geprueft`.
- `ungeprueft`: Download eingetragen, aber nicht bestätigt (etwa weil das Portal aus der Cloud nicht erreichbar war).
- `manuell` und `dienst` passen nur zu `art: manuell` bzw. `art: keiner`.

## zuordnungen/

Geprüfte Wertezuordnungen, die eine Analyse braucht, um Daten zu deuten, zum Beispiel welche Rasterwerte zu
welcher Temperaturklasse gehören. Format am Beispiel:

```yaml
datensatz: klimaanalyse-nacht-raster
lesart: werte        # werte | temperatur | farben
band: 1              # welches Band gelesen wird (bei werte und temperatur)
geprueft: true       # erst nach Abgleich mit der Legende des Anbieters
quelle: "Legende aus Klimaanalyse_meta.zip/…"
werte:
  1: 1
  11: ausgleich      # gehört nicht zum Wirkraum
  12: "?"            # noch offen (in Anführungszeichen, sonst ist es kein gültiges YAML)
farben:              # nur bei lesart: farben; für RGB-Raster oder ein Band mit Farbtabelle
  "#fdae61": 6
```

Für stetige Raster (`lesart: temperatur`) kommen zwei Angaben dazu, wie bei der echten Klimaanalyse:

```yaml
dateien:             # welche Datei im ZIP je Szenario gelesen wird (Parameter szenario)
  extrem: PL_KY_NACHT_LT_EXT.tif
  typisch: PL_KY_NACHT_LT_TYP.tif
wirkraum: fehlwerte  # Zellen mit Wert sind Wirkraum; ohne diese Angabe grenzt das GeoPackage ab
vermerk: "Datum: wie geprüft"
```

Liegen mehrere Raster im Datensatz und fehlt `dateien`, bricht die Analyse ab, statt eine Datei zu raten.

Werte ohne Klasse oder mit `"?"` zählen nicht zum Wirkraum. Betreffen sie mehr als 1 % der Zellen im
Stadtgebiet, bricht die Analyse mit einer Liste der offenen Werte ab.

Vorlagen schreibt die Analyse nach `data/zuordnungen/`. Eine Zuordnung im Datenordner hat Vorrang vor der im
Katalog; so können Testdaten eigene Zuordnungen haben.
