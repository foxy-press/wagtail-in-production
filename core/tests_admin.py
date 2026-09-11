from django.contrib.auth import get_user_model
from django.urls import reverse
from wagtail.admin.admin_url_finder import AdminURLFinder

from blog.models import BlogPage
from core.models import PageView
from core.testing import SeededSiteTestCase
from pages.models import Enquiry


class AdminScreenTests(SeededSiteTestCase):
    """Chapter 4: every custom admin screen loads, and read-only screens stay read-only."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "pw")
        Enquiry.objects.create(name="Ada", email="ada@example.com", message="Can you upgrade us to 8.3?")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_custom_screens_load(self):
        for name in [
            "wagtailsnippets_core_pageview:list",
            "wagtailsnippets_blog_topic:list",
            "enquiry:index",
            "newslettersignup:index",
            "missing_descriptions",
        ]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_articles_listing(self):
        response = self.client.get(reverse("articles:index"))
        self.assertContains(response, "Renaming a StreamField block")

    def test_page_views_are_read_only(self):
        PageView.objects.create(day="2027-01-01", path="/", count=3)
        response = self.client.get(reverse("wagtailsnippets_core_pageview:list"))
        self.assertNotContains(response, reverse("wagtailsnippets_core_pageview:add"))

    def test_enquiry_edit_form_only_offers_handled(self):
        enquiry = Enquiry.objects.get()
        response = self.client.get(reverse("enquiry:edit", args=[enquiry.pk]))
        self.assertContains(response, 'name="handled"')
        self.assertNotContains(response, 'name="message"')

    def test_report_lists_pages_without_descriptions(self):
        response = self.client.get(reverse("missing_descriptions"))
        self.assertContains(response, "Testing every live page")

    def test_page_views_cannot_be_edited_even_by_a_superuser(self):
        row = PageView.objects.create(day="2027-01-01", path="/", count=3)
        self.assertEqual(self.client.get(reverse("wagtailsnippets_core_pageview:edit", args=[row.pk])).status_code, 302)
        self.assertEqual(self.client.get(reverse("wagtailsnippets_core_pageview:add")).status_code, 302)

    def test_stale_article_warning(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        BlogPage.objects.filter(pk=post.pk).update(date="2020-01-01", updated=None)
        response = self.client.get(reverse("wagtailadmin_pages:edit", args=[post.pk]), follow=True)
        self.assertContains(response, "Last reviewed 01 January 2020")
        self.assertTrue(AdminURLFinder(self.admin).get_edit_url(post))

    def test_new_article_date_is_prefilled(self):
        blog = BlogPage.objects.first().get_parent()
        response = self.client.get(reverse("wagtailadmin_pages:add", args=["blog", "blogpage", blog.pk]))
        from django.utils import timezone

        self.assertContains(response, timezone.localdate().isoformat())

    def test_userbar_shows_read_time_on_articles(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        self.assertContains(self.client.get(post.url), "min read")


class PageViewMiddlewareTests(SeededSiteTestCase):
    def test_counts_public_pages_once_per_request(self):
        self.client.get("/writing/")
        self.client.get("/writing/")
        self.assertEqual(PageView.objects.get(path="/writing/").count, 2)

    def test_ignores_admin_and_errors(self):
        self.client.get("/studio-admin/login/")
        self.client.get("/no-such-page/")
        self.assertFalse(PageView.objects.exists())
