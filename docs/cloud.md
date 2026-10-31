# Arbeiten in einer Cloud-Sitzung

Das Projekt lässt sich auch in einer Cloud-Sitzung eines Coding-Agenten weiterentwickeln, zum Beispiel mit
Claude Code im Browser. Die Sitzung klont das Repository und liest `CLAUDE.md` (mit `AGENTS.md`), die Skills
unter `.claude/skills/` und den Hook in `.claude/settings.json`.

## Was beim Start passiert

`.claude/settings.json` startet bei jeder Sitzung `scripts/cloud-setup.sh`. Das Skript tut nur in der
Cloud etwas (Umgebungsvariable `CLAUDE_CODE_REMOTE=true`):

1. `uv sync` installiert die Pakete aus `uv.lock`.
2. Gibt es noch keine Testdaten, erzeugt `uv run essen testdaten` sie in `data_test/`.
3. Es prüft kurz, ob die Datenportale erreichbar sind, und schreibt das Ergebnis in den Sitzungskontext.

## Netzwerk

In der Standardeinstellung („Trusted“) erreichen Cloud-Sitzungen Paketquellen wie PyPI und GitHub, aber nicht
die Datenportale. Zwei Wege:

- **Mit Testdaten arbeiten** (Standard): `uv run essen --testdaten …`, `uv run pytest`. Für Code, Tests und
  Oberfläche reicht das.
- **Portale freigeben:** In den Einstellungen der Cloud-Umgebung den Netzwerkzugriff auf „Custom“ stellen,
  „Also include default list of common package managers“ anhaken und die Hosts eintragen, die
  `uv run essen katalog --domains` ausgibt. Stand Oktober 2026:

  ```
  www.opengeodata.nrw.de
  opendata.essen.de
  opendata.dwd.de
  www.wms.nrw.de
  sgx.geodatenzentrum.de
  geodaten.metropoleruhr.de
  www.pegelonline.wsv.de
  data.sensor.community
  ```

Gesperrte Adressen nicht über Umwege (andere Werkzeuge, Spiegel, Proxys) erreichen. Wenn ein Download
gesperrt ist: Status im Katalog auf `ungeprueft` lassen und die Prüfung lokal nachholen.

## Daten in der Cloud

Geladene Daten liegen nur in der Sitzung und verschwinden mit ihr. Nie Daten committen (`data/` und
`data_test/` stehen in `.gitignore`). Ergebnisse, die bleiben sollen, gehören in die Doku oder den Katalog,
zum Beispiel eine geprüfte Zuordnung nach `katalog/zuordnungen/`.
