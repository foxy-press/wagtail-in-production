import datetime
from unittest import mock

from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from wagtail.images.models import Image
from wagtail.images.tests.utils import get_test_image_file

from blog.models import BlogIndexPage, BlogPage, Topic
from core.testing import SeededSiteTestCase


def add_posts(count):
    blog = BlogIndexPage.objects.get()
    topic = Topic.objects.create(name="Extra", slug="extra")
    for i in range(count):
        blog.add_child(instance=BlogPage(
            title=f"Post {i}", slug=f"post-{i}", intro="…", date=datetime.date(2027, 3, 1), topic=topic,
            body=[{"type": "paragraph", "value": "<p>" + "word " * 2000 + "</p>"}],
        ))


class QueryCountTests(SeededSiteTestCase):
    """Chapter 10: the listing costs the same number of queries for 2 posts or 22."""

    def count_queries(self, url):
        cache.clear()
        self.client.get(url)  # warm up: the first request creates settings rows and today's page-view row
        cache.clear()
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.client.get(url).status_code, 200)
        return len(queries)

    def test_blog_index_has_no_n_plus_one(self):
        before = self.count_queries("/writing/")
        add_posts(20)
        self.assertEqual(self.count_queries("/writing/"), before)

    def test_listing_does_not_load_bodies(self):
        add_posts(1)
        page = BlogIndexPage.objects.get()
        posts = page.get_context(self.client.get("/writing/").wsgi_request)["posts"]
        self.assertIn("body", posts[0].get_deferred_fields())


class FragmentCacheTests(SeededSiteTestCase):
    def test_body_cache_is_invalidated_by_publishing(self):
        cache.clear()
        post = BlogPage.objects.get(slug="testing-every-live-page")
        self.assertContains(self.client.get(post.url), "Render every live page")
        post.body = [{"type": "paragraph", "value": "<p>Rewritten intro.</p>"}]
        post.save_revision().publish()
        response = self.client.get(post.url)
        self.assertContains(response, "Rewritten intro.")  # page.cache_key changed, so the fragment re-rendered
        self.assertNotContains(response, "Render every live page")


class RenditionTests(SeededSiteTestCase):
    def test_picture_offers_avif_webp_and_jpeg(self):
        image = Image.objects.create(title="Diagram", file=get_test_image_file())
        post = BlogPage.objects.get(slug="testing-every-live-page")
        post.body = [{"type": "image", "value": {"image": image.pk, "alt": "A diagram", "caption": ""}}]
        post.save_revision().publish()
        html = self.client.get(post.url).content.decode()
        self.assertIn('type="image/avif"', html)
        self.assertIn('type="image/webp"', html)
        self.assertIn('alt="A diagram"', html)
        self.assertIn('loading="lazy"', html)


class FrontendCacheTests(SeededSiteTestCase):
    @override_settings(WAGTAILFRONTENDCACHE={
        "varnish": {"BACKEND": "wagtail.contrib.frontend_cache.backends.HTTPBackend", "LOCATION": "http://cache.internal"}
    })
    def test_publishing_purges_the_page(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        with mock.patch("wagtail.contrib.frontend_cache.backends.http.urlopen") as urlopen:
            post.save_revision().publish()
        purged = [call.args[0].full_url for call in urlopen.call_args_list]
        self.assertIn("http://cache.internal/writing/testing-every-live-page/", purged)
