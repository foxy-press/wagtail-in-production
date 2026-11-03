import math

from django.db import models
from django.utils.functional import cached_property
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.api import APIField
from wagtail.images.api.fields import ImageRenditionField
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from core.blocks import ArticleBodyBlock, FAQBlock, body_faqs, body_headings, body_word_count
from core.models import BasePage, HeroMixin, fit_description

WORDS_PER_MINUTE = 230


class Topic(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)

    panels = [FieldPanel("name"), FieldPanel("slug")]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BlogIndexPage(HeroMixin, BasePage):
    content_panels = Page.content_panels + HeroMixin.hero_panels

    parent_page_types = ["pages.HomePage"]
    subpage_types = ["blog.BlogPage"]
    max_count_per_parent = 1

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # One query for the posts and their topics, without loading every post's StreamField JSON (chapter 10).
        posts = BlogPage.objects.live().child_of(self).select_related("topic").defer_streamfields().order_by("-date")
        topic = request.GET.get("topic")
        if topic:
            posts = posts.filter(topic__slug=topic)
        context["posts"] = posts
        context["topics"] = Topic.objects.filter(posts__isnull=False).distinct()
        return context


class BlogPage(BasePage):
    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.SET_NULL, related_name="posts")
    intro = models.TextField(help_text="Lead paragraph under the H1. Also the default meta description.")
    date = models.DateField("Published")
    updated = models.DateField("Last updated", null=True, blank=True)
    author_name = models.CharField(max_length=80, default="Studio team")
    body = StreamField(ArticleBodyBlock(), use_json_field=True)
    faqs = StreamField([("faq", FAQBlock())], blank=True, use_json_field=True)

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
        index.AutocompleteField("intro"),
        index.RelatedFields("topic", [index.SearchField("name")]),
        index.FilterField("date"),
        index.FilterField("topic"),
    ]

    # Read by the v2 and v3 APIs. writable=True also lets authenticated v3 clients set them.
    api_fields = [
        APIField("intro", writable=True),
        APIField("date", writable=True),
        APIField("updated", writable=True),
        APIField("author_name", writable=True),
        APIField("body", writable=True),
        APIField("topic_name"),
        APIField("read_minutes"),
        APIField("og_image", serializer=ImageRenditionField("fill-1200x630|format-jpeg")),
    ]

    @property
    def topic_name(self):
        return self.topic.name if self.topic_id else ""

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("topic"), FieldPanel("intro"), FieldPanel("date"), FieldPanel("updated")],
            heading="Article",
        ),
        FieldPanel("author_name"),
        FieldPanel("body"),
        FieldPanel("faqs"),
    ]

    parent_page_types = ["blog.BlogIndexPage"]
    subpage_types = []

    @cached_property
    def read_minutes(self):
        return max(1, math.ceil(body_word_count(self.body) / WORDS_PER_MINUTE))

    @cached_property
    def toc(self):
        items = body_headings(self.body)
        if self.get_faqs():
            items.append(("faq", "Questions"))
        return items

    def get_meta_description(self):
        return self.search_description or fit_description(self.intro)

    def get_structured_data(self, request=None):
        article = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.title,
            "description": self.get_meta_description(),
            "datePublished": self.date.isoformat(),
            "dateModified": (self.updated or self.date).isoformat(),
            "author": {"@type": "Person", "name": self.author_name},
            "mainEntityOfPage": self.full_url,
        }
        if self.og_image:
            article["image"] = self.og_image.get_rendition("fill-1200x630|format-jpeg").full_url
        return [article] + super().get_structured_data(request)

    def get_sitemap_urls(self, request=None):
        # Tell search engines when the content really changed, not when someone last clicked Publish.
        # Start from Wagtail's entry, so it keeps the links to this page's translations.
        urls = super().get_sitemap_urls(request)
        urls[0]["lastmod"] = self.updated or self.date
        return urls

    def get_faqs(self):
        return super().get_faqs() or body_faqs(self.body)

    def get_related(self, count=3):
        siblings = BlogPage.objects.live().sibling_of(self, inclusive=False).select_related("topic")
        related = list(siblings.filter(topic=self.topic).order_by("-date")[:count]) if self.topic_id else []
        if len(related) < count:
            exclude = [page.pk for page in related]
            related += list(siblings.exclude(pk__in=exclude).order_by("-date")[: count - len(related)])
        return related

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["related"] = self.get_related()
        return context
