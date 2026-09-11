import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from blog.importer import html_to_blocks, intro_from
from blog.models import BlogIndexPage, BlogPage


class Command(BaseCommand):
    help = "Import legacy articles (one .html file per article, named <slug>.html) as draft BlogPages."

    def add_arguments(self, parser):
        parser.add_argument("directory")

    @transaction.atomic
    def handle(self, directory, **options):
        # The default language's blog: other locales have their own BlogIndexPage (chapter 8).
        blog = BlogIndexPage.objects.get(locale=Locale.get_default())
        created = 0
        for path in sorted(Path(directory).glob("*.html")):
            slug = path.stem
            if BlogPage.objects.filter(slug=slug).exists():
                continue  # idempotent: re-running skips what is already imported
            html = path.read_text()
            title = (html.split("<h1>", 1)[1].split("</h1>", 1)[0] if "<h1>" in html else slug.replace("-", " ").title())
            page = BlogPage(title=title, slug=slug, intro=intro_from(html), date=datetime.date.today(), body=html_to_blocks(html), live=False)
            blog.add_child(instance=page)
            page.save_revision(log_action=True)  # a draft for an editor to review, with an audit log entry
            created += 1
        self.stdout.write(f"Imported {created} articles as drafts")
