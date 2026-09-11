import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Page

TITLE_LIMIT = 60
DESCRIPTION_LIMIT = 160
LIMITS = {"seo_title": TITLE_LIMIT, "search_description": DESCRIPTION_LIMIT}


class Command(BaseCommand):
    help = "Apply SEO titles and descriptions from a JSON file keyed by slug. Never publishes over an editor's draft."

    def add_arguments(self, parser):
        parser.add_argument("path", help='JSON like {"slug": {"seo_title": "...", "search_description": "..."}}')
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, path, dry_run, **options):
        with open(path) as f:
            meta = json.load(f)
        for field, limit in LIMITS.items():
            too_long = [slug for slug, values in meta.items() if len(values.get(field, "")) > limit]
            if too_long:
                raise CommandError(f"{field} over {limit} characters for: {', '.join(too_long)}")

        for page in Page.objects.filter(slug__in=meta).specific():
            # Decide before saving: with no pending draft, get_latest_revision_as_object() returns the page
            # itself, and save_revision() then sets has_unpublished_changes on it.
            safe_to_publish = page.live and not page.has_unpublished_changes
            draft = page.get_latest_revision_as_object()  # start from the newest version, draft or live
            changed = [field for field, value in meta[page.slug].items() if getattr(draft, field) != value]
            if not changed:
                continue
            for field in changed:
                setattr(draft, field, meta[page.slug][field])
            if dry_run:
                action = "would update"
            else:
                revision = draft.save_revision(log_action=True)
                if safe_to_publish:
                    revision.publish()
                    action = "published"
                else:
                    action = "draft saved"  # an editor has unpublished work here: leave publishing to them
            self.stdout.write(f"{action:>13}  {page.url_path}  ({', '.join(changed)})")
        if dry_run:
            transaction.set_rollback(True)
