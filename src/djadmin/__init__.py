"""djadmin — a clean, modern UI for the Django admin.

djadmin does not reimplement the admin: it layers a new interface on top of
``django.contrib.admin``.  Everything you already know keeps working —
``list_display``, ``list_filter``, actions, inlines, permissions, autocomplete,
history — it just looks (and feels) like software from this decade.

Typical usage::

    # settings.py
    INSTALLED_APPS = [
        "djadmin",                          # must come before the admin app
        "djadmin.apps.DjadminAdminConfig",  # replaces "django.contrib.admin"
        ...
    ]

    # admin.py
    from django.contrib import admin
    import djadmin

    @admin.register(Product)
    class ProductAdmin(djadmin.ModelAdmin):
        icon = "box"
        list_display = ("name", "price", "status_badge")
"""

__version__ = "0.1.0"

__all__ = [
    "ModelAdmin",
    "StackedInline",
    "TabularInline",
    "DjadminMixin",
    "DjadminSite",
    "badge",
    "money",
    "progress",
    "avatar",
    "__version__",
]

# Lazy re-exports: importing djadmin must never drag in the admin (and through
# it, the model registry) before Django's app loading has finished.
_LAZY = {
    "ModelAdmin": ("djadmin.options", "ModelAdmin"),
    "StackedInline": ("djadmin.options", "StackedInline"),
    "TabularInline": ("djadmin.options", "TabularInline"),
    "DjadminMixin": ("djadmin.options", "DjadminMixin"),
    "DjadminSite": ("djadmin.sites", "DjadminSite"),
    "badge": ("djadmin.badges", "badge"),
    "money": ("djadmin.badges", "money"),
    "progress": ("djadmin.badges", "progress"),
    "avatar": ("djadmin.badges", "avatar"),
}


def __getattr__(name):
    try:
        module_path, attr = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    from importlib import import_module

    value = getattr(import_module(module_path), attr)
    globals()[name] = value
    return value


def __dir__():
    return sorted(__all__)
