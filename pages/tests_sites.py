from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from wagtail.models import Locale, Site

from blog.models import BlogPage
from core.models import BrandSettings
from core.testing import SeededSiteTestCase
from pages.models import HomePage


class MultiSiteTests(SeededSiteTestCase):
    """Chapter 8: two brands in one installation."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("add_site", "labs.localhost", name="Studio Labs", stdout=StringIO())
        call_command("setup_groups", stdout=StringIO())

    def test_each_hostname_gets_its_own_home_page(self):
        self.assertContains(self.client.get("/", HTTP_HOST="localhost"), "Django and Wagtail sites")
        self.assertContains(self.client.get("/", HTTP_HOST="labs.localhost"), "Studio Labs")

    def test_brand_settings_are_per_site(self):
        labs = Site.objects.get(hostname="labs.localhost")
        self.assertEqual(BrandSettings.for_site(labs).brand_name, "Studio Labs")
        self.assertContains(self.client.get("/", HTTP_HOST="labs.localhost"), "#2d6cdf")
        self.assertNotContains(self.client.get("/", HTTP_HOST="localhost"), "#2d6cdf")

    def test_editors_on_one_site_cannot_edit_the_other(self):
        editor = get_user_model().objects.create_user("eddie", "e@example.com", "pw")
        editor.groups.set([Group.objects.get(name="Editors")])
        studio_home = Site.objects.get(hostname="localhost").root_page
        labs_home = Site.objects.get(hostname="labs.localhost").root_page
        self.assertTrue(studio_home.permissions_for_user(editor).can_edit())
        self.assertFalse(labs_home.permissions_for_user(editor).can_edit())

    def test_add_site_is_idempotent(self):
        call_command("add_site", "labs.localhost", name="Studio Labs", stdout=StringIO())
        self.assertEqual(HomePage.objects.count(), 2)


class TranslationTests(SeededSiteTestCase):
    """Chapter 8: a Welsh translation of one article, served under /cy/."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.welsh = Locale.objects.create(language_code="cy")
        post = BlogPage.objects.get(slug="testing-every-live-page")
        cls.translation = post.copy_for_translation(cls.welsh, copy_parents=True)
        cls.translation.title = "Profi pob tudalen fyw"
        cls.translation.save_revision().publish()

    def test_translation_is_linked_to_the_original(self):
        post = BlogPage.objects.get(slug="testing-every-live-page", locale__language_code="en-gb")
        self.assertEqual(post.translation_key, self.translation.translation_key)
        self.assertEqual(list(post.get_translations()), [self.translation.page_ptr.specific])

    def test_welsh_page_is_served_under_cy(self):
        response = self.client.get("/cy/writing/testing-every-live-page/")
        self.assertContains(response, "Profi pob tudalen fyw")
        self.assertContains(response, '<html lang="cy">')

    def test_english_page_advertises_its_translation(self):
        response = self.client.get("/writing/testing-every-live-page/")
        self.assertContains(response, 'hreflang="cy" href="http://localhost/cy/writing/testing-every-live-page/"')

    def test_parents_were_created_as_drafts(self):
        welsh_blog = self.translation.get_parent()
        self.assertEqual(welsh_blog.locale, self.welsh)
