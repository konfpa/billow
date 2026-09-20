from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin

from apps.accounts.forms import UserChangeForm, UserCreationForm
from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin):
    add_form = UserCreationForm
    form = UserChangeForm

    list_display = ("email", "name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    search_fields = ("email", "name")
    ordering = ("email",)
    readonly_fields = ("last_login", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("email", "name", "password")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Privileges", {"fields": ("groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    # A superuser sets the initial password here, because billow has no
    # password-reset flow for a new colleague to fall back on yet.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2"),
            },
        ),
    )
