from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet, ModelViewSetGroup

from pages.models import Enquiry, NewsletterSignup


class EnquiryViewSet(ModelViewSet):
    model = Enquiry
    icon = "mail"
    list_display = ["name", "email", "created_at", "handled"]
    list_filter = ["handled"]
    search_fields = ["name", "email", "message"]
    form_fields = ["handled"]  # staff only tick an enquiry off; they never rewrite it
    inspect_view_enabled = True
    copy_view_enabled = False
    menu_order = 100


class NewsletterSignupViewSet(ModelViewSet):
    model = NewsletterSignup
    icon = "user"
    list_display = ["email", "created_at"]
    search_fields = ["email"]
    form_fields = ["email"]
    copy_view_enabled = False
    menu_order = 200


class InboxGroup(ModelViewSetGroup):
    menu_label = "Inbox"
    menu_icon = "mail"
    menu_order = 250
    items = (EnquiryViewSet, NewsletterSignupViewSet)


@hooks.register("register_admin_viewset")
def register_inbox():
    return InboxGroup()
