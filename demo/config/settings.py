"""Settings for the djadmin demo shop.

The only djadmin-specific pieces are the two INSTALLED_APPS entries and the
optional DJADMIN dict at the bottom of this file.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-demo-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    # 1. djadmin ships the templates and styles, so it must come *before* the
    #    admin app for its admin/*.html overrides to win.
    "djadmin",
    # 2. This replaces "django.contrib.admin": same app, djadmin's AdminSite.
    "djadmin.apps.DjadminAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "shop",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Password-reset mails are printed to the console in this demo.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "northwind@example.com"

# -- djadmin ---------------------------------------------------------------
DJADMIN = {
    "BRAND": "Northwind",
    "BRAND_SHORT": "N",
    "ACCENT": "#5b5bd6",
    "THEME": "auto",
    "FOOTER": "Northwind Trading · djadmin demo",
    "APP_ICONS": {"shop": "cart", "auth": "shield"},
    "MFA": {
        "ENABLED": True,
        # Try "superusers" or True to see the enforced-enrolment flow.
        "REQUIRED": False,
        "ISSUER": "Northwind admin",
    },
    "MODEL_ICONS": {
        "shop.order": "cart",
        "shop.product": "box",
        "shop.customer": "users",
        "shop.category": "tag",
        "shop.review": "star",
        "shop.tag": "bookmark",
    },
}
