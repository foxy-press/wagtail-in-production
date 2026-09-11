import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command

from blog.importer import html_to_blocks
from blog.models import BlogPage
from core.testing import SeededSiteTestCase

LEGACY = """
<article>
  <h1>Moving to Wagtail</h1>
  <p>We moved from a <strong>static</strong> site. <span class="x">Here's how.</span></p>
  <h2 id="plan">The plan</h2>
  <ul><li>Export</li><li>Import</li></ul>
  <pre><code class="language-python">print("hello")</code></pre>
  <aside class="warning">Test on a copy first.</aside>
  <div class="comparison"><table><tr><td>Old</td><td>New</td></tr></table></div>
</article>
"""


class ApplyMetaTests(SeededSiteTestCase):
    """Chapter 6: the revision-safe edit pattern."""

    def run_command(self, meta, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(meta, f)
        out = StringIO()
        call_command("apply_meta", f.name, *args, stdout=out)
        return out.getvalue()

    def test_publishes_pages_with_no_pending_draft(self):
        output = self.run_command({"testing-every-live-page": {"search_description": "One loop catches most template errors."}})
        self.assertIn("published", output)
        page = BlogPage.objects.get(slug="testing-every-live-page")
        self.assertEqual(page.search_description, "One loop catches most template errors.")

    def test_never_publishes_over_an_editors_draft(self):
        page = BlogPage.objects.get(slug="testing-every-live-page")
        draft = page.get_latest_revision_as_object()
        draft.intro = "An editor's unfinished rewrite"
        draft.save_revision()

        output = self.run_command({"testing-every-live-page": {"seo_title": "Test every live page"}})
        self.assertIn("draft saved", output)
        page.refresh_from_db()
        self.assertEqual(page.seo_title, "")  # live page untouched
        latest = page.get_latest_revision_as_object()
        self.assertEqual(latest.seo_title, "Test every live page")
        self.assertEqual(latest.intro, "An editor's unfinished rewrite")  # the editor's work survives

    def test_dry_run_changes_nothing(self):
        before = BlogPage.objects.get(slug="testing-every-live-page").revisions.count()
        output = self.run_command({"testing-every-live-page": {"seo_title": "Changed"}}, "--dry-run")
        self.assertIn("would update", output)
        self.assertEqual(BlogPage.objects.get(slug="testing-every-live-page").revisions.count(), before)

    def test_rejects_long_titles_before_touching_anything(self):
        with self.assertRaises(CommandError):
            self.run_command({"testing-every-live-page": {"seo_title": "x" * 61}})


class LegacyImportTests(SeededSiteTestCase):
    def test_html_maps_to_blocks(self):
        types = [b["type"] for b in html_to_blocks(LEGACY)]
        self.assertEqual(types, ["paragraph", "heading", "paragraph", "code", "note", "html"])
        paragraph = html_to_blocks(LEGACY)[0]["value"]
        self.assertEqual(paragraph, "<p>We moved from a <b>static</b> site. Here's how.</p>")

    def test_import_creates_reviewable_drafts_once(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "moving-to-wagtail.html").write_text(LEGACY)
            call_command("import_legacy_html", directory, stdout=StringIO())
            call_command("import_legacy_html", directory, stdout=StringIO())
        pages = BlogPage.objects.filter(slug="moving-to-wagtail")
        self.assertEqual(pages.count(), 1)
        page = pages.get()
        self.assertEqual(page.title, "Moving to Wagtail")
        self.assertFalse(page.live)
        self.assertEqual(page.body[3].value["language"], "python")
        response = page.get_latest_revision_as_object().make_preview_request()  # what an editor sees in preview
        self.assertContains(response, "Test on a copy first.")
