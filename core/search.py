from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from wagtail.contrib.search_promotions.models import Query
from wagtail.models import Page, Site

from core.models import BasePage

RESULTS_PER_PAGE = 10


def search(request):
    query = request.GET.get("q", "").strip()
    site = Site.find_for_request(request)
    promotions, results = [], Page.objects.none()
    if query:
        # Live, public pages on this site only: not drafts, not private pages, not another brand's pages.
        pages = Page.objects.live().public().descendant_of(site.root_page, inclusive=True).specific()
        results = pages.search(query)
        record = Query.get(query)
        record.add_hit()  # shows in Reports → Search terms, so editors see what people look for
        promotions = record.editors_picks.select_related("page").all()
    paginator = Paginator(results, RESULTS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    return render(
        request,
        "core/search.html",
        {"query": query, "results": paginator.get_page(page_number), "promotions": promotions},
    )


def autocomplete(request):
    """Titles for a search-as-you-type box: partial words match ("rena" finds "Renaming...")."""
    query = request.GET.get("q", "").strip()
    site = Site.find_for_request(request)
    pages = Page.objects.live().public().descendant_of(site.root_page).type(BasePage)
    matches = pages.autocomplete(query)[:8] if len(query) >= 2 else []
    return JsonResponse({"results": [{"title": page.title, "url": page.url} for page in matches]})
