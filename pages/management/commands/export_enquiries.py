import csv

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from wagtail.permissions import policy_registry

from pages.models import Enquiry


class Command(BaseCommand):
    help = "Write enquiries as CSV, on behalf of a user who is allowed to see them."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="The username to check permissions for")

    def handle(self, user, **options):
        account = get_user_model().objects.get(username=user)
        # The same policy the admin uses, found without importing the viewset (Wagtail 8.0 registry).
        policy = policy_registry.get_by_type(Enquiry)
        if not policy.user_has_permission(account, "view"):
            raise CommandError(f"{user} may not view enquiries")
        writer = csv.writer(self.stdout)
        writer.writerow(["created_at", "name", "email", "handled"])
        for enquiry in Enquiry.objects.order_by("created_at"):
            writer.writerow([enquiry.created_at.isoformat(), enquiry.name, enquiry.email, enquiry.handled])
