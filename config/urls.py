from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.api.v3.urls import api as api_v3

from config.api import api_router
from core import search
from core.views_seo import robots_txt
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path(settings.WAGTAIL_ADMIN_PATH, include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("sitemap.xml", sitemap),
    path("robots.txt", robots_txt),
    # The docs suggest this mount while v3 is a preview, so clients know it may change.
    path("api/v3-preview/", api_v3.urls),
    path("api/v2/", api_router.urls),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# English stays at the root (/writing/), Welsh is under /cy/ (/cy/writing/).
urlpatterns += i18n_patterns(
    path("search/", search.search, name="search"),
    path("search/autocomplete/", search.autocomplete, name="search_autocomplete"),
    path("", include(wagtail_urls)),
    prefix_default_language=False,
)
