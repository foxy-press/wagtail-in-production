from django.conf import settings
from django.db.models import F
from django.utils import timezone

from core.models import PageView

SKIP_PREFIXES = ("/static/", "/media/", "/documents/", "/django-admin/")


class PageViewMiddleware:
    """Count successful GET requests for public HTML pages, one row per path per day."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.skip = SKIP_PREFIXES + ("/" + settings.WAGTAIL_ADMIN_PATH,)

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method == "GET"
            and response.status_code == 200
            and response.get("Content-Type", "").startswith("text/html")
            and not request.path.startswith(self.skip)
            and not getattr(request, "is_preview", False)
        ):
            today = timezone.localdate()
            updated = PageView.objects.filter(day=today, path=request.path).update(count=F("count") + 1)
            if not updated:
                PageView.objects.get_or_create(day=today, path=request.path, defaults={"count": 1})
        return response
