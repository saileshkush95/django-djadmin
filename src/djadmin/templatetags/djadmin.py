"""Template tags used by the djadmin templates.

Everything here degrades gracefully: the templates work against a plain
``django.contrib.admin.AdminSite`` too, they just lose the dashboard stats and
the command palette's object search.
"""

from django import template
from django.http import QueryDict
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..conf import get_config
from ..icons import icon_for_app, icon_for_model

register = template.Library()


@register.simple_tag(takes_context=True)
def djadmin_conf(context):
    """The resolved ``DJADMIN`` settings, with branding filled in."""
    config = dict(get_config())
    brand = config.get("BRAND") or context.get("site_header") or "Admin"
    config["BRAND"] = brand
    config["BRAND_SHORT"] = config.get("BRAND_SHORT") or str(brand)[:1].upper()
    return config


@register.simple_tag
def dj_icon(name, css_class="dj-icon", size=None):
    """Render one icon from the sprite."""
    attrs = format_html(' width="{0}" height="{0}"', size) if size else mark_safe("")
    return format_html(
        '<svg class="{}" aria-hidden="true" focusable="false"{}><use href="#dji-{}"></use></svg>',
        css_class,
        attrs,
        name,
    )


@register.simple_tag(takes_context=True)
def djadmin_palette_url(context):
    """URL of the command-palette endpoint, or "" on a stock AdminSite."""
    request = context.get("request")
    namespace = getattr(getattr(request, "resolver_match", None), "namespace", None) or "admin"
    try:
        return reverse(f"{namespace}:djadmin_search")
    except NoReverseMatch:
        return ""


@register.simple_tag(takes_context=True)
def djadmin_nav(context):
    """Sidebar navigation built from the admin site's ``available_apps``.

    Returns a list of app dicts, each with an ``icon``, an ``active`` flag and
    its models (also with icons and active flags).
    """
    request = context.get("request")
    path = getattr(request, "path", "") or ""
    hidden = set(get_config()["HIDE_APPS"])
    apps = context.get("available_apps") or context.get("app_list") or []

    nav = []
    for app in apps:
        app_label = app.get("app_label", "")
        if app_label in hidden or _hidden_from_nav(app_label):
            continue
        models = []
        app_active = False
        for entry in app.get("models", []):
            url = entry.get("admin_url") or ""
            active = bool(url) and path.startswith(url)
            app_active = app_active or active
            model = entry.get("model")
            models.append(
                {
                    "label": entry.get("name"),
                    "url": url,
                    "add_url": entry.get("add_url") or "",
                    "active": active,
                    "icon": icon_for_model(model, _admin_for(context, model)),
                    "view_only": entry.get("view_only", False),
                }
            )
        app_url = app.get("app_url") or ""
        nav.append(
            {
                "label": app.get("name"),
                "app_label": app_label,
                "url": app_url,
                "icon": icon_for_app(app_label),
                "active": app_active or (bool(app_url) and path == app_url),
                "models": models,
            }
        )
    return nav


def _hidden_from_nav(app_label):
    """Apps can keep themselves out of the sidebar with ``hide_from_nav``.

    Useful for apps whose tables are an implementation detail with a dedicated
    page of their own — djadmin's own analytics tables, for instance.
    """
    from django.apps import apps as django_apps

    try:
        return bool(getattr(django_apps.get_app_config(app_label), "hide_from_nav", False))
    except LookupError:
        return False


def _admin_for(context, model):
    request = context.get("request")
    site = getattr(getattr(request, "resolver_match", None), "func", None)
    registry = getattr(getattr(site, "admin_site", None), "_registry", None)
    if registry is None:
        from django.contrib import admin

        registry = admin.site._registry
    return registry.get(model)


@register.filter
def dj_initials(value):
    """"Ada Lovelace" -> "AL"."""
    parts = str(value or "").split()
    return "".join(part[0] for part in parts[:2]).upper() or "?"


@register.filter
def dj_startswith(value, prefix):
    return str(value or "").startswith(str(prefix))


@register.simple_tag
def djadmin_active_filter_count(cl):
    """How many filters are currently applied on a changelist."""
    if cl is None:
        return 0
    ignored = {"p", "o", "q", "_popup", "_to_field", "_facets"}
    return len([key for key in getattr(cl, "params", {}) if key not in ignored])


