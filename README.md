# djadmin

A clean, modern UI for the Django admin — plus the things the admin never
shipped: a dashboard with real numbers, a command palette, and two-factor
authentication.

djadmin does **not** reimplement the admin. It layers a new interface on top of
`django.contrib.admin`, so everything you already know keeps working:
`list_display`, `list_filter`, `search_fields`, actions, inlines, permissions,
autocomplete, history, popups, `filter_horizontal`, date hierarchies.

## What you get

**The shell**
- Sidebar navigation grouped by app, with per-model icons, that collapses to an
  icon rail (`[`), or fully closes if you prefer (`SIDEBAR_TOGGLE`).
- Command palette (`⌘K` / `Ctrl+K`) that searches models *and* records.
- Light / dark / system theme, applied before first paint — no flash.
- Keyboard shortcuts (`/` search, `c` add, `f` filters, `⌘S` save, `?` help).
- Messages as toasts, sticky save bar, mobile layout, RTL styles.
- Delete confirmations in a dialog — fetched from Django's own confirmation
  view, so permissions, protected relations and the deletion tree are still
  computed server-side (and it degrades to the full page without JS).

**The dashboard**
- Stat cards per model with a 14-day sparkline and a week-over-week delta.
- Admin activity chart for the last 30 days, server-rendered as inline SVG
  (no chart library, no CDN, works with JavaScript disabled).
- Recent-actions timeline.

**The changelist**
- Sticky-header tables, filter panel that remembers its state, removable filter
  chips, a floating bulk-action bar that appears on selection, badges, progress
  cells and identity cells for `list_display`.

**Authentication**
- TOTP two-factor authentication (RFC 6238, implemented on the standard
  library — works with 1Password, Google Authenticator, Aegis…).
- Single-use recovery codes, stored as keyed hashes.
- Replay protection, attempt throttling with lockout, expiring challenges.
- A per-account **Security** page, and an optional org-wide MFA requirement.
- Styled password change and password reset flows.

## Install

```bash
pip install django-djadmin        # or: uv add django-djadmin
pip install "django-djadmin[mfa]" # adds QR codes on the MFA setup page
```

```python
# settings.py
INSTALLED_APPS = [
    "djadmin",                          # before the admin app: template overrides
    "djadmin.apps.DjadminAdminConfig",  # replaces "django.contrib.admin"
    ...
]
```

That is the whole installation. Run `manage.py migrate` (djadmin adds two small
tables for MFA) and open `/admin/`.

## Configure

Everything is optional:

```python
DJADMIN = {
    "BRAND": "Northwind",
    "ACCENT": "#5b5bd6",
    "THEME": "auto",              # auto | light | dark
    "SIDEBAR": "expanded",        # expanded | mini | hidden (initial state)
    "SIDEBAR_TOGGLE": "mini",     # what the button collapses to: mini | hidden
    "NAV_ACCORDION": False,       # one app group open at a time
    "DENSITY": "comfortable",     # comfortable | compact
    "APP_ICONS": {"shop": "cart"},
    "MODEL_ICONS": {"shop.order": "cart"},
    "HIDE_APPS": [],
    "DASHBOARD_STATS": True,
    "DASHBOARD_ANALYTICS": True,
    "ANALYTICS_DAYS": 30,
    "COMMAND_PALETTE": True,
    "MFA": {
        "ENABLED": True,
        "REQUIRED": False,        # False | True | "staff" | "superusers"
        "ISSUER": "Northwind admin",
        "CHALLENGE_TIMEOUT": 300,
        "MAX_ATTEMPTS": 5,
        "LOCKOUT_SECONDS": 300,
        "RECOVERY_CODES": 10,
    },
}
```

## Use it in `admin.py`

Plain `admin.ModelAdmin` renders fine. `djadmin.ModelAdmin` adds a few
declarations the UI understands:

```python
from django.contrib import admin
import djadmin
from djadmin import avatar, badge, money, progress

@admin.register(Product)
class ProductAdmin(djadmin.ModelAdmin):
    icon = "box"                  # sidebar / dashboard / palette icon
    dashboard_order = 10          # position among the stat cards
    help_text = "Everything you sell."
    list_display = ("name", "status_badge", "price_display", "stock_display")

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return badge(obj.get_status_display(), "success", dot=True)

    @admin.display(description="Price", ordering="price")
    def price_display(self, obj):
        return money(obj.price)
```

Cell helpers: `badge(text, tone, dot=False)`, `money(amount, currency)`,
`progress(value, total, tone, label)`, `avatar(name, subtitle, image_url)`.
Tones: `neutral`, `success`, `warning`, `danger`, `info`, `accent`.

`djadmin.TabularInline` and `djadmin.StackedInline` mirror the Django ones.

## The demo

A complete shop admin — products, orders with inlines, customers, reviews,
tags with `filter_horizontal`, custom filters, bulk actions and seeded data.

```bash
uv sync                                   # or: pip install -e ".[demo]"
uv run demo/manage.py migrate
uv run demo/manage.py seed_demo           # ~20 products, 45 customers, 240 orders
uv run demo/manage.py runserver
```

Then open http://127.0.0.1:8000/admin/ and sign in with **admin / admin**.

Run the test suite (50 tests: every admin screen, the palette, the dashboard
and the whole MFA flow):

```bash
uv run demo/manage.py test shop
```

## Roadmap

`docs/analytics-design.md` is a full design for a website-analytics module —
visitors, sessions, page views, sources, devices, countries, rollups, an
opt-in tracking app and a dashboard. It was built and then parked; the design
document stands on its own if it is picked up again.

The dashboard's own charts (per-model sparklines and the admin-activity graph)
are unrelated to that and remain part of djadmin — see `djadmin/charts.py`.

## Documentation

Full docs live in [`docs/`](docs/) — [installation](docs/installation.md),
[configuration](docs/configuration.md), [ModelAdmin](docs/modeladmin.md),
[authentication](docs/authentication.md) and
[customising](docs/customising.md). Build them locally with
`uv run --with mkdocs-material mkdocs serve`.

## Compatibility

| | |
|---|---|
| Python | 3.10 – 3.14 |
| Django | 5.2 LTS, 6.0, 6.1 |

Every combination is exercised in CI. Django 4.2 is not supported: it reached
end of life in April 2026 and lacks the collapsible-fieldset markup the forms
rely on.

No runtime dependencies beyond Django; `segno` is optional and only used to
draw the two-factor QR code.

## License

MIT
