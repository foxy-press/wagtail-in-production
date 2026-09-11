from wagtail.models import Page

from blog.models import BlogIndexPage, BlogPage
from core.blocks import body_faqs, body_headings
from core.models import fit_description
from core.testing import SeededSiteTestCase
from pages.models import HomePage, LegalPage, ServicePage, ServicesPage


class ArchitectureTests(SeededSiteTestCase):
    """Chapter 1: the page tree rules are the architecture, so test them."""

    def test_home_page_children(self):
        self.assertAllowedSubpageTypes(HomePage, {ServicesPage, LegalPage, BlogIndexPage})

    def test_leaf_pages_have_no_children(self):
        self.assertAllowedSubpageTypes(BlogPage, {})
        self.assertAllowedSubpageTypes(ServicePage, {})

    def test_home_pages_only_under_the_root(self):
        self.assertCanNotCreateAt(HomePage, HomePage)

    def test_seed_is_idempotent(self):
        from io import StringIO

        from django.core.management import call_command

        before = Page.objects.count()
        call_command("seed_site", stdout=StringIO())
        self.assertEqual(Page.objects.count(), before)


class RenderTests(SeededSiteTestCase):
    def test_every_live_page_renders(self):
        for page in Page.objects.live().specific().filter(depth__gt=1):
            with self.subTest(page=page.url_path):
                self.assertPageIsRenderable(page)

    def test_structured_data(self):
        post = BlogPage.objects.get(slug="renaming-streamfield-blocks")
        types = [item["@type"] for item in post.get_structured_data()]
        self.assertEqual(types, ["BlogPosting", "BreadcrumbList", "FAQPage"])


class StreamFieldHelperTests(SeededSiteTestCase):
    """Chapter 2: reading a stream in Python."""

    def test_table_of_contents(self):
        post = BlogPage.objects.get(slug="renaming-streamfield-blocks")
        self.assertEqual(
            body_headings(post.body),
            [("why-makemigrations-stays-silent", "Why makemigrations stays silent"), ("common-questions", "Common questions")],
        )

    def test_faqs_from_body(self):
        post = BlogPage.objects.get(slug="renaming-streamfield-blocks")
        self.assertEqual(body_faqs(post.body)[0]["question"], "Do old revisions need migrating?")

    def test_code_block_api_representation(self):
        post = BlogPage.objects.get(slug="renaming-streamfield-blocks")
        code = next(child for child in post.body if child.block_type == "code")
        data = code.block.get_api_representation(code.value)
        self.assertIn("highlighted", data)
        self.assertEqual(data["filename"], "blog/models.py")

    def test_block_id_in_template(self):
        post = BlogPage.objects.get(slug="renaming-streamfield-blocks")
        note = next(child for child in post.body if child.block_type == "note")
        html = self.client.get(post.url).content.decode()
        self.assertIn(f'id="block-{note.id}"', html)

    def test_fit_description(self):
        text = "First sentence is here. " * 10
        self.assertLessEqual(len(fit_description(text)), 160)
        self.assertTrue(fit_description(text).endswith("."))


class BlockUsageTests(SeededSiteTestCase):
    """Chapter 3: find every use of a block before renaming or removing it."""

    def test_counts_every_block_type(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("block_usage", stdout=out)
        self.assertIn("note", out.getvalue())
        self.assertIn("heading", out.getvalue())

    def test_lists_pages_using_a_block(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("block_usage", "note", stdout=out)
        self.assertIn("/renaming-streamfield-blocks/", out.getvalue())
        self.assertNotIn("/testing-every-live-page/", out.getvalue())
