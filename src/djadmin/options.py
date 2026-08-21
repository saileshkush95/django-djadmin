"""ModelAdmin / inline base classes.

These are ordinary ``django.contrib.admin`` classes with a handful of extra
declarative hooks the modern UI understands.  Using them is optional — plain
``admin.ModelAdmin`` classes render perfectly well — but they let you say what
an icon or a dashboard card should be without touching a template.
"""

from django.contrib import admin


class DjadminMixin:
    """Extra, entirely optional, declarations understood by djadmin.

    Attributes:
        icon: sprite id used in the sidebar, dashboard and palette
            (see :data:`djadmin.icons.ICONS`).  Guessed from the model name
            when omitted.
        dashboard: include a stat card for this model on the dashboard.
        dashboard_order: lower sorts first among the stat cards.
        trend_field: date/datetime field used for the "vs last week" delta.
            Auto-detected from common names when omitted.
        help_text: one-line description rendered under the changelist title.
        palette_search: search this model's rows from the command palette.
            Turn it off for machine-written tables (logs, telemetry) so the
            palette's query budget goes to content people actually look for.
    """

    icon = None
    dashboard = True
    dashboard_order = 100
    trend_field = None
    help_text = ""
    #: Include this model's objects in the command palette's search.
    palette_search = True

    def get_djadmin_help_text(self, request):
        return self.help_text

    def changelist_view(self, request, extra_context=None):
        extra_context = dict(extra_context or {})
        extra_context.setdefault("djadmin_help_text", self.get_djadmin_help_text(request))
        return super().changelist_view(request, extra_context)


class ModelAdmin(DjadminMixin, admin.ModelAdmin):
    #: A denser default than Django's 100 — the modern table shows more per row.
    list_per_page = 25
    #: The sticky action bar already keeps Save in reach at any scroll position.
    save_on_top = False


class TabularInline(DjadminMixin, admin.TabularInline):
    extra = 0


class StackedInline(DjadminMixin, admin.StackedInline):
    extra = 0