@register.simple_tag(takes_context=True)
def dj_url(context, name, *args):
    """Reverse an admin URL in the *current* site's namespace.

    ``{% dj_url 'logout' as logout_url %}`` works on a custom AdminSite where a
    hardcoded ``{% url 'admin:logout' %}`` would not resolve.  Returns "" when
    the URL does not exist, so callers can simply test the result.
    """
    request = context.get("request")
    namespace = getattr(getattr(request, "resolver_match", None), "namespace", None) or "admin"
    for candidate in (namespace, "admin"):
        try:
            return reverse(f"{candidate}:{name}", args=args)
        except NoReverseMatch:
            continue
    return ""


@register.filter
def dj_number(value):
    """1234567 -> "1,234,567"."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value


@register.simple_tag
def djadmin_active_filters(cl):
    """The filters currently applied, as removable chips.

    Each entry is ``{"title", "display", "remove_url"}``.
    """
    if cl is None:
        return []
    chips = []
    params = getattr(cl, "params", {}) or {}
    for spec in getattr(cl, "filter_specs", []):
        expected = [str(p) for p in spec.expected_parameters()]
        if not any(p in params for p in expected):
            continue
        try:
            choices = list(spec.choices(cl))
        except Exception:
            choices = []
        # Index 0 is always the filter's "All" choice, which is selected while
        # the filter is idle — skip it and keep whatever else is selected.
        labels = [str(c["display"]) for i, c in enumerate(choices) if c.get("selected") and i]
        if not labels:
            labels = [_flatten(params[p]) for p in expected if p in params]
        chips.append(
            {
                "title": str(getattr(spec, "title", "")),
                "display": ", ".join(label for label in labels if label),
                "remove_url": cl.get_query_string(remove=expected),
            }
        )
    return chips


def _flatten(value):
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


@register.filter(is_safe=True)
def dj_object_list(value, max_items=None):
    """Render nested deletion trees, truncated when the admin asks for it.

    Django 6.1 introduced ``truncated_unordered_list`` (and the
    ``delete_confirmation_max_display`` setting behind it). On older versions
    this falls back to the built-in ``unordered_list``, which renders the whole
    tree — the same behaviour those versions always had.
    """
    try:
        max_items = int(max_items)
    except (TypeError, ValueError):
        max_items = None  # the setting does not exist on this Django version
    try:
        from django.contrib.admin.templatetags.admin_filters import truncated_unordered_list
    except ImportError:
        from django.template.defaultfilters import unordered_list

        return unordered_list(value)
    return truncated_unordered_list(value, max_items)


@register.filter
def dj_ago(value):
    """Like ``timesince``, but says "just now" instead of "0 minutes"."""
    from django.utils.timesince import timesince
    from django.utils.translation import gettext

    if not value:
        return ""
    try:
        rendered = timesince(value)
    except (TypeError, ValueError):
        return ""
    if rendered.startswith("0 "):
        return gettext("just now")
    return gettext("%(age)s ago") % {"age": rendered}


@register.simple_tag(takes_context=True)
def dj_query(context, **kwargs):
    """Current query string with some parameters replaced.

    ``{% dj_query metric="sessions" %}`` keeps the selected date range while
    switching one value. Passing None drops a parameter.
    """
    request = context.get("request")
    params = request.GET.copy() if request is not None else QueryDict(mutable=True)
    for key, value in kwargs.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else ""


@register.filter
def dj_duration(value):
    """90 -> "1m 30s"; 3700 -> "1h 1m"; 0 -> "0s"."""
    try:
        seconds = int(value or 0)
    except (TypeError, ValueError):
        return value
    if seconds <= 0:
        return "0s"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


@register.filter
def dj_percent(value):
    try:
        return f"{round(float(value))}%"
    except (TypeError, ValueError):
        return value


@register.simple_tag(takes_context=True)
def dj_change_form_actions(context):
    """Admin actions on a change form — a Django 6.1 feature.

    Renders Django's own template when it exists, and nothing at all on older
    versions, so one change_form.html serves every supported release.
    """
    if not context.get("action_form"):
        return ""
    from django.template import TemplateDoesNotExist
    from django.template.loader import render_to_string

    try:
        return mark_safe(render_to_string("admin/change_form_actions.html", context.flatten()))
    except TemplateDoesNotExist:
        return ""
