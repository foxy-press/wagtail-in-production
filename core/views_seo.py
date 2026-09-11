from django.http import HttpResponse
from django.views.decorators.http import require_GET
from wagtail.models import Site


@require_GET
def robots_txt(request):
    """One robots.txt per site, pointing at that site's sitemap."""
    site = Site.find_for_request(request)
    lines = [
        "User-agent: *",
        "Disallow: /search/",
        f"Sitemap: {site.root_url}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
