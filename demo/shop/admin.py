"""Admin for the demo shop.

Everything here is ordinary Django admin. The only djadmin-specific bits are
``djadmin.ModelAdmin`` (for ``icon`` / ``help_text`` / dashboard hints) and the
``badge`` / ``money`` / ``progress`` / ``avatar`` cell helpers.
"""

from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Count, F, Sum
from django.utils import timezone
from django.utils.html import format_html

import djadmin
from djadmin import avatar, badge, money, progress

from .models import Category, Customer, Order, OrderItem, Product, Review, Tag

PRODUCT_TONES = {"draft": "neutral", "active": "success", "archived": "warning"}
ORDER_TONES = {
    "pending": "warning",
    "paid": "info",
    "shipped": "accent",
    "delivered": "success",
    "cancelled": "neutral",
    "refunded": "danger",
}


class StockFilter(admin.SimpleListFilter):
    """Custom filter — renders exactly like the built-in ones."""

    title = "stock level"
    parameter_name = "stock_level"

    def lookups(self, request, model_admin):
        return [("out", "Out of stock"), ("low", "Needs restock"), ("ok", "Healthy")]

    def queryset(self, request, queryset):
        if self.value() == "out":
            return queryset.filter(stock=0)
        if self.value() == "low":
            return queryset.filter(stock__gt=0, stock__lte=F("reorder_level"))
        if self.value() == "ok":
            return queryset.filter(stock__gt=F("reorder_level"))
        return queryset


