from django.core.management.base import BaseCommand
from wagtail.models import Site


class Command(BaseCommand):
    help = "Point the default Site at its real domain. Wagtail builds absolute URLs (canonical, sitemap, hreflang) from this."

    def add_arguments(self, parser):
        parser.add_argument("hostname")
        parser.add_argument("--port", type=int, default=443)
        parser.add_argument("--name", default="")

    def handle(self, hostname, port, name, **options):
        site = Site.objects.get(is_default_site=True)
        site.hostname, site.port = hostname, port
        if name:
            site.site_name = name
        site.save()
        self.stdout.write(self.style.SUCCESS(f"Default site is now {site.root_url}"))
