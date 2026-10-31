import pytest

from essen import dienste
from essen.laden import DownloadFehler

WMS = b"""<?xml version="1.0"?>
<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms"><Capability><Layer><Title>Wurzel</Title>
<Layer><Name>nacht</Name><Title>Klimaanalysekarte Nacht</Title><Abstract>4 Uhr</Abstract></Layer>
<Layer><Title>Gruppe ohne Namen</Title><Layer><Name>tag</Name><Title>Tag</Title></Layer></Layer>
</Layer></Capability></WMS_Capabilities>"""

WFS = b"""<?xml version="1.0"?>
<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0"><wfs:FeatureTypeList>
<wfs:FeatureType><wfs:Name>app:klimatope</wfs:Name><wfs:Title>Klimatope</wfs:Title></wfs:FeatureType>
</wfs:FeatureTypeList></wfs:WFS_Capabilities>"""


def test_wms_ebenen_nur_mit_namen():
    ebenen = dienste.ebenen_aus_xml(WMS, "wms")
    assert [(e.name, e.titel) for e in ebenen] == [("nacht", "Klimaanalysekarte Nacht"), ("tag", "Tag")]


def test_wfs_objektarten():
    assert [e.name for e in dienste.ebenen_aus_xml(WFS, "wfs")] == ["app:klimatope"]


def test_fehlermeldung_des_dienstes():
    with pytest.raises(DownloadFehler, match="kaputt"):
        dienste.ebenen_aus_xml(b"<ServiceExceptionReport><ServiceException>kaputt</ServiceException></ServiceExceptionReport>", "wms")


def test_capabilities_adresse():
    assert dienste.capabilities_adresse("https://x.de/wms", "wms") == "https://x.de/wms?SERVICE=WMS&REQUEST=GetCapabilities"
    assert dienste.capabilities_adresse("https://x.de/wms?map=a", "wfs").endswith("&SERVICE=WFS&REQUEST=GetCapabilities")
