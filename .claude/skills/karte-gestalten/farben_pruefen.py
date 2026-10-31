"""Prüft eine Farbstufenfolge für Karten: Helligkeit, Abstände, Farbsehschwächen, Kontrast.

Aufruf:
    uv run python .claude/skills/karte-gestalten/farben_pruefen.py "#e9a23e,#df7d03,#cb5d01,#b43e03,#912813"
    uv run python .claude/skills/karte-gestalten/farben_pruefen.py "…" --hintergrund "#fdfdfb" --keine "#d9ddd8"

Geprüft wird (Abstände in OKLab × 100):
- Helligkeit steigt oder fällt durchgehend (eine Farbe, hell nach dunkel)
- Nachbarstufen unterscheiden sich mit normalem Sehen um mindestens 8
- auch bei Protanopie, Deuteranopie und Tritanopie um mindestens 6 (Simulation nach Machado 2009)
- jede Stufe unterscheidet sich von der Farbe für „keine Daten“ um mindestens 8
- Kontrast der hellsten Stufe zum Hintergrund mindestens 1,15 (sonst Umrisse nötig)
Ausgang 1, wenn eine Prüfung scheitert.
"""

from __future__ import annotations

import argparse
import math
import sys
from itertools import pairwise

MACHADO = {
    "Protanopie": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "Deuteranopie": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "Tritanopie": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def linear(hexfarbe: str) -> tuple[float, float, float]:
    h = hexfarbe.lstrip("#")
    werte = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(w / 12.92 if w <= 0.04045 else ((w + 0.055) / 1.055) ** 2.4 for w in werte)


def oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = rgb
    lk = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    mk = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    sk = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    lk, mk, sk = (math.copysign(abs(x) ** (1 / 3), x) for x in (lk, mk, sk))
    return (0.2104542553 * lk + 0.7936177850 * mk - 0.0040720468 * sk,
            1.9779984951 * lk - 2.4285922050 * mk + 0.4505937099 * sk,
            0.0259040371 * lk + 0.7827717662 * mk - 0.8086757660 * sk)


def abstand(a, b) -> float:
    return 100 * math.dist(oklab(a), oklab(b))


def simuliere(rgb, matrix):
    return tuple(min(1.0, max(0.0, sum(matrix[i][j] * rgb[j] for j in range(3)))) for i in range(3))


def kontrast(a, b) -> float:
    def leuchtdichte(rgb):
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    hell, dunkel = sorted((leuchtdichte(a), leuchtdichte(b)), reverse=True)
    return (hell + 0.05) / (dunkel + 0.05)


def pruefe(farben: list[str], hintergrund: str, keine: str | None) -> list[tuple[str, bool, str]]:
    rgb = [linear(f) for f in farben]
    ergebnisse = []
    helligkeit = [oklab(f)[0] for f in rgb]
    stetig = all(a > b for a, b in pairwise(helligkeit)) or all(a < b for a, b in pairwise(helligkeit))
    ergebnisse.append(("Helligkeit durchgehend", stetig, " → ".join(f"{100 * h:.0f}" for h in helligkeit)))
    normal = [abstand(a, b) for a, b in pairwise(rgb)]
    ergebnisse.append(("Nachbarn, normales Sehen ≥ 8", min(normal) >= 8, ", ".join(f"{d:.1f}" for d in normal)))
    for name, matrix in MACHADO.items():
        sim = [simuliere(f, matrix) for f in rgb]
        werte = [abstand(a, b) for a, b in pairwise(sim)]
        ergebnisse.append((f"Nachbarn, {name} ≥ 6", min(werte) >= 6, ", ".join(f"{d:.1f}" for d in werte)))
    if keine:
        werte = [abstand(f, linear(keine)) for f in rgb]
        ergebnisse.append((f"Abstand zu „keine Daten“ {keine} ≥ 8", min(werte) >= 8, ", ".join(f"{d:.1f}" for d in werte)))
    hellste = max(rgb, key=lambda f: oklab(f)[0])
    wert = kontrast(hellste, linear(hintergrund))
    ergebnisse.append((f"Kontrast hellste Stufe zu {hintergrund} ≥ 1,15", wert >= 1.15, f"{wert:.2f}"))
    return ergebnisse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("farben", help="Farben hell nach dunkel, mit Komma getrennt")
    parser.add_argument("--hintergrund", default="#fdfdfb")
    parser.add_argument("--keine", default="#d9ddd8", help="Farbe für fehlende Werte (leer = nicht prüfen)")
    args = parser.parse_args()
    farben = [f.strip() for f in args.farben.split(",") if f.strip()]
    ergebnisse = pruefe(farben, args.hintergrund, args.keine or None)
    for titel, ok, werte in ergebnisse:
        print(f"{'OK  ' if ok else 'FEHL'}  {titel:45s} {werte}")
    sys.exit(0 if all(ok for _, ok, _ in ergebnisse) else 1)


if __name__ == "__main__":
    main()
