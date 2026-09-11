from django.db import models
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.search import index

from core.blocks import ArticleBodyBlock, FAQBlock
from core.models import BasePage, HeroMixin


def faq_field():
    return StreamField([("faq", FAQBlock())], blank=True, use_json_field=True)


class ServiceRowBlock(blocks.StructBlock):
    name = blocks.CharBlock()
    description = blocks.TextBlock()
    page = blocks.PageChooserBlock(page_type="pages.ServicePage")

    class Meta:
        icon = "list-ul"


class HomePage(HeroMixin, BasePage):
    services = StreamField([("service", ServiceRowBlock())], blank=True, use_json_field=True)

    content_panels = Page.content_panels + HeroMixin.hero_panels + [FieldPanel("services")]

    # Home pages sit directly under the root, one per site (chapter 8), so no max_count.
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["pages.ServicesPage", "pages.LegalPage", "blog.BlogIndexPage"]


class ServicesPage(HeroMixin, BasePage):
    content_panels = Page.content_panels + HeroMixin.hero_panels

    parent_page_types = ["pages.HomePage"]
    subpage_types = ["pages.ServicePage"]
    max_count_per_parent = 1  # one per home page, so one per site

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["services"] = ServicePage.objects.live().child_of(self).order_by("path")
        return context


class ServicePage(HeroMixin, BasePage):
    body = StreamField(ArticleBodyBlock(), blank=True, use_json_field=True)
    faqs = faq_field()

    search_fields = Page.search_fields + [index.SearchField("hero_lead"), index.SearchField("body")]

    content_panels = Page.content_panels + HeroMixin.hero_panels + [FieldPanel("body"), FieldPanel("faqs")]

    parent_page_types = ["pages.ServicesPage"]
    subpage_types = []


class LegalPage(BasePage):
    body = RichTextField(features=["h2", "h3", "bold", "italic", "link", "ol", "ul"])

    content_panels = Page.content_panels + [FieldPanel("body")]

    parent_page_types = ["pages.HomePage"]
    subpage_types = []


class Enquiry(models.Model):
    """A message from the contact form. Data, not content: no revisions, no choosers."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "enquiries"

    def __str__(self):
        return f"{self.name} ({self.created_at:%d %b %Y})"


class NewsletterSignup(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
