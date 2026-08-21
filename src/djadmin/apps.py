from django.apps import AppConfig
from django.contrib.admin import apps as admin_apps
from django.utils.translation import gettext_lazy as _


class DjadminConfig(AppConfig):
    """The djadmin app itself — ships the templates, styles and template tags.

    List it *before* the admin app so its ``templates/admin/*`` overrides win.
    """

    name = "djadmin"
    verbose_name = _("Djadmin")
    default_auto_field = "django.db.models.BigAutoField"
    default = True
    #: djadmin's own tables (MFA authenticators) stay out of the sidebar: they
    #: are managed from the Security page, not browsed like application data.
    #: They remain reachable at their admin URLs for staff who need them.
    hide_from_nav = True


class DjadminAdminConfig(admin_apps.AdminConfig):
    """Drop-in replacement for ``"django.contrib.admin"`` in INSTALLED_APPS.

    Same app, but ``admin.site`` becomes a :class:`~djadmin.sites.DjadminSite`,
    which adds the dashboard statistics and the command-palette endpoint.
    """

    default_site = "djadmin.sites.DjadminSite"
    # Never auto-selected for the plain "djadmin" entry — it is only used when
    # named explicitly, in place of "django.contrib.admin".
    default = False
