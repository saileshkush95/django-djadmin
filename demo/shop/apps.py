from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"
    verbose_name = "Shop"
    #: djadmin reads this for the sidebar section icon.
    icon = "cart"
