from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from wagtail.models import Comment

from blog.models import BlogPage
from core.ai_review import ai_findings, deterministic_checks

REVIEWER_USERNAME = "ai-reviewer"


class Command(BaseCommand):
    help = "Review articles with unpublished changes and leave comments for editors. Never edits or publishes."

    def add_arguments(self, parser):
        parser.add_argument("--slug", help="Review one article, even with no pending draft")
        parser.add_argument("--no-ai", action="store_true", help="Run only the deterministic checks")

    def handle(self, slug=None, no_ai=False, **options):
        reviewer, _ = get_user_model().objects.get_or_create(username=REVIEWER_USERNAME, defaults={"is_active": False})
        pages = BlogPage.objects.filter(slug=slug) if slug else BlogPage.objects.filter(has_unpublished_changes=True)
        for page in pages:
            draft = page.get_latest_revision_as_object()
            findings = deterministic_checks(draft) + ([] if no_ai else ai_findings(draft))
            # Don't repeat a comment the reviewer already left and nobody has resolved.
            open_texts = set(Comment.objects.filter(page=page, user=reviewer, resolved_at__isnull=True).values_list("text", flat=True))
            new = [f for f in findings if f"[{f.source}] {f.text}" not in open_texts]
            Comment.objects.bulk_create(
                Comment(page=page, user=reviewer, contentpath=f.contentpath, text=f"[{f.source}] {f.text}", revision_created=page.latest_revision)
                for f in new
            )
            self.stdout.write(f"{len(new):>3} new comments  {page.url_path}")
