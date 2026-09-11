import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from blog.models import BlogIndexPage, BlogPage
from core.testing import SeededSiteTestCase

API = "/api/v3-preview"


class V3ApiTests(SeededSiteTestCase):
    """Chapter 6: create, publish and read an article through the v3 API, as a real editor would."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("setup_groups", stdout=StringIO())
        cls.importer = get_user_model().objects.create_user("importer", "importer@example.com", "pw")
        cls.importer.groups.set([Group.objects.get(name="Moderators")])
        out = StringIO()
        call_command("api_tokens", "create", "--user", "importer", "--name", "legacy import", stdout=out)
        cls.token = out.getvalue().strip()
        cls.blog = BlogIndexPage.objects.get()

    def api(self, method, path, data=None):
        return getattr(self.client, method)(
            API + path,
            data=json.dumps(data) if data is not None else None,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def create_draft(self):
        return self.api("post", "/pages/", {
            "meta": {"type": "blog.BlogPage", "parent_id": self.blog.pk},
            "title": "Upgrading to Wagtail 8.3",
            "slug": "upgrading-wagtail-8-3",
            "intro": "What changes between the 7.4 and 8.3 LTS releases.",
            "date": "2027-05-10",
            "body": [
                {"type": "paragraph", "value": "<p>Start with the <b>release notes</b>.</p>"},
                {"type": "note", "value": {"tone": "caution", "text": "<p>Back up first.</p>"}},
            ],
        })

    def test_create_draft_then_publish(self):
        response = self.create_draft()
        self.assertEqual(response.status_code, 201, response.content)
        page_id = response.json()["id"]
        page = BlogPage.objects.get(pk=page_id)
        self.assertFalse(page.live)                       # created as a draft: no "action": "publish"
        self.assertEqual(page.latest_revision.user, self.importer)

        response = self.api("post", f"/pages/{page_id}/actions/publish/")
        self.assertEqual(response.status_code, 200, response.content)
        page.refresh_from_db()
        self.assertTrue(page.live)
        self.assertEqual([child.block_type for child in page.body], ["paragraph", "note"])
        self.assertContains(self.client.get(page.url), "Back up first.")

    def test_read_back_includes_body(self):
        page_id = self.create_draft().json()["id"]
        data = self.api("get", f"/pages/{page_id}/").json()
        self.assertEqual(data["intro"], "What changes between the 7.4 and 8.3 LTS releases.")
        self.assertEqual(data["body"][1]["type"], "note")

    def test_requires_a_token(self):
        response = self.client.post(API + "/pages/", data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_editor_token_cannot_publish(self):
        editor = get_user_model().objects.create_user("eddie", "e@example.com", "pw")
        editor.groups.set([Group.objects.get(name="Editors")])
        out = StringIO()
        call_command("api_tokens", "create", "--user", "eddie", "--name", "eddie", stdout=out)
        self.token, moderator_token = out.getvalue().strip(), self.token
        page_id = self.create_draft().json()["id"]
        self.assertEqual(self.api("post", f"/pages/{page_id}/actions/publish/").status_code, 403)
        self.token = moderator_token