@admin.register(Category)
class CategoryAdmin(djadmin.ModelAdmin):
    icon = "tag"
    dashboard_order = 30
    help_text = "Top-level grouping used across the storefront navigation."
    list_display = ("name", "product_count", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    date_hierarchy = "created_at"
    # Annotated querysets carry a GROUP BY, which makes QuerySet.ordered False
    # and makes Django warn when paginating. Be explicit about the ordering.
    ordering = ("name",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_products=Count("products"))

    @admin.display(description="Products", ordering="_products")
    def product_count(self, obj):
        return badge(f"{obj._products} products", "accent" if obj._products else "neutral")


@admin.register(Tag)
class TagAdmin(djadmin.ModelAdmin):
    icon = "bookmark"
    dashboard = False
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class ReviewInline(djadmin.TabularInline):
    model = Review
    fields = ("customer", "rating", "title", "is_published", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("customer",)
    extra = 0
    classes = ("collapse",)


@admin.register(Product)
class ProductAdmin(djadmin.ModelAdmin):
    icon = "box"
    dashboard_order = 10
    help_text = "Everything you sell. Prices are per unit, excluding tax."
    list_display = ("name", "sku", "category", "status_badge", "price_display", "stock_display", "is_featured")
    list_display_links = ("name",)
    list_editable = ("is_featured",)
    list_filter = ("status", StockFilter, "is_featured", "category", "tags")
    search_fields = ("name", "sku", "description")
    autocomplete_fields = ("category",)
    filter_horizontal = ("tags",)
    prepopulated_fields = {"slug": ("name",)}
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at", "margin_display")
    inlines = (ReviewInline,)
    actions = ("mark_active", "mark_archived", "feature_products")
    list_per_page = 25
    save_on_top = False
    fieldsets = (
        (None, {"fields": ("name", "slug", "sku", "category", "tags")}),
        ("Pricing", {"fields": (("price", "cost"), "margin_display")}),
        ("Inventory", {"fields": (("stock", "reorder_level"), "status", "is_featured")}),
        ("Content", {"classes": ("collapse",), "fields": ("description",)}),
        ("Timestamps", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return badge(obj.get_status_display(), PRODUCT_TONES.get(obj.status, "neutral"), dot=True)

    @admin.display(description="Price", ordering="price")
    def price_display(self, obj):
        return money(obj.price)

    @admin.display(description="Stock", ordering="stock")
    def stock_display(self, obj):
        ceiling = max(obj.reorder_level * 3, 1)
        tone = "danger" if obj.stock == 0 else ("warning" if obj.needs_restock else "success")
        return progress(min(obj.stock, ceiling), ceiling, tone, label=f"{obj.stock} left")

    @admin.display(description="Margin")
    def margin_display(self, obj):
        if not obj.pk:
            return "—"
        return badge(f"{obj.margin:.0f}%", "success" if obj.margin > 40 else "warning")

    @admin.action(description="Mark selected products as active")
    def mark_active(self, request, queryset):
        updated = queryset.update(status=Product.Status.ACTIVE)
        self.message_user(request, f"{updated} product(s) are now active.", messages.SUCCESS)

    @admin.action(description="Archive selected products")
    def mark_archived(self, request, queryset):
        updated = queryset.update(status=Product.Status.ARCHIVED)
        self.message_user(request, f"{updated} product(s) archived.", messages.WARNING)

    @admin.action(description="Feature selected products")
    def feature_products(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} product(s) featured on the storefront.")


class OrderItemInline(djadmin.TabularInline):
    model = OrderItem
    fields = ("product", "quantity", "unit_price", "subtotal_display")
    readonly_fields = ("subtotal_display",)
    autocomplete_fields = ("product",)
    extra = 1

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        if obj.pk is None:
            return "—"
        return money(obj.subtotal)


@admin.register(Customer)
class CustomerAdmin(djadmin.ModelAdmin):
    icon = "users"
    dashboard_order = 20
    help_text = "People who have bought something, or signed up to."
    list_display = ("identity", "email", "location", "vip_badge", "order_count", "created_at")
    list_display_links = ("identity",)
    list_filter = ("is_vip", "country", "created_at")
    search_fields = ("first_name", "last_name", "email", "city")
    date_hierarchy = "created_at"
    ordering = ("last_name", "first_name")
    readonly_fields = ("created_at",)
    actions = ("promote_to_vip",)
    fieldsets = (
        ("Identity", {"fields": (("first_name", "last_name"), "email", "phone")}),
        ("Location", {"fields": (("city", "country"),)}),
        ("Account", {"fields": ("is_vip", "notes", "created_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_orders=Count("orders"))

    @admin.display(description="Customer", ordering="last_name")
    def identity(self, obj):
        return avatar(obj.full_name, obj.email)

    @admin.display(description="Location")
    def location(self, obj):
        parts = [part for part in (obj.city, obj.country) if part]
        return ", ".join(parts) or format_html('<span class="dj-muted">—</span>')

    @admin.display(description="Tier", ordering="is_vip", boolean=False)
    def vip_badge(self, obj):
        return badge("VIP", "accent") if obj.is_vip else badge("Standard", "neutral")

    @admin.display(description="Orders", ordering="_orders")
    def order_count(self, obj):
        return obj._orders

    @admin.action(description="Promote selected customers to VIP")
    def promote_to_vip(self, request, queryset):
        updated = queryset.update(is_vip=True)
        self.message_user(request, f"{updated} customer(s) promoted to VIP.", messages.SUCCESS)


@admin.register(Order)
class OrderAdmin(djadmin.ModelAdmin):
    icon = "cart"
    dashboard_order = 1
    help_text = "Orders flow pending → paid → shipped → delivered."
    list_display = ("reference", "customer", "status_badge", "items_display", "total_display", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("reference", "customer__first_name", "customer__last_name", "customer__email")
    autocomplete_fields = ("customer",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    inlines = (OrderItemInline,)
    readonly_fields = ("total_display", "created_at")
    actions = ("mark_shipped", "mark_delivered")
    list_select_related = ("customer",)
    fieldsets = (
        (None, {"fields": ("reference", "customer", "status")}),
        ("Fulfilment", {"fields": ("shipping_address", "shipped_at")}),
        ("Summary", {"fields": ("total_display", "created_at")}),
        ("Internal", {"classes": ("collapse",), "fields": ("notes",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("items__product").annotate(
            _total=Sum(F("items__unit_price") * F("items__quantity")),
            _items=Sum("items__quantity"),
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return badge(obj.get_status_display(), ORDER_TONES.get(obj.status, "neutral"), dot=True)

    @admin.display(description="Items", ordering="_items")
    def items_display(self, obj):
        return getattr(obj, "_items", None) or 0

    @admin.display(description="Total", ordering="_total")
    def total_display(self, obj):
        total = getattr(obj, "_total", None)
        if total is None:
            total = obj.total
        return money(total or Decimal("0.00"), tone="success")

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        updated = queryset.update(status=Order.Status.SHIPPED, shipped_at=timezone.now())
        self.message_user(request, f"{updated} order(s) marked as shipped.", messages.SUCCESS)

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        updated = queryset.update(status=Order.Status.DELIVERED)
        self.message_user(request, f"{updated} order(s) marked as delivered.", messages.SUCCESS)


@admin.register(Review)
class ReviewAdmin(djadmin.ModelAdmin):
    icon = "star"
    dashboard_order = 40
    help_text = "Customer reviews. Only published ones appear on the storefront."
    list_display = ("title", "product", "customer", "stars", "published_badge", "created_at")
    list_filter = ("is_published", "rating", "created_at")
    search_fields = ("title", "body", "product__name")
    autocomplete_fields = ("product", "customer")
    date_hierarchy = "created_at"
    actions = ("publish", "unpublish")

    @admin.display(description="Rating", ordering="rating")
    def stars(self, obj):
        return format_html('<span title="{} of 5">{}</span>', obj.rating, "★" * obj.rating + "☆" * (5 - obj.rating))

    @admin.display(description="Published", ordering="is_published")
    def published_badge(self, obj):
        return badge("Live", "success") if obj.is_published else badge("Hidden", "neutral")

    @admin.action(description="Publish selected reviews")
    def publish(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_published=True)} review(s) published.", messages.SUCCESS)

    @admin.action(description="Unpublish selected reviews")
    def unpublish(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_published=False)} review(s) hidden.", messages.WARNING)


admin.site.site_header = "Northwind"
admin.site.site_title = "Northwind admin"
admin.site.index_title = "Overview"
