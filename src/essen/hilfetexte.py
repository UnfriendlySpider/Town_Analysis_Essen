"""Hilfetexte der App: je Seite ein Satz „Wozu ist die Seite da?“ und zwei bis vier Schritte.

Die Seiten zeigen sie oben im Kasten „So funktioniert diese Seite“. Begriffe, die dort vorkommen und im
Glossar stehen, werden unter dem Kasten erklärt (Feld begriffe).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hilfe:
    wozu: str
    schritte: tuple[str, ...]
    begriffe: tuple[str, ...] = ()


HILFE: dict[str, Hilfe] = {
    "start": Hilfe(
        "Antworten auf Fragen zur Umwelt in Ihrer Stadt: Hitze, Grün, Lärm, Starkregen und Luft – für jeden der 50 "
        "Stadtteile, aus offenen Daten von Stadt, Land und Bund.",
        ("Wählen Sie unten eine Frage, die Sie interessiert – die App führt Sie zur passenden Seite.",
         "Unter „Essen in Zahlen“ stehen die wichtigsten Ergebnisse für die ganze Stadt.",
         "Unbekannte Wörter erklärt die Seite „Begriffe erklärt“ im Menü links."),
    ),
    "stadtteil": Hilfe(
        "Alle Themen für einen Stadtteil auf einen Blick, jeweils im Vergleich mit den anderen 49 Stadtteilen.",
        ("Wählen Sie oben Ihren Stadtteil.",
         "Jeder Kasten zeigt ein Thema: den Wert, eine farbige Einordnung und einen Satz dazu.",
         "Die Punktreihe darunter zeigt alle Stadtteile; Ihr Stadtteil ist der große, beschriftete Punkt, der Strich "
         "das Mittel.",
         "Grün heißt günstiger, Rot ungünstiger als die meisten Stadtteile; Grau liegt im Mittelfeld.",
         "Mit „Mehr zum Thema“ sehen Sie die Karte für ganz Essen."),
        ("Mittel der Stadtteile", "Rang"),
    ),
    "themen": Hilfe(
        "Ein Thema für ganz Essen: Karte, alle Stadtteile der Reihe nach und was die Zahl bedeutet.",
        ("Wählen Sie oben ein Thema.",
         "Lesen Sie den Kasten „So lesen Sie das“: Er sagt, ob dunkel gut oder schlecht ist.",
         "Zeigen oder tippen Sie auf einen Stadtteil, um seinen Wert zu sehen. Ein Klick auf einen Balken in "
         "„Alle Stadtteile im Vergleich“ öffnet diesen Stadtteil.",
         "Gibt es für ein Thema mehrere Jahre, schalten Sie über der Karte auf „Verlauf über die Jahre“. ▶ spielt "
         "die Jahre nacheinander ab, die kleinen Karten zeigen alle Zeitpunkte nebeneinander. Steht dort „nur ein "
         "Datenstand“, gibt es keine älteren Daten.",
         "„Was diese Zahl nicht sagt“ nennt die wichtigsten Grenzen."),
        ("Modellrechnung",),
    ),
    "karte": Hilfe(
        "Eine Karte von Essen, auf der Sie ein Thema einblenden und mit Karten der Behörden vergleichen können.",
        ("Wählen Sie links, was die Karte zeigen soll. Ein Klick auf einen Stadtteil zeigt seinen Wert.",
         "Unter „Orte einblenden“ legen Sie Punkte darüber, etwa kühle Orte für heiße Tage oder Ladesäulen.",
         "Mit dem Mausrad, zwei Fingern oder + und − zoomen Sie; durch Ziehen verschieben Sie die Karte.",
         "Unter „Weitere Karten der Anbieter“ können Sie Originalkarten der Behörden darüberlegen."),
    ),
    "vergleich": Hilfe(
        "Zeigt, ob zwei Themen zusammenhängen – zum Beispiel, ob Stadtteile mit wenig Grün nachts wärmer sind.",
        ("Wählen Sie zwei Themen.",
         "Jeder Punkt ist ein Stadtteil. Zeigen oder tippen Sie darauf, um den Namen zu sehen.",
         "Der Satz über dem Bild sagt in Worten, wie eng die Themen zusammenhängen.",
         "Die gestrichelten Linien teilen das Bild in vier Felder, zum Beispiel „beides hoch“."),
        ("Korrelation",),
    ),
    "zeitreihen": Hilfe(
        "Wie sich Hitze und Luftqualität über die Jahre entwickelt haben: heiße Tage in Ihrem Stadtteil seit 1951, "
        "an der Wetterstation Bredeney seit 1935 und Luftwerte an den Messstationen.",
        ("Wählen Sie oben, was Sie sehen möchten. Bei „Heiße Tage in Ihrem Stadtteil“ wählen Sie Ihren Stadtteil "
         "und unter „Vergleichen mit …“ weitere Stadtteile oder ganz Essen.",
         "Mit dem Schieberegler wählen Sie den Zeitraum.",
         "„Auf der Karte“ zeigt alle Stadtteile je Jahrzehnt; ▶ spielt den Verlauf ab, ein Klick auf einen Stadtteil "
         "wählt ihn aus. Für versiegelten Boden, neue Bäume und Haushalte führen die Links oben zur Karte über die Jahre.",
         "„Früher und heute“ vergleicht 1961–1990 mit den letzten zehn Jahren; die Liste „Trend“ zeigt die "
         "Änderung je 10 Jahre. Bei der Luft zeigen gestrichelte Linien die Grenzwerte."),
        ("Heißer Tag", "Modellrechnung", "Trend", "Grenzwert", "WHO-Richtwert"),
    ),
    "begriffe": Hilfe(
        "Alle Fachwörter der App in einfacher Sprache.",
        ("Tippen Sie ein Wort in die Suche oder blättern Sie durch die Liste.",),
    ),
    "daten_erklaert": Hilfe(
        "Jeder Datensatz der App in Worten: von wem er stammt, was drinsteht, wofür man ihn nutzen kann und wie man "
        "ihn richtig liest.",
        ("Wählen Sie oben einen Datensatz; die Liste ist nach Themen geordnet. Mit der Suche finden Sie ein Wort in "
         "allen Erklärungen.",
         "Der Kasten „Auf einen Blick“ nennt Anbieter, Lizenz und die Themen der App, die den Datensatz nutzen.",
         "Wer die Dateien selbst ansehen möchte, findet den Weg dorthin am Ende der Seite (Werkstatt)."),
        ("Datensatz", "Lizenz", "Modellrechnung"),
    ),
    "vorbereiten": Hilfe(
        "Lädt einmal alle Daten von den Behörden und berechnet alle Themen. Danach zeigt die App überall Ergebnisse.",
        ("Prüfen Sie, wie viel heruntergeladen wird und ob genug Platz frei ist.",
         "Klicken Sie auf „Alles vorbereiten“. Das dauert je nach Internet einige Minuten.",
         "Später können Sie hier prüfen, ob es neuere Daten gibt."),
    ),
    "daten_laden": Hilfe(
        "Alle Datensätze, die die App kennt, mit Herkunft und Nutzungsbedingungen. Für die Themen genügt „Alles "
        "vorbereiten“; hier laden Sie einzelne Datensätze gezielt.",
        ("Suchen oder filtern Sie oben.",
         "„Herunterladen“ holt einen Datensatz direkt bei der Behörde.",
         "„Details“ nennt Herkunft, Stand und die Quellenangabe zum Weitergeben."),
    ),
    "neu_berechnen": Hilfe(
        "Für Fortgeschrittene: ein Thema mit anderen Einstellungen berechnen und die Ergebnisse herunterladen.",
        ("Wählen Sie ein Thema und prüfen Sie, ob alle Daten geladen sind.",
         "Ändern Sie unter „Einstellungen“, was Sie anders sehen möchten.",
         "Klicken Sie auf „Berechnen“. Das Ergebnis ersetzt das bisherige für dieses Thema."),
    ),
    "untersuchen": Hilfe(
        "Für Fortgeschrittene: zeigt, was in einem geladenen Datensatz steckt – Ebenen, Felder, Werte, Legenden.",
        ("Wählen Sie einen Datensatz.", "Klicken Sie auf „Untersuchen“ und lesen Sie den Bericht."),
    ),
    "originaldaten": Hilfe(
        "Für Fortgeschrittene: zeigt die Originaldateien eines geladenen Datensatzes – als Karte, Tabelle oder Bild, "
        "so wie sie von der Behörde kommen.",
        ("Wählen Sie einen Datensatz und darin eine Datei.",
         "Vektordaten erscheinen auf der Karte und als Tabelle; fahren Sie über ein Objekt, um seine Werte zu sehen.",
         "Rasterdaten erscheinen als Bild über Essen, dazu eine Verteilung der Werte.",
         "Große Dateien werden nur als Ausschnitt gezeigt: Objekte im Rechteck um Essen, Bilder vergröbert."),
    ),
    "schnellanalyse": Hilfe(
        "Für Fortgeschrittene: verteilt Punkte, Linien oder Flächen eines Datensatzes auf die Stadtteile, etwa die "
        "Zahl der Ladesäulen je Quadratkilometer.",
        ("Wählen Sie einen Datensatz und eine Ebene.", "Klicken Sie auf „Verteilen“."),
    ),
    "quellen": Hilfe(
        "Alle Behörden und Portale, von denen die Daten stammen, mit Zugang und Nutzungsbedingungen.",
        ("Filtern Sie oben nach Thema oder Ebene.", "Unter „Einzelheiten“ stehen Links und Hinweise."),
    ),
    "methodik": Hilfe(
        "Wie jedes Thema berechnet wurde, unter welchen Bedingungen Daten genutzt werden dürfen und woher sie stammen.",
        ("„Methodik“ beschreibt Rechenweg, Prüfung und Grenzen je Thema.",
         "„Lizenzen“ und „Quellenangaben“ brauchen Sie, wenn Sie Ergebnisse weitergeben möchten."),
    ),
}


# Begriffe, die zu einem Thema gehören (Kasten „Begriffe zu diesem Thema“ auf der Seite Themen)
THEMA_BEGRIFFE: dict[str, tuple[str, ...]] = {
    "hitze-nacht": ("bebaute Fläche (Wirkraum)", "Tropennacht", "extremer Sommertag", "Modellrechnung"),
    "hitze-tag": ("gefühlte Temperatur (PET)", "extremer Sommertag", "Modellrechnung"),
    "versiegelung": ("Versiegelung",),
    "gruenanteil": ("Mindestfläche",),
    "laerm": ("Dezibel (dB(A))", "Lärmschwelle", "Modellrechnung"),
    "starkregen": ("Starkregen (100-jährlich)", "Einstau", "Modellrechnung"),
    "betroffenheit": ("Baublock", "bebaute Fläche (Wirkraum)", "Zensus 2022"),
    "mehrfachbelastung": ("Mehrfachbelastung", "oberstes Fünftel"),
    "hitzetage-station": ("Heißer Tag", "Tropennacht", "Trend"),
    "hitzetage-raster": ("Heißer Tag", "Modellrechnung", "Trend"),
    "kuehlorte": ("Kühler Ort", "Luftlinie", "Zensus 2022"),
    "jungbaeume": ("Jungbaum",),
    "haushalte": ("Privathaushalt",),
    "umweltzone": ("Umweltzone",),
    "planungshinweise": ("Planungshinweiskarte", "bebaute Fläche (Wirkraum)", "Modellrechnung"),
    "klimatope": ("Klimatop", "Modellrechnung"),
    "luft-station": ("Stickstoffdioxid (NO₂)", "Feinstaub (PM₁₀, PM₂,₅)", "Jahresmittel", "Grenzwert", "WHO-Richtwert"),
}
