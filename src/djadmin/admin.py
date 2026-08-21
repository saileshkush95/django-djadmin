"""Admin registration for djadmin's own models."""

from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _, ngettext

from .badges import badge
from .models import MFADevice
from .options import ModelAdmin


@admin.register(MFADevice)
class MFADeviceAdmin(ModelAdmin):
    """Who has MFA — visible to staff who can manage users.

    Secrets are never shown or editable here; an administrator can only revoke
    a device, which forces the owner to enrol again.
    """

    icon = "shield"
    dashboard = False
    palette_search = False
    help_text = _("Authenticator apps enrolled by staff. Revoke one to force re-enrolment.")
    list_display = ("user", "state", "codes_left", "confirmed_at", "last_used_at")
    list_filter = ("confirmed",)
    search_fields = ("user__username", "user__email")
    ordering = ("-confirmed_at",)
    readonly_fields = ("user", "confirmed", "created_at", "confirmed_at", "last_used_at", "codes_left")
    fields = readonly_fields
    actions = ("revoke_devices",)

    def has_add_permission(self, request):
        return False  # enrolment happens through the security page

    @admin.display(description=_("Status"), ordering="confirmed")
    def state(self, obj):
        return badge(_("Active"), "success", dot=True) if obj.confirmed else badge(_("Pending"), "warning", dot=True)

    @admin.display(description=_("Recovery codes"))
    def codes_left(self, obj):
        left = obj.unused_recovery_code_count
        return badge(str(left), "accent" if left > 2 else "danger")

    @admin.action(description=_("Revoke selected authenticators"))
    def revoke_devices(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            ngettext(
                "%(count)d authenticator revoked. That user must enrol again.",
                "%(count)d authenticators revoked. Those users must enrol again.",
                count,
            )
            % {"count": count},
            messages.WARNING,
        )
