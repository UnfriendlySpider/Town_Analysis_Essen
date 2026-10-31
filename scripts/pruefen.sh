#!/bin/bash
# Alles prüfen, bevor etwas eingecheckt wird: Stil, Katalog, Tests (samt erzeugter Doku).
# Aufruf: scripts/pruefen.sh   (Code 0 = alles in Ordnung)

cd "$(dirname "$0")/.." || exit 1
fehler=0

schritt() {
  echo "▸ $1"
  shift
  if ! "$@"; then
    echo "✗ fehlgeschlagen: $*"
    fehler=1
  fi
}

schritt "Stil (ruff)" uv run ruff check src tests scripts .claude/skills
schritt "Katalog" uv run essen katalog --pruefen
# Die Tests prüfen auch, ob docs/datenquellen.md und docs/daten-erklaert.md zum Katalog passen.
schritt "Tests" uv run pytest -q

if [ "$fehler" -eq 0 ]; then
  echo "✓ alles in Ordnung"
else
  echo "✗ es gibt Fehler (siehe oben)"
fi
exit "$fehler"
