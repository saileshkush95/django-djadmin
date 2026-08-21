# ModelAdmin

A plain `admin.ModelAdmin` renders perfectly well. `djadmin.ModelAdmin` adds a
few declarations the interface understands.

```python
from django.contrib import admin
import djadmin
from djadmin import avatar, badge, money, progress


@admin.register(Product)
class ProductAdmin(djadmin.ModelAdmin):
    icon = "box"
    dashboard_order = 10
    help_text = "Everything you sell. Prices are per unit, excluding tax."
    list_display = ("name", "status_badge", "price_display", "stock_display")
```

`djadmin.TabularInline` and `djadmin.StackedInline` mirror the Django ones
(with `extra = 0`, which is nearly always what you want).

## Declarations

### `icon`

Sprite id used in the sidebar, the dashboard and the palette. Guessed from the
model name when omitted. [Full list](customising.md#icons).

### `dashboard`

`True` by default. Set `False` to keep a model off the dashboard's stat cards —
right for join tables, logs and anything machine-written.

### `dashboard_order`

Lower sorts first among the stat cards. Default `100`, so the models you care
about can be pulled to the front without renumbering everything.

### `trend_field`

Date or datetime field behind the "vs last week" delta and the sparkline.
Auto-detected from common names (`created`, `created_at`, `date_joined`,
`published_at`, …) or from `date_hierarchy`; set it explicitly when the guess is
wrong.

### `help_text`

One line under the changelist title. Use it to say what the model is *for* —
new colleagues read it, and it costs nothing.

### `palette_search`

`True` by default. Set `False` to keep a model's records out of the command
palette. Worth doing for high-volume machine-written tables: the palette queries
a limited number of models per keystroke, and telemetry should not spend the
budget that real content needs.

## Cell helpers

Small helpers that return safe HTML for `list_display` columns.

```python
from djadmin import avatar, badge, money, progress
```

### `badge(text, tone="neutral", dot=False)`

A pill-shaped status label. Tones: `neutral`, `success`, `warning`, `danger`,
`info`, `accent`.

```python
@admin.display(description="Status", ordering="status")
def status_badge(self, obj):
    return badge(obj.get_status_display(), TONES[obj.status], dot=True)
```

### `money(amount, currency="$", tone=None)`

Right-aligned tabular figures, so columns of numbers line up.

### `progress(value, total=100, tone="accent", label=None)`

A compact bar. Good for stock levels, quotas and completion.

```python
@admin.display(description="Stock", ordering="stock")
def stock_display(self, obj):
    tone = "danger" if obj.stock == 0 else "warning" if obj.needs_restock else "success"
    return progress(obj.stock, obj.reorder_level * 3, tone, label=f"{obj.stock} left")
```

### `avatar(name, subtitle=None, image_url=None)`

An identity cell: initials (or a photo) with a name and a second line.

```python
@admin.display(description="Customer", ordering="last_name")
def identity(self, obj):
    return avatar(obj.full_name, obj.email)
```

## A note on annotated querysets

If you annotate in `get_queryset()` — a count, a sum — Django adds a `GROUP BY`,
which makes `QuerySet.ordered` false and produces a pagination warning. Declare
an explicit `ordering` on the ModelAdmin when you annotate:

```python
class CustomerAdmin(djadmin.ModelAdmin):
    ordering = ("last_name", "first_name")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_orders=Count("orders"))
```
