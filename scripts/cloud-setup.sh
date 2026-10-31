#!/bin/bash
# Einrichtung für Cloud-Sitzungen von Coding-Agenten (z. B. Claude Code im Browser).
# Läuft über den SessionStart-Hook in .claude/settings.json. Lokal tut das Skript nichts.
# Was hier ausgegeben wird, landet im Kontext der Sitzung: kurz halten.

if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/..}" || exit 0

if ! command -v uv >/dev/null 2>&1; then
  echo "Hinweis: uv fehlt in dieser Umgebung. Installation: pip install uv"
  exit 0
fi

if ! uv sync --quiet 2>/tmp/uv-sync.log; then
  echo "Hinweis: uv sync ist fehlgeschlagen, siehe /tmp/uv-sync.log"
  exit 0
fi

if [ ! -f data_test/.testdaten ]; then
  uv run --quiet essen testdaten >/dev/null 2>&1 && echo "Testdaten erzeugt: data_test/ (erfunden)."
fi

# Sind die Datenportale erreichbar? Sonst mit Testdaten arbeiten (docs/cloud.md).
code=$(curl -s -o /dev/null -m 6 -w "%{http_code}" https://www.opengeodata.nrw.de/produkte/ 2>/dev/null)
if [ "$code" = "200" ]; then
  echo "Datenportale erreichbar: echte Downloads mit uv run essen laden ID möglich."
else
  echo "Datenportale nicht erreichbar (HTTP $code). Mit Testdaten arbeiten: uv run essen --testdaten ... (docs/cloud.md)."
fi
exit 0
