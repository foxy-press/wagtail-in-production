from io import StringIO

from django.core.management import call_command
from django.test import override_settings

from core.testing import SeededSiteTestCase


@override_settings(ALLOWED_HOSTS=["studio.example"])
class ConfigureSiteTests(SeededSiteTestCase):
    """Chapter 15: absolute URLs come from the Site record, not from the request."""

    def test_canonical_urls_use_the_configured_domain(self):
        call_command("configure_site", "studio.example", stdout=StringIO())
        html = self.client.get("/writing/", HTTP_HOST="studio.example").content.decode()
        self.assertIn('<link rel="canonical" href="https://studio.example/writing/">', html)

    def test_sitemap_uses_the_configured_domain(self):
        call_command("configure_site", "studio.example", stdout=StringIO())
        xml = self.client.get("/sitemap.xml", HTTP_HOST="studio.example").content.decode()
        self.assertIn("<loc>https://studio.example/writing/</loc>", xml)
