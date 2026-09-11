from django.urls import reverse
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.test.utils.form_data import nested_form_data, querydict_from_html, rich_text, streamfield

from blog.models import BlogIndexPage, BlogPage, Topic
from core.testing import SeededSiteTestCase


def article_form_data(title, topic):
    """POST data for the BlogPage editor, built with Wagtail's form-data helpers."""
    return nested_form_data({
        "title": title,
        "topic": topic.pk,
        "intro": "Written through the real admin form.",
        "date": "2027-04-01",
        "author_name": "Studio team",
        "body": streamfield([
            ("heading", {"text": "Why", "level": "h2", "anchor": ""}),
            ("paragraph", rich_text("<p>Because the form is the contract.</p>")),
            ("note", {"tone": "tip", "text": rich_text("<p>Use the helpers.</p>")}),
        ]),
        "faqs": streamfield([]),
    })


class EditorTests(SeededSiteTestCase):
    """Chapter 13: the admin forms work, tested the way an editor uses them."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.blog = BlogIndexPage.objects.get()
        cls.topic = Topic.objects.get(slug="wagtail")

    def setUp(self):
        self.admin = self.login()  # WagtailTestUtils: creates a superuser and logs in

    def test_an_editor_can_create_an_article(self):
        self.assertCanCreate(self.blog, BlogPage, article_form_data("Created in a test", self.topic))
        page = BlogPage.objects.get(slug="created-in-a-test")
        self.assertTrue(page.live)
        self.assertEqual([child.block_type for child in page.body], ["heading", "paragraph", "note"])

    def test_every_page_type_opens_in_the_editor(self):
        for page in Page.objects.filter(depth__gt=1).specific():
            with self.subTest(page=page.url_path):
                self.assertPageIsEditable(page, post_data=self.edit_data(page))

    def test_articles_preview(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        # StreamFields are drawn by JavaScript in the editor, so the helper can't read their data from the
        # edit page's HTML. Pass the POST data yourself.
        self.assertPageIsPreviewable(post, post_data=article_form_data(post.title, self.topic))

    def edit_data(self, page):
        """POST data for any page's editor: the form's own HTML, plus an empty value for each optional StreamField.

        StreamFields are drawn by JavaScript, so their data isn't in the HTML. Pages whose StreamFields are
        required (BlogPage.body) need real block data instead.
        """
        if isinstance(page, BlogPage):
            return article_form_data(page.title, self.topic)
        # assertPageIsEditable logs its own user in and out, so log back in before reading the form.
        self.client.force_login(self.admin)
        html = self.client.get(reverse("wagtailadmin_pages:edit", args=[page.pk])).content.decode()
        data = querydict_from_html(html, form_id="page-edit-form")
        for field in page._meta.get_fields():
            if isinstance(field, StreamField) and f"{field.name}-count" not in data:
                data[f"{field.name}-count"] = "0"
        return data
