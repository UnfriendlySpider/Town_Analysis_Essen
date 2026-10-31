"""Begriffe in einfacher Sprache: das Glossar der App (Seite „Begriffe erklärt“ und Tooltips).

Jeder Eintrag erklärt einen Fachbegriff in ein bis zwei Sätzen, ohne weitere Fachwörter vorauszusetzen.
Schlüssel sind die Begriffe so, wie sie in der App stehen.
"""

from __future__ import annotations

from .text import norm

BEGRIFFE: dict[str, str] = {
    "Baublock": "Ein von Straßen umschlossenes Stück Stadt mit seinen Häusern. Die Statistik fasst Daten oft je "
                "Baublock zusammen, damit einzelne Häuser nicht erkennbar sind.",
    "bebaute Fläche (Wirkraum)": "Die Flächen, auf denen Menschen wohnen und arbeiten: Häuser, Straßen, Plätze. Parks, "
                                 "Wald, Felder und Wasser gehören nicht dazu. Die Klimaanalyse nennt das Wirkraum.",
    "Dezibel (dB(A))": "Maß für die Lautstärke. 10 Dezibel mehr klingen etwa doppelt so laut. Das (A) heißt, dass die "
                       "Messung dem menschlichen Gehör angepasst ist. Zum Vergleich: ruhige Wohnstraße nachts etwa 40, "
                       "starker Straßenverkehr etwa 70 bis 80.",
    "Einstau": "Wasser, das nach einem Regen auf einer Fläche steht, weil es nicht schnell genug abfließen oder "
               "versickern kann. Angegeben als Höhe in Zentimetern.",
    "extremer Sommertag": "Eine Wetterlage, wie sie in Hitzewellen vorkommt: sehr heiß, kaum Wind, wolkenlos. Die "
                          "Klimaanalyse des Landes rechnet damit, um zu zeigen, wo es dann am heißesten wird.",
    "gefühlte Temperatur (PET)": "Wie warm es sich für einen Menschen im Freien anfühlt. Neben der Lufttemperatur "
                                 "zählen Sonne, Wind und Luftfeuchte. In der Sonne kann sie 10 Grad und mehr über der "
                                 "Lufttemperatur liegen; über 41 °C gilt als extreme Hitzebelastung.",
    "Grenzwert": "Eine Höchstmenge eines Schadstoffs, die laut Gesetz nicht überschritten werden darf. Für "
                 "Stickstoffdioxid gilt in der EU im Jahresmittel 40 µg/m³, ab 2030 strenger 20 µg/m³.",
    "Heißer Tag": "Ein Tag, an dem die höchste Temperatur mindestens 30 °C erreicht.",
    "Jungbaum": "Ein Baum, den die Stadt in den letzten Jahren neu gepflanzt hat, meist an Straßen oder auf Plätzen. "
                "Er braucht einige Jahre, bis seine Krone viel Schatten spendet.",
    "Planungshinweiskarte": "Eine Karte des Landesamts, die für bebaute Flächen sagt, wie dringend etwas gegen Hitze "
                            "getan werden sollte: dringender, erweiterter, mäßiger oder kein Handlungsbedarf. Grundlage "
                            "ist ein Modell der Wärme in Sommernächten.",
    "Privathaushalt": "Menschen, die zusammen an einer Adresse wohnen und gemeinsam wirtschaften, oder jemand, der "
                      "allein lebt. Die Stadt bildet Haushalte aus den Meldedaten (gleiche Adresse, Familien, Namen). "
                      "Menschen in Heimen zählen nicht dazu.",
    "Kühler Ort": "Ein öffentlich zugänglicher Ort, an dem man sich an heißen Tagen abkühlen kann, zum Beispiel ein "
                  "schattiger Park, ein Spielplatz unter Bäumen, eine Bibliothek oder ein Bad. Die Stadt Essen führt "
                  "eine Liste dieser Orte.",
    "Datensatz": "Eine Sammlung von Daten zu einem Thema, wie sie eine Behörde oder ein Portal herausgibt, zum Beispiel "
                 "die Grenzen der Stadtteile oder die Messwerte einer Wetterstation. Die Seite „Daten erklärt“ "
                 "beschreibt jeden Datensatz der App.",
    "Lizenz": "Die Regeln, unter denen man Daten nutzen und weitergeben darf. Bei vielen offenen Daten muss man bei "
              "einer Weitergabe nur Quelle und Lizenz nennen; für die private Nutzung auf dem eigenen Rechner gilt "
              "keine Pflicht.",
    "Luftlinie": "Die gerade Strecke zwischen zwei Punkten, ohne Umwege. Der Weg zu Fuß ist meist länger, weil Straßen, "
                 "Bahnlinien oder Zäune im Weg liegen.",
    "Jahresmittel": "Der Durchschnitt aller Messwerte eines Jahres. Kurze Spitzen fallen darin kaum auf.",
    "Klimatop": "Ein Gebiet mit ähnlichem Kleinklima, zum Beispiel Waldklima, Stadtrandklima oder Innenstadtklima. Das "
                "Landesamt leitet die Klimatope daraus ab, wie eine Fläche genutzt wird und wie dicht sie bebaut und "
                "versiegelt ist; gemessen wird dabei nichts.",
    "Korrelation": "Zeigt, wie eng zwei Werte über die Stadtteile zusammenhängen: nahe 1, wenn beide zusammen steigen; "
                   "nahe −1, wenn der eine steigt und der andere fällt; nahe 0, wenn es keinen Zusammenhang gibt. "
                   "Ein Zusammenhang beweist nicht, dass das eine das andere verursacht.",
    "Lärmschwelle": "Die Lautstärke, ab der Lärm auf Dauer der Gesundheit schaden kann. Das Umweltbundesamt empfiehlt, "
                    "ab nachts 55 und über den ganzen Tag 65 Dezibel Lärmschutz zu planen.",
    "Mehrfachbelastung": "Ein Stadtteil ist mehrfach belastet, wenn er bei mehreren Themen (hier Hitze in der Nacht, "
                         "Lärm, Starkregen) zu den am stärksten belasteten in Essen gehört.",
    "Mindestfläche": "Ist ein Stadtteil oder eine Fläche sehr klein, kann schon ein einzelnes Haus den Anteil stark "
                     "verändern. Unter der Mindestfläche wird deshalb kein Wert gezeigt.",
    "Mittel der Stadtteile": "Der Durchschnitt der Werte aller 50 Stadtteile, jeder Stadtteil zählt gleich viel. Er "
                             "kann vom Wert für die ganze Stadt abweichen, weil große Stadtteile dort mehr zählen.",
    "Modellrechnung": "Ein Ergebnis, das ein Computer aus Karten, Wetterdaten und Gebäuden berechnet hat, nicht "
                      "gemessen. Modelle zeigen gut, wo es im Vergleich wärmer oder lauter ist; der genaue Wert an "
                      "einem Ort kann abweichen.",
    "oberstes Fünftel": "Die 20 Prozent mit den höchsten Werten. Bei 50 Stadtteilen sind das die 10 Stadtteile, die in "
                        "einem Thema am stärksten belastet sind. Das ist ein Vergleich innerhalb Essens, kein Grenzwert.",
    "Rang": "Platz eines Stadtteils, wenn man alle 50 nach ihrem Wert sortiert. Rang 1 hat den höchsten Wert. Ob das "
            "gut oder schlecht ist, hängt vom Thema ab: viel Grün ist gut, viel Hitze nicht.",
    "Feinstaub (PM₁₀, PM₂,₅)": "Winzige Teilchen in der Luft, kleiner als 10 bzw. 2,5 Tausendstel Millimeter. Sie "
                               "kommen aus Verkehr, Heizungen, Industrie und Landwirtschaft und können tief in die "
                               "Lunge gelangen.",
    "Stickstoffdioxid (NO₂)": "Ein Reizgas, das vor allem aus Abgasen von Dieselfahrzeugen stammt. Es reizt die "
                              "Atemwege; an stark befahrenen Straßen ist es am höchsten.",
    "Starkregen (100-jährlich)": "Ein so heftiger Regen, dass er an einem Ort statistisch nur einmal in 100 Jahren "
                                 "vorkommt. Er kann trotzdem jedes Jahr irgendwo auftreten.",
    "Trend": "Die Richtung, in die sich Werte über viele Jahre im Schnitt entwickeln, hier als Änderung je 10 Jahre. "
             "Einzelne heiße oder kühle Jahre verschwinden darin.",
    "Tropennacht": "Eine Nacht, in der die Temperatur nicht unter 20 °C fällt.",
    "typischer Sommertag": "Ein warmer, sonniger Sommertag, wie er jeden Sommer mehrmals vorkommt.",
    "Versiegelung": "Boden, der mit Gebäuden, Asphalt, Beton oder Pflaster bedeckt ist. Dort kann Regen nicht "
                    "versickern und es heizt sich stärker auf.",
    "WHO-Richtwert": "Die Empfehlung der Weltgesundheitsorganisation von 2021: Bis zu diesem Wert sind gesundheitliche "
                     "Schäden kaum zu erwarten. Er ist strenger als die gesetzlichen Grenzwerte.",
    "Umweltzone": "Ein Gebiet, in dem nur Autos und Lastwagen mit grüner Plakette fahren dürfen, damit die Luft "
                  "sauberer wird. Die Zone ist eine Regel für den Verkehr, keine Messung der Luft.",
    "Zensus 2022": "Die Volkszählung von 2022. Ihre Einwohnerzahlen liegen auch für 100 × 100 Meter große Quadrate vor; "
                   "daraus schätzt die App, wie viele Menschen in einer Fläche wohnen.",
}


def erklaere(begriff: str) -> str:
    """Erklärung eines Begriffs; findet ihn auch ohne Beachtung von Groß- und Kleinschreibung oder Klammerzusatz."""
    if begriff in BEGRIFFE:
        return BEGRIFFE[begriff]
    gesucht = norm(begriff)
    for name, text in BEGRIFFE.items():
        if norm(name) == gesucht or norm(name).split(" (")[0] == gesucht:
            return text
    raise KeyError(f"Begriff „{begriff}“ ist nicht erklärt (essen/begriffe.py).")


def suche(text: str) -> dict[str, str]:
    """Alle Begriffe, deren Name oder Erklärung den Suchtext enthält, alphabetisch."""
    gesucht = norm(text or "")
    treffer = {n: t for n, t in BEGRIFFE.items() if gesucht in norm(n) or gesucht in norm(t)}
    return dict(sorted(treffer.items(), key=lambda e: norm(e[0])))
