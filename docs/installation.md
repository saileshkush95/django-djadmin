# Installation

## Requirements

| | |
|---|---|
| Python | 3.10 – 3.14 |
| Django | 5.2 LTS, 6.0, 6.1 |
| Database | anything Django supports |

Every combination above is exercised in CI. Django 4.2 is not supported: it
reached end of life in April 2026 and lacks the collapsible-fieldset markup the
forms rely on.

## Install

```bash
pip install django-djadmin          # or: uv add django-djadmin
pip install "django-djadmin[mfa]"   # adds QR codes on the 2FA setup page
```

## Settings

```python
INSTALLED_APPS = [
    "djadmin",                          # 1
    "djadmin.apps.DjadminAdminConfig",  # 2
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    ...
]
```

1. **`"djadmin"` must come before the admin app.** Django searches app template
   directories in order, and djadmin works by overriding `admin/*.html`. Listed
   after, the stock templates win and you get the default admin.
2. **`"djadmin.apps.DjadminAdminConfig"` replaces `"django.contrib.admin"`** —
   it is the same app, configured to use `DjadminSite` instead of `AdminSite`.
   Do not list both.

Then:

```bash
python manage.py migrate
```

That creates two small tables, `djadmin_mfadevice` and `djadmin_recoverycode`,
which hold enrolled authenticators. Nothing else in djadmin touches the
database.

## Serving the assets

djadmin ships one stylesheet and two scripts as ordinary app static files, so
`collectstatic` picks them up with no extra configuration:

```bash
python manage.py collectstatic
```

## Keeping the default admin as well

If you want djadmin on one admin site and the stock admin on another, register
your own site instead of swapping the default:

```python
# admin.py
from djadmin.sites import DjadminSite

modern_site = DjadminSite(name="modern")
```

```python
# urls.py
path("modern-admin/", modern_site.urls),
```

Note that djadmin's template overrides are global — the stock admin will pick up
the new look too, because both read `admin/base.html`. If the two must look
different, keep djadmin out of `INSTALLED_APPS` and add its template directory
to only one engine.
