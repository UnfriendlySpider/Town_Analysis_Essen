from essen import analysen, vorbereiten
from essen.analysen.basis import Ergebnis


def test_plan_ohne_daten_nennt_alles(leerer_datenordner, katalog):
    plan = vorbereiten.plan(katalog)
    assert set(plan.fehlend) == set(vorbereiten.benoetigte_datensaetze())
    assert "stadtteile" in plan.fehlend and "zensus-2022-gitter" in plan.fehlend
    assert plan.download_mb > 0 and plan.frei_gb > 0
    assert plan.zu_rechnen == vorbereiten.reihenfolge() and plan.zu_rechnen[-1] == "mehrfachbelastung"
    assert not plan.fertig and not vorbereiten.ist_vorbereitet()


def test_ausfuehren_mit_testdaten_rechnet_alles(kopie_testdaten, katalog):
    import shutil

    from essen import pfade

    shutil.rmtree(pfade.verarbeitet(), ignore_errors=True)  # Ergebnisse früherer Tests entfernen
    vorher = vorbereiten.plan(katalog)
    assert vorher.fehlend == []  # Testdaten enthalten alle nötigen Datensätze
    meldungen = []
    schritte = vorbereiten.ausfuehren(katalog, melde=meldungen.append)
    assert all(s.ok for s in schritte), [s.text for s in schritte if not s.ok]
    assert {s.kennung for s in schritte} == set(analysen.ALLE)
    assert vorbereiten.plan(katalog).fertig and vorbereiten.ist_vorbereitet()
    assert all(Ergebnis.laden(k) is not None for k in analysen.ALLE)
    # zweiter Lauf: nichts mehr zu tun
    assert vorbereiten.ausfuehren(katalog, melde=meldungen.append) == []


def test_fehler_stoppt_nur_den_eigenen_schritt(kopie_testdaten, katalog, monkeypatch):
    from essen import laden

    laden.entferne("laermkarte-essen")
    monkeypatch.setattr(laden, "hole", lambda *a, **k: (_ for _ in ()).throw(laden.DownloadFehler("kein Netz")))
    schritte = {(s.art, s.kennung): s for s in vorbereiten.ausfuehren(katalog, melde=lambda m: None)}
    assert not schritte[("laden", "laermkarte-essen")].ok and "kein Netz" in schritte[("laden", "laermkarte-essen")].text
    assert not schritte[("rechnen", "laerm")].ok
    assert schritte[("rechnen", "gruenanteil")].ok
