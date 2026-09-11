import importlib
import json

from django.apps import apps
from django.db import connection

from blog.models import BlogPage
from core.testing import SeededSiteTestCase

OLD_BODY = [
    {"type": "paragraph", "value": "<p>Before</p>", "id": "11111111-1111-1111-1111-111111111111"},
    {
        "type": "callout",
        "value": {"style": "warning", "text": "<p>Back up first.</p>"},
        "id": "22222222-2222-2222-2222-222222222222",
    },
]


class CalloutToNoteMigrationTests(SeededSiteTestCase):
    """Chapter 3: put old-shape data in the page and its revision, then run the real migration."""

    def setUp(self):
        self.post = BlogPage.objects.get(slug="testing-every-live-page")
        # Write the old JSON directly: the current block definitions would drop the unknown "callout" type.
        with connection.cursor() as cursor:
            cursor.execute("UPDATE blog_blogpage SET body = %s WHERE page_ptr_id = %s", [json.dumps(OLD_BODY), self.post.pk])
        revision = self.post.latest_revision
        revision.content["body"] = json.dumps(OLD_BODY)
        revision.save(update_fields=["content"])

    def run_migration(self):
        migration = importlib.import_module("blog.migrations.0003_callout_to_note").Migration
        migration.operations[0].migrate_stream_data_forward(apps, None)

    def test_page_and_revision_are_migrated(self):
        self.run_migration()
        post = BlogPage.objects.get(pk=self.post.pk)
        note = post.body[1]
        self.assertEqual(note.block_type, "note")
        self.assertEqual(note.value["tone"], "caution")
        self.assertEqual(note.id, "22222222-2222-2222-2222-222222222222")  # ids survive, so links to the block still work

        revision_body = json.loads(post.latest_revision.content["body"])
        self.assertEqual(revision_body[1]["type"], "note")
        self.assertEqual(revision_body[1]["value"], {"tone": "caution", "text": "<p>Back up first.</p>"})

    def test_running_twice_changes_nothing(self):
        self.run_migration()
        once = list(BlogPage.objects.get(pk=self.post.pk).body.raw_data)
        self.run_migration()
        self.assertEqual(list(BlogPage.objects.get(pk=self.post.pk).body.raw_data), once)

    def test_migrated_page_renders(self):
        self.run_migration()
        self.assertPageIsRenderable(BlogPage.objects.get(pk=self.post.pk))

    def test_block_usage_finds_blocks_the_code_no_longer_defines(self):
        from io import StringIO

        from django.core.management import call_command

        for args in (["callout"], ["callout", "--drafts"]):
            out = StringIO()
            call_command("block_usage", *args, stdout=out)
            self.assertIn("/testing-every-live-page/", out.getvalue(), args)
