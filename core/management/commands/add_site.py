from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page, Site

from core.models import BrandSettings


class Command(BaseCommand):
    help = "Add a second brand: its own home page, Site record and brand settings. Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument("hostname")
        parser.add_argument("--name", required=True)
        parser.add_argument("--accent", default="#2d6cdf")

    @transaction.atomic
    def handle(self, hostname, name, accent, **options):
        from pages.models import HomePage  # core must not import other apps at module level (chapter 1)

        site = Site.objects.filter(hostname=hostname).first()
        if site is None:
            home = Page.get_first_root_node().add_child(
                instance=HomePage(title=name, slug=hostname.split(".")[0], hero_title=name)
            )
            site = Site.objects.create(hostname=hostname, port=80, site_name=name, root_page=home)
        BrandSettings.objects.update_or_create(site=site, defaults={"brand_name": name, "accent_colour": accent})
        self.stdout.write(self.style.SUCCESS(f"{name} is served at http://{hostname}/"))
