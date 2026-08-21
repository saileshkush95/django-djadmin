# Contributing

## Running the demo

```bash
git clone https://github.com/saileshkush95/django-djadmin
cd django-djadmin
uv sync
uv run demo/manage.py migrate
uv run demo/manage.py seed_demo
uv run demo/manage.py runserver
```

Sign in at http://127.0.0.1:8000/admin/ with **admin / admin**.

The demo is a small shop: products, orders with inlines, customers, reviews,
tags with `filter_horizontal`, a custom list filter and bulk actions. It exists
to exercise every screen the package styles — if you add UI, add something to
the demo that shows it.

## Tests

```bash
uv run demo/manage.py test shop
```

Fifty tests cover every admin screen, the command palette, the dashboard and
the whole two-factor flow. They are written against behaviour, not markup
details, so they survive redesigns.

Against another Django version:

```bash
uv venv --python 3.12 /tmp/dj52
uv pip install --python /tmp/dj52/bin/python "Django~=5.2.0" segno -e .
cd demo && DJANGO_SETTINGS_MODULE=config.settings /tmp/dj52/bin/python manage.py test shop
```

CI runs Python 3.10/3.12 with Django 5.2 and Python 3.13 with Django 6.0 and
6.1.

## House style

**No runtime dependencies.** If a feature needs a library, it is optional, and
the feature degrades without it (see how `segno` is used for QR codes).

**No CDN and no build step.** Assets are plain files under
`src/djadmin/static/`. Charts are inline SVG generated in Python.

**Progressive enhancement.** Anything that needs JavaScript must have a working
server-rendered path behind it.

**Django decides.** Permissions, querysets and validation stay Django's.
Overriding a template to change where something appears is fine; reimplementing
a check is not.

## Releasing

See [RELEASING.md](https://github.com/saileshkush95/django-djadmin/blob/main/RELEASING.md).
The short version: bump `src/djadmin/__init__.py`, update the changelog, tag,
and let the publish workflow do the upload through PyPI Trusted Publishing.
