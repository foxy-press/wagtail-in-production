import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone


from blog.models import BlogPage
from core.testing import SeededSiteTestCase
from pages.models import Enquiry, LegalPage


def make_user(username, *groups):
    user = get_user_model().objects.create_user(username, f"{username}@example.com", "pw")
    user.groups.set(Group.objects.filter(name__in=groups))
    return user


class GroupPermissionTests(SeededSiteTestCase):
    """Chapter 5: the permission model, tested from each role's point of view."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("setup_groups", stdout=StringIO())
        cls.editor = make_user("eddie", "Editors")
        cls.moderator = make_user("mo", "Moderators")
        cls.sales = make_user("sam", "Sales")
        cls.post = BlogPage.objects.get(slug="testing-every-live-page")

    def test_editors_edit_but_cannot_publish(self):
        perms = self.post.permissions_for_user(self.editor)
        self.assertTrue(perms.can_edit())
        self.assertFalse(perms.can_publish())

    def test_moderators_publish(self):
        self.assertTrue(self.post.permissions_for_user(self.moderator).can_publish())

    def test_sales_see_the_inbox_but_no_pages(self):
        self.client.force_login(self.sales)
        self.assertEqual(self.client.get(reverse("enquiry:index")).status_code, 200)
        self.assertFalse(self.post.permissions_for_user(self.sales).can_edit())

    def test_editors_cannot_see_the_inbox(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse("enquiry:index")).status_code, 302)

    def test_setup_is_idempotent(self):
        call_command("setup_groups", stdout=StringIO())
        self.assertEqual(Group.objects.get(name="Editors").page_permissions.count(), 3)

    def test_legal_pages_go_through_legal_review(self):
        page = LegalPage.objects.get(slug="privacy")
        workflow = page.get_workflow()
        self.assertEqual(workflow.name, "Legal review")
        page.save_revision(user=self.editor)
        state = workflow.start(page, self.editor)
        self.assertEqual(state.current_task_state.task.specific.groups.get().name, "Legal")
        self.assertEqual(state.status, "in_progress")


class RegistryAndRetentionTests(SeededSiteTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("setup_groups", stdout=StringIO())
        cls.sales = make_user("sam", "Sales")
        cls.editor = make_user("eddie", "Editors")
        Enquiry.objects.create(name="Ada", email="ada@example.com", message="Hello")

    def test_export_checks_permission_through_the_registry(self):
        out = StringIO()
        call_command("export_enquiries", user="sam", stdout=out)
        self.assertIn("ada@example.com", out.getvalue())
        with self.assertRaises(CommandError):
            call_command("export_enquiries", user="eddie", stdout=StringIO())

    def test_purge_only_deletes_old_handled_enquiries(self):
        old = Enquiry.objects.create(name="Old", email="old@example.com", message="x", handled=True)
        Enquiry.objects.filter(pk=old.pk).update(created_at=timezone.now() - datetime.timedelta(days=400))
        unhandled = Enquiry.objects.create(name="Open", email="o@example.com", message="x")
        Enquiry.objects.filter(pk=unhandled.pk).update(created_at=timezone.now() - datetime.timedelta(days=400))
        call_command("purge_enquiries", stdout=StringIO())
        self.assertFalse(Enquiry.objects.filter(pk=old.pk).exists())
        self.assertTrue(Enquiry.objects.filter(pk=unhandled.pk).exists())
        self.assertTrue(Enquiry.objects.filter(name="Ada").exists())


