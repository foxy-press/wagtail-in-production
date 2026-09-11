from django.contrib import messages
from django.dispatch import receiver
from django.utils import timezone
from wagtail import hooks
from wagtail.admin.userbar import BaseItem
from wagtail.admin.views.pages.edit import EditView
from wagtail.admin.viewsets.pages import PageListingViewSet, PageViewSet
from wagtail.signals import init_new_page
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from blog.models import BlogPage, Topic

REVIEW_AFTER_DAYS = 365


class TopicViewSet(SnippetViewSet):
    model = Topic
    icon = "tag"
    list_display = ["name", "slug"]
    search_fields = ["name"]


register_snippet(TopicViewSet)


class ArticleListingViewSet(PageListingViewSet):
    """A flat "Articles" listing across the whole tree, with filters, alongside the page explorer."""

    model = BlogPage
    icon = "doc-full"
    menu_label = "Articles"
    add_to_admin_menu = True
    menu_order = 150
    list_display = ["title", "topic", "date"]
    list_filter = ["topic", "date"]


class BlogPageEditView(EditView):
    def get(self, request, *args, **kwargs):
        reviewed = self.page.updated or self.page.date
        if reviewed and (timezone.localdate() - reviewed).days > REVIEW_AFTER_DAYS:
            messages.warning(request, f"Last reviewed {reviewed:%d %B %Y}. Check it's still accurate, then set “Last updated”.")
        return super().get(request, *args, **kwargs)


class BlogPageViewSet(PageViewSet):
    """Wagtail 8.0: every admin view for BlogPage can be swapped. Here, only the edit view changes."""

    model = BlogPage
    edit_view_class = BlogPageEditView


@hooks.register("register_admin_viewset")
def register_article_listing():
    return ArticleListingViewSet("articles")


@hooks.register("register_admin_viewset")
def register_blog_page_viewset():
    return BlogPageViewSet()


@receiver(init_new_page)
def prefill_article(sender, page, parent, **kwargs):
    """Pre-fill new articles. In 8.0 the signal moved from wagtail.admin.signals to wagtail.signals."""
    if isinstance(page, BlogPage):
        page.date = timezone.localdate()


class ReadTimeItem(BaseItem):
    template_name = "blog/userbar/read_time.html"

    def __init__(self, page):
        super().__init__()
        self.page = page


@hooks.register("construct_wagtail_userbar")
def add_read_time(request, items, page):
    # Wagtail 8.0 passes the page as a third argument; two-argument hook functions now fail.
    if isinstance(page, BlogPage):
        items.append(ReadTimeItem(page))
