from django.contrib.auth import get_user_model
from wagtail.permission_policies import ModelPermissionPolicy


class ReadOnlyPermissionPolicy(ModelPermissionPolicy):
    """Users with Django's "view" permission can see rows. Nobody, not even a superuser, can add, change or delete them."""

    def user_has_permission(self, user, action):
        return action == "view" and super().user_has_permission(user, "view")

    def user_has_any_permission(self, user, actions):
        return "view" in actions and super().user_has_permission(user, "view")

    def users_with_any_permission(self, actions):
        if "view" not in actions:
            return get_user_model().objects.none()
        return super().users_with_any_permission(["view"])
