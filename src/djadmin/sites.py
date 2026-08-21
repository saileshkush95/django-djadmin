"""The djadmin admin site.

:class:`DjadminSite` is a thin, fully compatible subclass of Django's
``AdminSite``.  It adds two things the modern UI needs and stock admin has no
concept of: dashboard statistics and a JSON endpoint that powers the command
palette (⌘K).  Everything else is inherited untouched.
"""

from datetime import timedelta
from functools import update_wrapper

from django.contrib import admin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import NoReverseMatch, path, reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _

from . import __version__
from . import mfa
from .charts import admin_activity, daily_counts, sparkline
from .conf import get_config
from .icons import icon_for_app, icon_for_model

#: Field names scanned, in order, to work out "new this week" trends.
TIMESTAMP_FIELDS = (
    "created",
    "created_at",
    "created_on",
    "date_created",
    "added",
    "added_at",
    "timestamp",
    "date_joined",
    "ordered_at",
    "published_at",
)


class DjadminSite(admin.AdminSite):
    site_title = _("Admin")
    site_header = _("Admin")
    index_title = _("Overview")

    #: Most stat cards to render on the dashboard.
    max_dashboard_stats = 8

    # -- URLs ------------------------------------------------------------

    def get_urls(self):
        extra = [
            path(
                "djadmin/search/",
                self.admin_view(self.palette_search),
                name="djadmin_search",
            ),
            path("security/", self.admin_view(self.security_view), name="djadmin_security"),
            path(
                "security/two-factor/",
                self.admin_view(self.mfa_setup_view),
                name="djadmin_mfa_setup",
            ),
            path(
                "security/two-factor/off/",
                self.admin_view(self.mfa_disable_view),
                name="djadmin_mfa_disable",
            ),
            path(
                "security/recovery-codes/",
                self.admin_view(self.mfa_recovery_view),
                name="djadmin_mfa_recovery",
            ),
            # Deliberately *not* wrapped in admin_view: at this point the user
            # has passed the password step but is not logged in yet.
            path("login/two-factor/", self.mfa_verify_view, name="djadmin_mfa_verify"),
        ]
        # Must come first: AdminSite.get_urls() ends in a catch-all route.
        return extra + super().get_urls()

    # -- Authentication --------------------------------------------------

    def admin_view(self, view, cacheable=False):
        """Standard admin protection, plus the "MFA is mandatory" policy."""
        inner = super().admin_view(view, cacheable)

        def wrapper(request, *args, **kwargs):
            target = mfa.enforcement_redirect(request, self.name)
            if target and request.path != target:
                return HttpResponseRedirect(target)
            return inner(request, *args, **kwargs)

        return update_wrapper(wrapper, view)

    def login(self, request, extra_context=None):
        """Django's admin login, with a second factor when one is enrolled."""
        from django.contrib.admin.forms import AdminAuthenticationForm

        from .views import DjadminLoginView

        # Resolve "next" the way RedirectURLMixin does, rather than calling it:
        # its signature changed in Django 6.1 and this has to work on 4.2 too.
        requested = request.POST.get(REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME, ""))
        is_safe = requested and url_has_allowed_host_and_scheme(
            url=requested,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        redirect_url = requested if is_safe else reverse(f"{self.name}:index", current_app=self.name)
        if request.method == "GET" and self.has_permission(request):
            return HttpResponseRedirect(redirect_url)

        context = {
            **self.each_context(request),
            "title": _("Log in"),
            "subtitle": None,
            "app_path": request.get_full_path(),
            "username": request.user.get_username(),
            REDIRECT_FIELD_NAME: redirect_url,
        }
        context.update(extra_context or {})
        request.current_app = self.name
        return DjadminLoginView.as_view(
            extra_context=context,
            authentication_form=self.login_form or AdminAuthenticationForm,
            template_name=self.login_template or "admin/login.html",
        )(request)

    def security_view(self, request):
        from . import views

        return views.security(request, self)

    def mfa_setup_view(self, request):
        from . import views

        return views.mfa_setup(request, self)

    def mfa_disable_view(self, request):
        from . import views

        return views.mfa_disable(request, self)

    def mfa_recovery_view(self, request):
        from . import views

        return views.mfa_recovery(request, self)

    def mfa_verify_view(self, request):
        from . import views

        return views.mfa_verify(request, self)

    # -- Context ---------------------------------------------------------

    def each_context(self, request):
        context = super().each_context(request)
        context["djadmin_version"] = __version__
        context["djadmin_site"] = True
        context["djadmin_mfa_enabled"] = mfa.is_enabled()
        context["djadmin_mfa_active"] = mfa.has_mfa(getattr(request, "user", None))
        return context

    # -- Dashboard -------------------------------------------------------

    def index(self, request, extra_context=None):
        config = get_config()
        extra_context = dict(extra_context or {})
        if config["DASHBOARD_STATS"]:
            extra_context.setdefault("djadmin_stats", self.get_stats(request))
        if config["DASHBOARD_ANALYTICS"]:
            extra_context.setdefault(
                "djadmin_activity", admin_activity(days=config["ANALYTICS_DAYS"])
            )
        return super().index(request, extra_context)

    def get_stats(self, request):
        """Return the stat cards shown at the top of the dashboard."""
        stats = []
        for app in self.get_app_list(request):
            for entry in app["models"]:
                model = entry.get("model")
                if model is None or not entry["perms"].get("view"):
                    continue
                model_admin = self._registry.get(model)
                if not getattr(model_admin, "dashboard", True):
                    continue
                stat = self._build_stat(request, model, entry, app)
                if stat is not None:
                    stats.append(stat)
        stats.sort(key=lambda s: (s["order"], -s["count"]))
        return stats[: self.max_dashboard_stats]

    def _build_stat(self, request, model, entry, app):
        model_admin = self._registry.get(model)
        try:
            queryset = model_admin.get_queryset(request)
        except Exception:  # a broken admin should never break the dashboard
            return None
        try:
            count = queryset.count()
        except Exception:
            return None
        trend_field = self._trend_field(model, model_admin)
        spark = None
        if trend_field and get_config()["DASHBOARD_ANALYTICS"]:
            spark = sparkline(
                [value for _day, value in daily_counts(queryset, trend_field, days=14)]
            )
        return {
            "label": entry["name"],
            "app_label": app["name"],
            "count": count,
            "url": entry.get("admin_url"),
            "add_url": entry.get("add_url"),
            "icon": icon_for_model(model, model_admin),
            "order": getattr(model_admin, "dashboard_order", 100),
            "trend": self._build_trend(queryset, model, model_admin),
            "sparkline": spark,
        }

    def _build_trend(self, queryset, model, model_admin, field_name=None):
        """Week-over-week change, when the model has an obvious date field."""
        field_name = field_name or self._trend_field(model, model_admin)
        if not field_name:
            return None
        now = timezone.now()
        try:
            this_week = queryset.filter(**{f"{field_name}__gte": now - timedelta(days=7)}).count()
            last_week = queryset.filter(
                **{
                    f"{field_name}__gte": now - timedelta(days=14),
                    f"{field_name}__lt": now - timedelta(days=7),
                }
            ).count()
        except Exception:
            return None
        if not this_week and not last_week:
            return None
        if last_week:
            percent = round((this_week - last_week) / last_week * 100)
        else:
            percent = 100
        return {"recent": this_week, "percent": percent, "up": percent >= 0}

    def _trend_field(self, model, model_admin):
        candidates = []
        if getattr(model_admin, "trend_field", None):
            candidates.append(model_admin.trend_field)
        if getattr(model_admin, "date_hierarchy", None):
            candidates.append(model_admin.date_hierarchy)
        candidates.extend(TIMESTAMP_FIELDS)
        for name in candidates:
            if "__" in name:
                continue
            try:
                field = model._meta.get_field(name)
            except FieldDoesNotExist:
                continue
            if isinstance(field, (models.DateField, models.DateTimeField)):
                return name
        return None

    # -- Command palette -------------------------------------------------

    def palette_search(self, request):
        """JSON search over the registered models and their objects."""
        config = get_config()
        query = (request.GET.get("q") or "").strip()
        app_list = self.get_app_list(request)

        models_out = []
        for app in app_list:
            for entry in app["models"]:
                if not entry.get("admin_url"):
                    continue
                haystack = f"{entry['name']} {app['name']}".lower()
                if query and query.lower() not in haystack:
                    continue
                models_out.append(
                    {
                        "label": str(entry["name"]),
                        "app": str(app["name"]),
                        "url": entry["admin_url"],
                        "add_url": entry.get("add_url") or "",
                        "icon": icon_for_model(entry.get("model"), self._registry.get(entry.get("model"))),
                    }
                )

        objects_out = []
        if query:
            searched = 0
            for model, model_admin in self._searchable(request, app_list, query):
                if searched >= config["SEARCH_MODEL_LIMIT"]:
                    break
                searched += 1
                objects_out.extend(
                    self._search_model(request, model, model_admin, query, config["SEARCH_OBJECT_LIMIT"])
                )

        return JsonResponse(
            {
                "query": query,
                "models": models_out[:20],
                "objects": objects_out[:25],
                "apps": [
                    {"label": str(app["name"]), "url": app["app_url"]}
                    for app in app_list
                    if not query or query.lower() in str(app["name"]).lower()
                ][:6],
            }
        )

    def _searchable(self, request, app_list, query):
        """Registered admins whose objects the palette should search.

        Models whose name matches the query come first, then the rest in a
        stable order. A ModelAdmin can opt out with ``palette_search = False``
        — telemetry tables and other machine-written data should not spend the
        query budget that real content needs.
        """
        allowed = {
            entry["model"]
            for app in app_list
            for entry in app["models"]
            if entry.get("model") is not None and entry["perms"].get("view")
        }
        matches, others = [], []
        for model, model_admin in self._registry.items():
            if model not in allowed or not model_admin.get_search_fields(request):
                continue
            if not getattr(model_admin, "palette_search", True):
                continue
            name = model._meta.verbose_name_plural.lower()
            (matches if query.lower() in name else others).append((model, model_admin))
        others.sort(key=lambda pair: (pair[0]._meta.app_label, pair[0]._meta.model_name))
        return matches + others

    def _search_model(self, request, model, model_admin, query, limit):
        try:
            queryset = model_admin.get_queryset(request)
            queryset, _dupes = model_admin.get_search_results(request, queryset, query)
            objects = list(queryset[:limit])
        except Exception:
            return []
        results = []
        for obj in objects:
            try:
                url = reverse(
                    f"{self.name}:{model._meta.app_label}_{model._meta.model_name}_change",
                    args=[obj.pk],
                )
            except NoReverseMatch:
                continue
            results.append(
                {
                    "label": str(obj),
                    "model": str(model._meta.verbose_name),
                    "url": url,
                    "icon": icon_for_model(model, model_admin),
                }
            )
        return results


#: A ready-made site instance, for projects that prefer an explicit site.
site = DjadminSite(name="djadmin")
