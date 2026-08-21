"""Icon resolution for the sidebar, dashboard and command palette.

Icons are ids in the SVG sprite shipped at ``djadmin/templates/djadmin/icons.html``.
An icon is chosen in this order:

1. ``DJADMIN["MODEL_ICONS"]`` / ``DJADMIN["APP_ICONS"]``
2. ``ModelAdmin.icon`` / ``AppConfig.icon``
3. a keyword guess from the model or app name
4. a generic fallback
"""

from .conf import get_config

#: Every id available in the sprite.
ICONS = frozenset(
    """
    home box cart tag users user shield key file folder layers card truck star
    chat mail image chart settings database clock calendar globe bookmark check
    alert money search plus pencil trash sun moon monitor filter columns
    external chevron-down chevron-right menu x logout sparkle grid list
    """.split()
)

#: Substring -> icon.  Longest match wins, so order matters little; the lookup
#: below sorts by keyword length.
KEYWORDS = {
    "product": "box",
    "item": "box",
    "inventory": "box",
    "stock": "box",
    "order": "cart",
    "cart": "cart",
    "basket": "cart",
    "purchase": "cart",
    "categor": "tag",
    "tag": "tag",
    "label": "tag",
    "collection": "layers",
    "brand": "bookmark",
    "customer": "users",
    "client": "users",
    "user": "users",
    "person": "users",
    "profile": "user",
    "account": "user",
    "member": "users",
    "team": "users",
    "staff": "users",
    "group": "shield",
    "role": "shield",
    "permission": "key",
    "token": "key",
    "apikey": "key",
    "credential": "key",
    "session": "clock",
    "log": "file",
    "entry": "file",
    "audit": "file",
    "page": "file",
    "post": "file",
    "article": "file",
    "document": "file",
    "note": "file",
    "comment": "chat",
    "message": "chat",
    "thread": "chat",
    "review": "star",
    "rating": "star",
    "favorite": "star",
    "mail": "mail",
    "email": "mail",
    "newsletter": "mail",
    "image": "image",
    "photo": "image",
    "media": "image",
    "banner": "image",
    "file": "folder",
    "upload": "folder",
    "attachment": "folder",
    "payment": "card",
    "invoice": "card",
    "transaction": "card",
    "subscription": "card",
    "billing": "card",
    "price": "money",
    "discount": "money",
    "coupon": "money",
    "refund": "money",
    "shipment": "truck",
    "shipping": "truck",
    "delivery": "truck",
    "address": "globe",
    "country": "globe",
    "region": "globe",
    "site": "globe",
    "domain": "globe",
    "report": "chart",
    "stat": "chart",
    "metric": "chart",
    "analytic": "chart",
    "setting": "settings",
    "config": "settings",
    "preference": "settings",
    "option": "settings",
    "event": "calendar",
    "schedule": "calendar",
    "booking": "calendar",
    "task": "check",
    "todo": "check",
    "job": "check",
}

#: Apps we can name with certainty.
APP_KEYWORDS = {
    "auth": "shield",
    "authentication": "shield",
    "authorization": "shield",
    "account": "user",
    "user": "users",
    "shop": "cart",
    "store": "cart",
    "commerce": "cart",
    "catalog": "box",
    "blog": "file",
    "cms": "file",
    "content": "file",
    "site": "globe",
    "admin": "settings",
    "core": "layers",
    "common": "layers",
    "billing": "card",
    "payment": "card",
    "media": "image",
    "analytic": "chart",
    "report": "chart",
}

DEFAULT_MODEL_ICON = "box"
DEFAULT_APP_ICON = "layers"


def _guess(name, table, default):
    name = (name or "").lower()
    best, best_len = default, 0
    for keyword, icon in table.items():
        if keyword in name and len(keyword) > best_len:
            best, best_len = icon, len(keyword)
    return best


def _clean(icon, default):
    return icon if icon in ICONS else default


def icon_for_model(model, model_admin=None):
    """Return the sprite id to use for ``model``."""
    if model is None:
        return DEFAULT_MODEL_ICON
    opts = model._meta
    key = f"{opts.app_label}.{opts.model_name}"
    overrides = get_config()["MODEL_ICONS"]
    if key in overrides:
        return _clean(overrides[key], DEFAULT_MODEL_ICON)
    declared = getattr(model_admin, "icon", None)
    if declared:
        return _clean(declared, DEFAULT_MODEL_ICON)
    return _guess(f"{opts.model_name} {opts.verbose_name}", KEYWORDS, DEFAULT_MODEL_ICON)


def icon_for_app(app_label, app_config=None):
    """Return the sprite id to use for an app."""
    overrides = get_config()["APP_ICONS"]
    if app_label in overrides:
        return _clean(overrides[app_label], DEFAULT_APP_ICON)
    declared = getattr(app_config, "icon", None)
    if declared:
        return _clean(declared, DEFAULT_APP_ICON)
    return _guess(app_label, APP_KEYWORDS, DEFAULT_APP_ICON)
