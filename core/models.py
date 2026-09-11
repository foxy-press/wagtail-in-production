from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import format_html, strip_tags
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, BaseSiteSetting, register_setting
from wagtail.models import Page

TITLE_LIMIT = 60
DESCRIPTION_LIMIT = 160


@register_setting(icon="cog")
class SiteSettings(BaseGenericSetting):
    """Values every template needs. Generic, because Studio is a single brand (see chapter 8 for per-site settings)."""

    organisation_name = models.CharField(max_length=100, default="Studio")
    contact_email = models.EmailField(blank=True)
    default_og_image = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    panels = [
        MultiFieldPanel([FieldPanel("organisation_name"), FieldPanel("contact_email")], heading="Organisation"),
        FieldPanel("default_og_image"),
    ]

    class Meta:
        verbose_name = "Site settings"


@register_setting(icon="site")
class BrandSettings(BaseSiteSetting):
    """Values that differ per site (chapter 8): each brand has its own name, tagline and accent colour."""

    brand_name = models.CharField(max_length=60, default="Studio")
    tagline = models.CharField(max_length=120, blank=True)
    accent_colour = models.CharField(max_length=7, default="#f5c518", help_text="A hex colour, e.g. #f5c518")

    panels = [FieldPanel("brand_name"), FieldPanel("tagline"), FieldPanel("accent_colour")]


def fit_description(text, limit=DESCRIPTION_LIMIT):
    """Trim text to a meta description, ending on a sentence or word boundary."""
    text = " ".join(strip_tags(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if end >= limit * 0.6:
        return cut[: end + 1]
    return cut[: cut.rfind(" ")].rstrip(",;:—– ") + "…"


class BasePage(Page):
    """Fields and helpers shared by every public page type."""

    og_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Social sharing image. Defaults to the site-wide image.",
    )

    promote_panels = Page.promote_panels + [FieldPanel("og_image")]

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        # Search engines truncate longer values; catching it on save beats finding it in an audit.
        errors = {}
        if len(self.seo_title) > TITLE_LIMIT:
            errors["seo_title"] = f"Keep the title tag to {TITLE_LIMIT} characters ({len(self.seo_title)} now)."
        if len(self.search_description) > DESCRIPTION_LIMIT:
            errors["search_description"] = f"Keep the description to {DESCRIPTION_LIMIT} characters ({len(self.search_description)} now)."
        if errors:
            raise ValidationError(errors)

    def get_meta_title(self):
        return self.seo_title or f"{self.title} | Studio"

    def get_meta_description(self):
        return self.search_description or ""

    def get_breadcrumbs(self):
        """Ancestors between the home page and this page, as (title, url) pairs."""
        return [(ancestor.title, ancestor.url) for ancestor in self.get_ancestors().filter(depth__gt=2)]

    def get_faqs(self):
        faqs = getattr(self, "faqs", None)
        return [child.value for child in faqs] if faqs else []

    def get_structured_data(self, request=None):
        data = []
        if self.depth > 2:
            items = [("Home", settings.SITE_URL + "/")]
            items += [(title, absolute(url)) for title, url in self.get_breadcrumbs()]
            items.append((self.title, absolute(self.url)))
            data.append(
                {
                    "@context": "https://schema.org",
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": i, "name": name, "item": url}
                        for i, (name, url) in enumerate(items, start=1)
                    ],
                }
            )
        faqs = self.get_faqs()
        if faqs:
            data.append(
                {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": faq["question"],
                            "acceptedAnswer": {"@type": "Answer", "text": strip_tags(faq["answer"])},
                        }
                        for faq in faqs
                    ],
                }
            )
        return data


def absolute(url):
    return url if url.startswith("http") else settings.SITE_URL + url


class HeroMixin(models.Model):
    """The hero at the top of landing pages. A mixin, so pages without a hero carry no empty columns."""

    hero_title = models.CharField(max_length=200, help_text="The H1. The highlight is appended in the accent colour.")
    hero_highlight = models.CharField(max_length=120, blank=True)
    hero_lead = models.TextField(blank=True)

    hero_panels = [
        MultiFieldPanel(
            [FieldPanel("hero_title"), FieldPanel("hero_highlight"), FieldPanel("hero_lead")],
            heading="Hero",
        )
    ]

    class Meta:
        abstract = True

    @property
    def hero_heading(self):
        if not self.hero_highlight:
            return self.hero_title
        return format_html('{} <span class="hl">{}</span>', self.hero_title, self.hero_highlight)


class PageView(models.Model):
    """Daily view counts per path, written by core.middleware.PageViewMiddleware. Not content: read-only in the admin."""

    day = models.DateField(db_index=True)
    path = models.CharField(max_length=255)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["day", "path"], name="unique_page_view_per_day")]
        ordering = ["-day", "-count"]

    def __str__(self):
        return f"{self.path} on {self.day}"
