from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from shop.views import storefront

urlpatterns = [
    path("", storefront, name="storefront"),
    # The admin login page links to "admin_password_reset" when it exists, so
    # wiring these four URLs is all it takes to enable password recovery.
    path(
        "admin/password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path(
        "admin/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("admin/", admin.site.urls),
]
