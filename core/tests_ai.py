import json
from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command
from wagtail.images.models import Image
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Comment

from blog.models import BlogPage
from core.ai_review import ai_findings, page_as_text
from core.testing import SeededSiteTestCase


def fake_response(findings, stop_reason="end_turn"):
    """The shape of a Messages API response, as far as ai_findings reads it."""
    text = SimpleNamespace(type="text", text=json.dumps({"findings": findings}))
    return SimpleNamespace(stop_reason=stop_reason, content=[text])


def fake_client(findings, stop_reason="end_turn"):
    client = mock.Mock()
    client.beta.messages.create.return_value = fake_response(findings, stop_reason)
    return client


class AiReviewTests(SeededSiteTestCase):
    """Chapter 12: the model advises, editors decide. Tests never call the API."""

    def setUp(self):
        self.post = BlogPage.objects.get(slug="renaming-streamfield-blocks")

    def test_blocks_are_numbered_for_the_model(self):
        text = page_as_text(self.post)
        self.assertIn("[1] (heading) Why makemigrations stays silent", text)
        self.assertIn("(code)", text)

    def test_findings_map_back_to_block_ids(self):
        client = fake_client([{"field": "body", "block": 2, "issue": "Says JSON without explaining it.", "suggestion": "Add one line on why."}])
        finding = ai_findings(self.post, client=client)[0]
        self.assertEqual(finding.contentpath, f"body.{self.post.body[1].id}")
        kwargs = client.beta.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-opus-5-5")
        self.assertEqual(kwargs["fallbacks"], "default")
        self.assertIn("<page>", kwargs["messages"][0]["content"])

    def test_refusal_returns_no_findings(self):
        self.assertEqual(ai_findings(self.post, client=fake_client([], stop_reason="refusal")), [])

    def test_command_comments_without_touching_content(self):
        image = Image.objects.create(title="IMG_0042.jpg", file=get_test_image_file())
        draft = self.post.get_latest_revision_as_object()
        draft.body = list(draft.body.raw_data) + [{"type": "image", "value": {"image": image.pk, "alt": "", "caption": ""}}]
        draft.save_revision()
        before_revision = self.post.latest_revision_id

        findings = [{"field": "intro", "block": None, "issue": "The intro assumes the reader knows StreamField.", "suggestion": "Name it."}]
        with mock.patch("core.ai_review.anthropic.Anthropic", return_value=fake_client(findings)):
            call_command("ai_review", stdout=StringIO())
            call_command("ai_review", stdout=StringIO())  # second run must not duplicate comments

        comments = Comment.objects.filter(page=self.post)
        self.assertEqual(sorted(c.text[:7] for c in comments), ["[ai] Th", "[check]"])
        self.assertTrue(any(c.contentpath.startswith("body.") for c in comments))
        self.post.refresh_from_db()
        self.assertEqual(self.post.latest_revision_id, before_revision)  # no new revision: content untouched
        self.assertFalse(comments.first().user.is_active)  # the reviewer account can't log in
