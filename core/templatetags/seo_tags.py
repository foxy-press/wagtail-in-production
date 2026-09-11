import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# The same escapes Django's json_script uses, so page content can never close the <script> tag.
JSON_SCRIPT_ESCAPES = {ord(">"): "\\u003E", ord("<"): "\\u003C", ord("&"): "\\u0026"}


@register.filter
def jsonld(value):
    """Render structured data. Django's json_script writes type="application/json", which search engines ignore."""
    data = json.dumps(value, cls=DjangoJSONEncoder).translate(JSON_SCRIPT_ESCAPES)
    return format_html('<script type="application/ld+json">{}</script>', mark_safe(data))


@register.simple_tag(takes_context=True)
def og_image_url(context, page):
    """The page's sharing image, or the site-wide default, as an absolute 1200×630 JPEG URL."""
    image = getattr(page, "og_image", None)
    if image is None:
        site_settings = context.get("settings")
        image = site_settings.core.SiteSettings.default_og_image if site_settings else None
    if image is None:
        return ""
    return image.get_rendition("fill-1200x630|format-jpeg").full_url
