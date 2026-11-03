import json
import re
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Locale, PageViewRestriction

from blog.models import BlogPage
from core.testing import SeededSiteTestCase


def jsonld_items(html):
    return [json.loads(block) for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class HeadTagTests(SeededSiteTestCase):
    """Chapter 11: what search engines and social networks read from each page."""

    def get(self, url):
        return self.client.get(url).content.decode()

    def test_structured_data_uses_the_type_search_engines_read(self):
        html = self.get("/writing/renaming-streamfield-blocks/")
        self.assertNotIn('type="application/json"', html)
        types = [item["@type"] for item in jsonld_items(html)]
        self.assertEqual(types, ["BlogPosting", "BreadcrumbList", "FAQPage"])

    def test_article_data(self):
        article = jsonld_items(self.get("/writing/renaming-streamfield-blocks/"))[0]
        self.assertEqual(article["datePublished"], "2027-01-12")
        self.assertEqual(article["mainEntityOfPage"], "http://localhost/writing/renaming-streamfield-blocks/")

    def test_page_content_cannot_break_out_of_the_script_tag(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        post.title = "</script><script>alert(1)</script>"
        post.save_revision().publish()
        html = self.get(post.url)
        self.assertNotIn("<script>alert(1)", html)

    def test_canonical_and_open_graph(self):
        html = self.get("/writing/testing-every-live-page/")
        self.assertIn('<link rel="canonical" href="http://localhost/writing/testing-every-live-page/">', html)
        self.assertIn('<meta property="og:title" content="Testing every live page in one test | Studio">', html)

    def test_hreflang_includes_self_and_x_default_when_translated(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        welsh = post.copy_for_translation(Locale.objects.create(language_code="cy"), copy_parents=True)
        welsh.save_revision().publish()
        html = self.get("/writing/testing-every-live-page/")
        self.assertIn('hreflang="en-gb" href="http://localhost/writing/testing-every-live-page/"', html)
        self.assertIn('hreflang="cy" href="http://localhost/cy/writing/testing-every-live-page/"', html)
        self.assertIn('hreflang="x-default" href="http://localhost/writing/testing-every-live-page/"', html)

    def test_untranslated_pages_have_no_hreflang(self):
        self.assertNotIn("hreflang", self.get("/writing/testing-every-live-page/"))


class MetaValidationTests(SeededSiteTestCase):
    def test_long_descriptions_are_rejected_on_save(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        post.search_description = "x" * 161
        with self.assertRaises(ValidationError) as caught:
            post.full_clean()
        self.assertIn("search_description", caught.exception.message_dict)


class SitemapRobotsRedirectTests(SeededSiteTestCase):
    def test_sitemap_lists_live_public_pages_with_content_dates(self):
        private = BlogPage.objects.get(slug="renaming-streamfield-blocks")
        PageViewRestriction.objects.create(page=private, restriction_type=PageViewRestriction.LOGIN)
        xml = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("<loc>http://localhost/writing/testing-every-live-page/</loc><lastmod>2027-02-03</lastmod>", xml)
        self.assertNotIn("renaming-streamfield-blocks", xml)

    def test_sitemap_is_per_site(self):
        call_command("add_site", "labs.localhost", name="Studio Labs", stdout=StringIO())
        xml = self.client.get("/sitemap.xml", HTTP_HOST="labs.localhost").content.decode()
        self.assertIn("http://labs.localhost/", xml)
        self.assertNotIn("/writing/", xml)

    def test_sitemap_includes_translations(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        welsh = post.copy_for_translation(Locale.objects.create(language_code="cy"), copy_parents=True)
        welsh.save_revision().publish()
        xml = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("<loc>http://localhost/cy/writing/testing-every-live-page/</loc>", xml)
        self.assertIn('hreflang="cy" href="http://localhost/cy/writing/testing-every-live-page/"', xml)

    def test_robots_points_at_this_sites_sitemap(self):
        call_command("add_site", "labs.localhost", name="Studio Labs", stdout=StringIO())
        body = self.client.get("/robots.txt", HTTP_HOST="labs.localhost").content.decode()
        self.assertIn("Sitemap: http://labs.localhost/sitemap.xml", body)

    def test_changing_a_slug_keeps_the_old_url_working(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        post.slug = "test-every-live-page"
        # page_slug_changed is sent on commit, and the redirect is created by its handler.
        with self.captureOnCommitCallbacks(execute=True):
            post.save_revision().publish()
        self.assertTrue(Redirect.objects.filter(old_path="/writing/testing-every-live-page").exists())
        response = self.client.get("/writing/testing-every-live-page/")
        self.assertRedirects(response, "/writing/test-every-live-page/", status_code=301, fetch_redirect_response=False)

    def test_renaming_a_draft_creates_no_redirect(self):
        # Since 8.1, only live pages get automatic redirects: a draft's old URL was never public.
        post = BlogPage.objects.get(slug="testing-every-live-page")
        post.unpublish()
        post.slug = "test-every-live-page"
        with self.captureOnCommitCallbacks(execute=True):
            post.save()
        self.assertFalse(Redirect.objects.filter(old_path="/writing/testing-every-live-page").exists())
