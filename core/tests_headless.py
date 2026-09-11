import os
import shutil
import subprocess
import tempfile
import unittest
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import LiveServerTestCase, override_settings
from wagtail.images.tests.utils import get_test_image_file
from wagtail.images.models import Image

from blog.models import BlogPage
from core.testing import SeededSiteTestCase


class V2ContractTests(SeededSiteTestCase):
    """Chapter 7: the API shape the front end depends on. If this test changes, the front end must too."""

    def test_list_posts(self):
        data = self.client.get("/api/v2/pages/", {"type": "blog.BlogPage", "fields": "intro,date,topic_name"}).json()
        self.assertEqual(data["meta"]["total_count"], 2)
        post = data["items"][0]
        self.assertEqual(set(post) - {"meta"}, {"id", "title", "intro", "date", "topic_name"})
        self.assertTrue(post["meta"]["html_url"].endswith("/writing/renaming-streamfield-blocks/")
                        or post["meta"]["html_url"].endswith("/writing/testing-every-live-page/"))

    def test_detail_body_is_ready_to_render(self):
        post = BlogPage.objects.get(slug="renaming-streamfield-blocks")
        image = Image.objects.create(title="Diagram", file=get_test_image_file())
        body = list(post.body.raw_data) + [
            {"type": "image", "value": {"image": image.pk, "alt": "How the parts fit", "decorative": False, "caption": "How it fits"}},
            {"type": "image", "value": {"image": image.pk, "alt": "", "decorative": True, "caption": ""}},
        ]
        post.body = body
        post.save_revision().publish()

        data = self.client.get(f"/api/v2/pages/{post.pk}/").json()
        images = [block["value"] for block in data["body"] if block["type"] == "image"]
        blocks = {block["type"]: block["value"] for block in data["body"]}
        self.assertIn("highlighted", blocks["code"])
        self.assertTrue(blocks["image"]["src"].startswith("http"))
        self.assertTrue(blocks["image"]["src"].endswith(".webp"))
        self.assertEqual([image["alt"] for image in images], ["How the parts fit", ""])  # decorative: empty alt
        self.assertEqual(data["read_minutes"], 1)

    def test_drafts_are_not_exposed(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        post.unpublish()
        data = self.client.get("/api/v2/pages/", {"type": "blog.BlogPage"}).json()
        self.assertEqual(data["meta"]["total_count"], 1)


class RebuildHookTests(SeededSiteTestCase):
    @override_settings(FRONTEND_REBUILD_HOOK="https://hooks.example/deploy")
    def test_publishing_requests_a_rebuild_after_commit(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        with mock.patch("core.signals.urllib.request.urlopen") as urlopen:
            with self.captureOnCommitCallbacks(execute=True):
                post.save_revision().publish()
        urlopen.assert_called_once()
        self.assertEqual(urlopen.call_args.args[0].full_url, "https://hooks.example/deploy")

    @override_settings(FRONTEND_REBUILD_HOOK="https://hooks.example/deploy")
    def test_a_failing_hook_never_breaks_publishing(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        with mock.patch("core.signals.urllib.request.urlopen", side_effect=OSError("timeout")):
            with self.captureOnCommitCallbacks(execute=True):
                post.save_revision().publish()
        post.refresh_from_db()
        self.assertTrue(post.live)

    def test_no_hook_configured_means_no_request(self):
        post = BlogPage.objects.get(slug="testing-every-live-page")
        with mock.patch("core.signals.urllib.request.urlopen") as urlopen:
            with self.captureOnCommitCallbacks(execute=True):
                post.save_revision().publish()
        urlopen.assert_not_called()



@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class FrontendBuildTests(LiveServerTestCase):
    """Run the real Node front-end build against a live Wagtail server."""

    def test_static_build(self):
        call_command("seed_site", stdout=StringIO())
        with tempfile.TemporaryDirectory() as out:
            env = {**os.environ, "CMS_URL": self.live_server_url, "OUT_DIR": out}
            result = subprocess.run(["node", "frontend/build.mjs"], env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(os.path.join(out, "renaming-streamfield-blocks", "index.html")) as f:
                html = f.read()
        self.assertIn('<aside class="note note-caution">', html)
        self.assertIn('class="tok-n"', html)
