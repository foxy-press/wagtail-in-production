from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import AdminOnlyMenuItem
from wagtail.admin.userbar import ContentCheckerItem
from wagtail.permissions import register_permission_policy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from core.models import PageView
from core.permissions import ReadOnlyPermissionPolicy
from core.views import MissingDescriptionReportView


@hooks.register("register_rich_text_features")
def enable_code(features):
    features.default_features.append("code")


class PageViewViewSet(SnippetViewSet):
    """Read-only analytics: the middleware writes rows, nobody edits them."""

    model = PageView
    icon = "view"
    menu_label = "Page views"
    menu_name = "page-views"
    list_display = ["day", "path", "count"]
    list_filter = ["day"]
    ordering = ["-day", "-count"]
    add_to_admin_menu = True
    # There is no add_view_enabled / edit_view_enabled / delete_view_enabled: Wagtail ignores them.
    # Read-only is a permission question, so answer it with a permission policy.
    permission_policy = ReadOnlyPermissionPolicy(PageView)
    copy_view_enabled = False
    inspect_view_enabled = False


# Wagtail 8.0: a custom permission_policy on a viewset must be registered, or it raises a deprecation warning.
register_permission_policy(PageView, PageViewViewSet.permission_policy)
register_snippet(PageViewViewSet)


@hooks.register("register_admin_urls")
def register_report_urls():
    return [
        path("reports/missing-descriptions/", MissingDescriptionReportView.as_view(), name="missing_descriptions"),
        path(
            "reports/missing-descriptions/results/",
            MissingDescriptionReportView.as_view(results_only=True),
            name="missing_descriptions_results",
        ),
    ]


@hooks.register("register_reports_menu_item")
def register_missing_descriptions_menu_item():
    return AdminOnlyMenuItem("Missing descriptions", reverse("missing_descriptions"), icon_name="search", order=700)


class StudioContentChecker(ContentCheckerItem):
    """Check only the main content: the header and footer are covered once, in the design system."""

    axe_include = ["main"]


@hooks.register("construct_wagtail_userbar")
def use_studio_content_checker(request, items, page):
    # Wagtail adds its checker as AccessibilityItem, a subclass of ContentCheckerItem, so match with isinstance.
    items[:] = [StudioContentChecker() if isinstance(item, ContentCheckerItem) else item for item in items]
