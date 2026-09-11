from io import StringIO

from django.core.management import call_command
from wagtail.test.utils import WagtailPageTestCase


class SeededSiteTestCase(WagtailPageTestCase):
    """A test case with the full Studio demo site built once per class."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", stdout=StringIO())
