import logging
import urllib.request

from django.conf import settings
from django.db import transaction
from django.dispatch import receiver
from wagtail.signals import page_published, page_unpublished

logger = logging.getLogger(__name__)


def request_frontend_rebuild(reason):
    """POST to the static host's deploy hook. Never let a slow or failing host break publishing."""
    try:
        request = urllib.request.Request(settings.FRONTEND_REBUILD_HOOK, data=reason.encode(), method="POST")
        urllib.request.urlopen(request, timeout=5).close()
    except OSError:
        logger.exception("Front-end rebuild hook failed (%s)", reason)


@receiver(page_published)
@receiver(page_unpublished)
def rebuild_frontend(sender, instance, **kwargs):
    if not settings.FRONTEND_REBUILD_HOOK:
        return
    reason = f"{instance.url_path} changed"
    # Wait for the publish transaction to commit, so the front end never builds from content that is rolled back.
    transaction.on_commit(lambda: request_frontend_rebuild(reason))
