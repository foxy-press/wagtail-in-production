import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from pages.models import Enquiry


class Command(BaseCommand):
    help = "Delete handled enquiries older than the retention period. Personal data shouldn't be kept forever."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=365)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, days, dry_run, **options):
        cutoff = timezone.now() - datetime.timedelta(days=days)
        old = Enquiry.objects.filter(handled=True, created_at__lt=cutoff)
        count = old.count()
        if not dry_run:
            old.delete()
        self.stdout.write(f"{'Would delete' if dry_run else 'Deleted'} {count} enquiries handled before {cutoff:%d %b %Y}")
