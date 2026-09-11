from io import StringIO

from django.core.management import call_command
from django.urls import reverse
from wagtail.contrib.search_promotions.models import Query, SearchPromotion
from wagtail.models import PageViewRestriction

from blog.models import BlogPage
from core.testing import SeededSiteTestCase


class SearchTests(SeededSiteTestCase):
    """Chapter 9: what visitors can find, and what they must not."""

    def search(self, q, host="localhost"):
        return self.client.get(reverse("search"), {"q": q}, HTTP_HOST=host)

    def test_finds_words_inside_streamfield_blocks(self):
        # "revert" appears only in a paragraph block of one article's body
        self.assertContains(self.search("revert"), "Renaming a StreamField block")

    def test_finds_pages_by_related_topic_name(self):
        response = self.search("testing")
        self.assertContains(response, "Testing every live page")

    def test_excludes_drafts(self):
        BlogPage.objects.get(slug="renaming-streamfield-blocks").unpublish()
        self.assertNotContains(self.search("revert"), "Renaming a StreamField block")

    def test_excludes_private_pages(self):
        post = BlogPage.objects.get(slug="renaming-streamfield-blocks")
        PageViewRestriction.objects.create(page=post, restriction_type=PageViewRestriction.LOGIN)
        self.assertNotContains(self.search("revert"), "Renaming a StreamField block")

    def test_excludes_other_sites(self):
        call_command("add_site", "labs.localhost", name="Studio Labs", stdout=StringIO())
        self.assertNotContains(self.search("revert", host="labs.localhost"), "Renaming a StreamField block")

    def test_queries_are_logged_and_promotions_shown(self):
        target = BlogPage.objects.get(slug="testing-every-live-page")
        SearchPromotion.objects.create(query=Query.get("upgrade"), page=target, description="Start here")
        response = self.search("Upgrade")
        self.assertContains(response, "Start here")
        self.assertEqual(Query.get("upgrade").hits, 1)  # queries are normalised: case and spacing

    def test_results_of_every_page_type_render(self):
        # PostgreSQL stems "upgrade" to match the "Django upgrades" service page; SQLite doesn't. Search for a
        # word in both page types' titles, so this test runs the mixed-results template on every database.
        response = self.search("wagtail")
        self.assertContains(response, "Wagtail development")  # a ServicePage
        self.assertContains(response, "Renaming a StreamField block")  # a BlogPage

    def test_autocomplete_matches_partial_words(self):
        data = self.client.get(reverse("search_autocomplete"), {"q": "rena"}).json()
        self.assertEqual([r["title"] for r in data["results"]], ["Renaming a StreamField block without losing content"])

    def test_update_index_rebuilds_everything(self):
        out = StringIO()
        call_command("update_index", stdout=out)
        self.assertIn("default: blog.BlogPage", out.getvalue())
        self.assertRegex(out.getvalue(), r"indexed \d+ objects")
        self.assertContains(self.search("revert"), "Renaming a StreamField block")  # still searchable afterwards
