"""Settings for djadmin, read from the ``DJADMIN`` settings dict."""

from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

DEFAULTS = {
    # Branding
    "BRAND": None,  # defaults to the admin site header
    "BRAND_SHORT": None,  # collapsed-sidebar mark; defaults to first letter
    "LOGO_URL": None,  # static-ish URL rendered instead of the letter mark
    "FOOTER": None,
    # Look and feel
    "ACCENT": "#4f46e5",
    "ACCENT_FG": "#ffffff",
    "THEME": "auto",  # auto | light | dark — the default before a user picks
    "SIDEBAR": "expanded",  # expanded | mini | hidden — the default before a user picks
    # What the sidebar button toggles to: "mini" keeps an icon rail, "hidden"
    # closes it completely.
    "SIDEBAR_TOGGLE": "mini",
    "NAV_ACCORDION": False,  # True: opening an app group closes the others
    "DENSITY": "comfortable",  # comfortable | compact
    # Features
    "COMMAND_PALETTE": True,
    "DASHBOARD_STATS": True,
    "DASHBOARD_ANALYTICS": True,
    "ANALYTICS_DAYS": 30,
    "TOASTS": True,
    #: Show delete confirmations in a dialog instead of a separate page.
    "CONFIRM_MODAL": True,
    "STICKY_SUBMIT": True,
    # Navigation
    "APP_ICONS": {},  # {"shop": "cart"}
    "MODEL_ICONS": {},  # {"shop.product": "box"}
    "HIDE_APPS": [],  # app labels kept out of the sidebar
    # Command palette
    "SEARCH_MODEL_LIMIT": 6,  # models queried for objects per keystroke
    "SEARCH_OBJECT_LIMIT": 5,  # objects returned per model
    # Multi-factor authentication
    "MFA": {
        "ENABLED": True,
        # False | True | "staff" | "superusers"
        "REQUIRED": False,
        "ISSUER": None,  # authenticator app label; defaults to BRAND
        "CHALLENGE_TIMEOUT": 300,  # seconds to finish the second step
        "MAX_ATTEMPTS": 5,  # wrong codes before a lockout
        "LOCKOUT_SECONDS": 300,
        "RECOVERY_CODES": 10,
    },
}


class Config(dict):
    """Dict of resolved settings, refreshed whenever ``DJADMIN`` changes."""

    def reload(self):
        overrides = getattr(settings, "DJADMIN", None) or {}
        self.clear()
        self.update(DEFAULTS)
        self.update(overrides)
        # Nested dicts merge key by key, so setting one MFA option does not
        # silently drop the rest of the defaults.
        self["MFA"] = {**DEFAULTS["MFA"], **(overrides.get("MFA") or {})}
        return self


config = Config()


def get_config():
    if not config:
        config.reload()
    return config


@receiver(setting_changed)
def _reset_config(sender, setting, **kwargs):
    if setting == "DJADMIN":
        config.clear()
