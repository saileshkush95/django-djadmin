# djadmin

A clean, modern UI for the Django admin — plus the things the admin never
shipped: a dashboard with real numbers, a command palette, and two-factor
authentication.

djadmin does **not** reimplement the admin. It layers a new interface on top of
`django.contrib.admin`, so everything you already know keeps working:
`list_display`, `list_filter`, `search_fields`, actions, inlines, permissions,
autocomplete, history, popups, `filter_horizontal`, date hierarchies.

```bash
pip install django-djadmin
```

```python
INSTALLED_APPS = [
    "djadmin",                          # before the admin app
    "djadmin.apps.DjadminAdminConfig",  # replaces "django.contrib.admin"
    ...
]
```

That is the whole installation. Run `manage.py migrate` and open `/admin/`.

## Where to go next

| Page | What's in it |
|---|---|
| [Installation](installation.md) | Requirements, the two INSTALLED_APPS lines, what `migrate` adds |
| [Configuration](configuration.md) | Every `DJADMIN` setting, with defaults |
| [ModelAdmin](modeladmin.md) | `icon`, dashboard cards, cell helpers, palette control |
| [Authentication](authentication.md) | Two-factor auth, recovery codes, enforcement, password reset |
| [Customising](customising.md) | Design tokens, template overrides, icons, keyboard shortcuts |
| [Contributing](contributing.md) | Running the demo, the test suite, releasing |

## Design principles

These explain most of the decisions you will meet in the code.

**No runtime dependency but Django.** Charts are inline SVG generated in Python.
TOTP is forty lines of `hmac`. The only optional dependency is `segno`, and only
to draw a QR code.

**No CDN, no build step.** One stylesheet and two small scripts, served by your
own `staticfiles`. Nothing phones home, and a strict CSP is achievable.

**Progressive enhancement.** Delete confirmations, filters, the theme and the
dashboard all work with JavaScript disabled — the enhancements are additive.

**Django stays in charge.** Permissions, querysets, form validation and the
deletion tree are Django's. djadmin changes where things are shown, not who is
allowed to see them.
