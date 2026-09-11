from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import (
    Collection,
    GroupApprovalTask,
    GroupCollectionPermission,
    GroupPagePermission,
    Page,
    Site,
    Workflow,
    WorkflowPage,
    WorkflowTask,
)

# Page permissions are granted on a page and apply to it and everything below it.
PAGE_PERMISSIONS = {
    "Editors": ["add", "change", "lock"],
    "Moderators": ["add", "change", "lock", "publish", "unlock", "bulk_delete"],
}
# Image and document permissions are granted per collection.
COLLECTION_PERMISSIONS = {
    "Editors": ["add_image", "change_image", "choose_image", "add_document", "change_document", "choose_document"],
    "Moderators": ["add_image", "change_image", "delete_image", "choose_image",
                   "add_document", "change_document", "delete_document", "choose_document"],
}
# Ordinary Django model permissions, as "app_label.codename".
MODEL_PERMISSIONS = {
    "Editors": ["blog.add_topic", "blog.change_topic", "blog.view_topic"],
    "Moderators": ["blog.add_topic", "blog.change_topic", "blog.delete_topic", "blog.view_topic", "core.view_pageview"],
    "Sales": ["pages.view_enquiry", "pages.change_enquiry", "pages.view_newslettersignup"],
    "Legal": [],
}


def permission(dotted):
    app_label, codename = dotted.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


class Command(BaseCommand):
    help = "Create Studio's editor groups, their permissions and the legal review workflow. Safe to run repeatedly."

    @transaction.atomic
    def handle(self, **options):
        # Not HomePage.objects.get(): with several sites or locales there is more than one home page (chapter 8).
        home = Site.objects.get(is_default_site=True).root_page
        root_collection = Collection.get_first_root_node()
        access_admin = permission("wagtailadmin.access_admin")

        for name in MODEL_PERMISSIONS:
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.add(access_admin, *[permission(p) for p in MODEL_PERMISSIONS[name]])
            # Wagtail's first migration already creates "Editors" and "Moderators" with permissions on the
            # root page. Make each group match this definition exactly, rather than adding to whatever is there.
            wanted = [permission(f"wagtailcore.{permission_type}_page") for permission_type in PAGE_PERMISSIONS.get(name, [])]
            GroupPagePermission.objects.filter(group=group).exclude(page=home, permission__in=wanted).delete()
            for page_permission in wanted:
                GroupPagePermission.objects.get_or_create(group=group, page=home, permission=page_permission)
            for codename in COLLECTION_PERMISSIONS.get(name, []):
                app_label = "wagtailimages" if codename.endswith("image") else "wagtaildocs"
                GroupCollectionPermission.objects.get_or_create(
                    group=group, collection=root_collection, permission=permission(f"{app_label}.{codename}")
                )

        self.setup_legal_review(home)
        self.stdout.write(self.style.SUCCESS("Groups and workflows ready"))

    def setup_legal_review(self, home):
        """Legal pages need sign-off from the Legal group before they go live."""
        workflow, _ = Workflow.objects.get_or_create(name="Legal review")
        task, created = GroupApprovalTask.objects.get_or_create(name="Legal approval")
        if created:
            task.groups.set([Group.objects.get(name="Legal")])
            WorkflowTask.objects.create(workflow=workflow, task=task, sort_order=0)
        LegalPage = apps.get_model("pages", "LegalPage")
        for page in LegalPage.objects.child_of(home):
            WorkflowPage.objects.update_or_create(page=page, defaults={"workflow": workflow})
