"""Geprüfte Farbstufen für Karten, jeweils hell nach dunkel.

Jede Stufenfolge besteht .claude/skills/karte-gestalten/farben_pruefen.py: durchgehende Helligkeit,
genug Abstand zwischen Nachbarstufen auch bei Farbsehschwächen, Abstand zur Farbe für fehlende Werte.
Neue Folgen erst prüfen, dann hier eintragen (Skill karte-gestalten).
"""

FARBSTUFEN: dict[str, tuple[str, ...]] = {
    "waerme": ("#e9a23e", "#df7d03", "#cb5d01", "#b43e03", "#912813"),   # Hitze, Belastung
    "gruen": ("#b9dc9b", "#8cc274", "#5ea84a", "#3b8432", "#235f1f"),    # Grün, Vegetation
    "neutral": ("#a8cbe6", "#7aaed6", "#4f91c2", "#2f73a6", "#1d5582"),  # alles ohne Wertung
}
KEINE_DATEN = "#d9ddd8"
HINTERGRUND = "#fdfdfb"
