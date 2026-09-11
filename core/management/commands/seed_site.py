import datetime
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page, Site

from blog.models import BlogIndexPage, BlogPage, Topic
from pages.models import HomePage, LegalPage, ServicePage, ServicesPage


def block(block_type, value):
    return {"type": block_type, "value": value, "id": str(uuid.uuid4())}


POSTS = [
    {
        "title": "Renaming a StreamField block without losing content",
        "slug": "renaming-streamfield-blocks",
        "topic": "wagtail",
        "intro": "makemigrations can't see inside a StreamField, so a rename needs a data migration.",
        "date": datetime.date(2027, 1, 12),
        "body": [
            block("heading", {"text": "Why makemigrations stays silent", "level": "h2", "anchor": ""}),
            block("paragraph", "<p>StreamField stores JSON. Django sees one column whose type never changes.</p>"),
            block("code", {"filename": "blog/models.py", "language": "python", "code": "note = NoteBlock()"}),
            block("note", {"tone": "caution", "text": "<p>Migrate old revisions too.</p>"}),
            block("heading", {"text": "Common questions", "level": "h2", "anchor": ""}),
            block("heading", {"text": "Do old revisions need migrating?", "level": "h3", "anchor": ""}),
            block("paragraph", "<p>Yes, or compare and revert will break for older revisions.</p>"),
        ],
    },
    {
        "title": "Testing every live page in one test",
        "slug": "testing-every-live-page",
        "topic": "testing",
        "intro": "One loop over the page tree catches most template errors before your users do.",
        "date": datetime.date(2027, 2, 3),
        "body": [block("paragraph", "<p>Render every live page and check for a 200.</p>")],
    },
]


class Command(BaseCommand):
    help = "Build the Studio demo site. Safe to run repeatedly: existing pages are left alone."

    @transaction.atomic
    def handle(self, **options):
        root = Page.get_first_root_node()
        home = HomePage.objects.first()
        if home is None:
            # Replace the "Welcome to your new Wagtail site!" page that the initial migration creates.
            Page.objects.filter(depth=2, content_type__model="page").delete()
            home = root.add_child(
                instance=HomePage(title="Studio", slug="home", hero_title="Django and Wagtail sites", hero_highlight="that last")
            )
            Site.objects.update_or_create(is_default_site=True, defaults={"hostname": "localhost", "root_page": home})

        services = ServicesPage.objects.first() or home.add_child(
            instance=ServicesPage(title="Services", slug="services", hero_title="What we do")
        )
        for slug, title in [("wagtail-development", "Wagtail development"), ("django-upgrades", "Django upgrades")]:
            if not ServicePage.objects.filter(slug=slug).exists():
                services.add_child(instance=ServicePage(title=title, slug=slug, hero_title=title))

        if not LegalPage.objects.filter(slug="privacy").exists():
            home.add_child(instance=LegalPage(title="Privacy", slug="privacy", body="<p>We keep very little.</p>"))

        blog = BlogIndexPage.objects.first() or home.add_child(
            instance=BlogIndexPage(title="Writing", slug="writing", hero_title="Notes from production")
        )
        for post in POSTS:
            if BlogPage.objects.filter(slug=post["slug"]).exists():
                continue
            topic, _ = Topic.objects.get_or_create(slug=post["topic"], defaults={"name": post["topic"].title()})
            fields = {key: value for key, value in post.items() if key != "topic"}
            page = blog.add_child(instance=BlogPage(topic=topic, **fields))
            page.save_revision().publish()

        self.stdout.write(self.style.SUCCESS(f"Studio site ready: {Page.objects.live().count()} live pages"))
