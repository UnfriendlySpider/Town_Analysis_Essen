@AGENTS.md

## Ergänzungen für Claude Code

- Die Skills unter `.claude/skills/` sind auch als Befehle verfügbar, zum Beispiel `/neue-datenquelle`, `/neue-analyse` oder `/daten-inspizieren`.
- In Cloud-Sitzungen läuft beim Start `scripts/cloud-setup.sh` (Hook in `.claude/settings.json`). Seine Ausgabe sagt, ob die Datenportale erreichbar sind.
- Für Screenshots der App ist in Cloud-Sitzungen meist Chromium für Playwright vorhanden. Die Hintergrundkarte und CDNs sind dort oft gesperrt; Leaflet kann über eine lokale Kopie eingehängt werden (Skill `app-erweitern`).
