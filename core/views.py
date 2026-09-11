from wagtail.admin.views.reports import PageReportView
from wagtail.models import Page


class MissingDescriptionReportView(PageReportView):
    """Live pages with no search description: the first thing an SEO audit finds (chapter 11)."""

    page_title = "Missing descriptions"
    header_icon = "search"
    index_url_name = "missing_descriptions"
    index_results_url_name = "missing_descriptions_results"

    def get_queryset(self):
        return Page.objects.live().filter(depth__gt=1, search_description="").order_by("title")
