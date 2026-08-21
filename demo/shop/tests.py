"""Smoke tests: every djadmin screen must render for a staff user.

Run with:  uv run demo/manage.py test shop
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from shop.models import Category, Customer, Order, OrderItem, Product, Review, Tag

MODELS = ["category", "tag", "product", "customer", "order", "review"]


class AdminSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_superuser("root", "root@example.com", "pw-for-tests")

        cls.category = Category.objects.create(name="Coffee", slug="coffee")
        cls.tag = Tag.objects.create(name="organic", slug="organic")
        cls.product = Product.objects.create(
            name="Ethiopia Yirgacheffe",
            slug="ethiopia-yirgacheffe",
            sku="NW-1000",
            category=cls.category,
            status=Product.Status.ACTIVE,
            price=Decimal("24.00"),
            cost=Decimal("11.50"),
            stock=8,
        )
        cls.product.tags.add(cls.tag)
        cls.customer = Customer.objects.create(
            first_name="Ada", last_name="Okafor", email="ada@example.com", city="Lisbon", country="Portugal"
        )
        cls.order = Order.objects.create(
            reference="NW-2026-0001", customer=cls.customer, status=Order.Status.PAID
        )
        OrderItem.objects.create(order=cls.order, product=cls.product, quantity=2, unit_price=Decimal("24.00"))
        cls.review = Review.objects.create(
            product=cls.product, customer=cls.customer, rating=5, title="Great", is_published=True
        )

    def setUp(self):
        self.client.force_login(self.user)

    # -- the shell ------------------------------------------------------

    def test_dashboard_renders_with_stats_and_shell(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('class="dj-shell"', html)
        self.assertIn("dj-sidebar", html)
        self.assertIn("djadmin/css/djadmin.css", html)
        self.assertIn("dj-stat", html)  # dashboard statistics rendered
        self.assertIn("dji-", html)  # icon sprite in use
        self.assertNotIn("admin/css/base.css", html)  # Django's stylesheet is gone

    def test_dashboard_stats_count_objects(self):
        response = self.client.get(reverse("admin:index"))
        labels = [stat["label"] for stat in response.context["djadmin_stats"]]
        counts = {stat["label"]: stat["count"] for stat in response.context["djadmin_stats"]}
        self.assertIn("Products", labels)
        self.assertEqual(counts["Products"], 1)
        self.assertEqual(counts["Orders"], 1)

    def test_delete_confirmations_get_a_dialog_host(self):
        # The dialog is progressive enhancement: the host is on the page, and
        # the delete link still points at the full confirmation page.
        response = self.client.get(reverse("admin:shop_review_change", args=[self.review.pk]))
        self.assertContains(response, 'id="dj-confirm-modal"')
        self.assertContains(response, reverse("admin:shop_review_delete", args=[self.review.pk]))

    def test_app_index(self):
        response = self.client.get(reverse("admin:app_list", args=["shop"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dj-app-card")

    def test_login_page_is_the_djadmin_one(self):
        self.client.logout()
        response = self.client.get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dj-auth-card")

    # -- changelists ----------------------------------------------------

    def test_every_changelist_renders(self):
        for model in MODELS:
            with self.subTest(model=model):
                response = self.client.get(reverse(f"admin:shop_{model}_changelist"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "dj-changelist")

    def test_changelist_search_filters_and_pagination(self):
        url = reverse("admin:shop_product_changelist")
        response = self.client.get(url, {"q": "Ethiopia"})
        self.assertContains(response, "Ethiopia Yirgacheffe")
        response = self.client.get(url, {"q": "nothing-matches-this"})
        self.assertContains(response, "No products found")
        response = self.client.get(url, {"status__exact": "active"})
        self.assertContains(response, "dj-chip")  # active-filter chip
        self.assertContains(response, "Ethiopia Yirgacheffe")
        self.assertContains(response, "Clear all")

    def test_custom_filter_applies(self):
        url = reverse("admin:shop_product_changelist")
        self.assertContains(self.client.get(url, {"stock_level": "low"}), "Ethiopia Yirgacheffe")
        response = self.client.get(url, {"stock_level": "out"})
        self.assertNotContains(response, "Ethiopia Yirgacheffe")

    def test_bulk_action_runs(self):
        response = self.client.post(
            reverse("admin:shop_product_changelist"),
            {"action": "mark_archived", "_selected_action": [self.product.pk], "index": "0"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.Status.ARCHIVED)
        self.assertContains(response, "dj-toast")  # messages render as toasts

    # -- forms ----------------------------------------------------------

    def test_every_add_form_renders(self):
        for model in MODELS:
            with self.subTest(model=model):
                response = self.client.get(reverse(f"admin:shop_{model}_add"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "dj-fieldset")
                self.assertContains(response, "dj-submit-row")

    def test_change_form_with_inlines_and_collapsed_fieldsets(self):
        response = self.client.get(reverse("admin:shop_order_change", args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("dj-inline", html)
        self.assertIn("js-inline-admin-formset", html)  # Django's inlines.js hook survives
        self.assertIn("inline-related", html)
        self.assertIn("dj-fieldset-details", html)  # collapsible fieldset

    def test_change_form_saves(self):
        url = reverse("admin:shop_category_change", args=[self.category.pk])
        response = self.client.post(
            url, {"name": "Coffee beans", "slug": "coffee", "description": "", "is_active": "on",
                  "created_at_0": "2026-01-01", "created_at_1": "10:00:00"}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Coffee beans")

    def test_history_page(self):
        response = self.client.get(reverse("admin:shop_product_history", args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "change-history")

    def test_delete_confirmation(self):
        response = self.client.get(reverse("admin:shop_review_delete", args=[self.review.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dj-confirm-card")
        self.assertContains(response, "dj-summary")

    def test_delete_of_protected_object_explains_itself(self):
        # OrderItem protects Product, so this must render the "protected" branch.
        response = self.client.get(reverse("admin:shop_product_delete", args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dj-alert--warning")
        self.assertNotContains(response, "dj-confirm-card")

    def test_autocomplete_endpoint_still_works(self):
        response = self.client.get(
            reverse("admin:autocomplete"),
            {"app_label": "shop", "model_name": "order", "field_name": "customer", "term": "Ada"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Ada Okafor", response.json()["results"][0]["text"])

    def test_popup_renders_without_chrome(self):
        response = self.client.get(reverse("admin:shop_category_add"), {"_popup": "1"})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("dj-popup-shell", html)
        self.assertNotIn('class="dj-sidebar"', html)


class CommandPaletteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_superuser("root", "root@example.com", "pw-for-tests")
        cls.staff = User.objects.create_user("clerk", "clerk@example.com", "pw-for-tests", is_staff=True)
        category = Category.objects.create(name="Coffee", slug="coffee")
        Product.objects.create(
            name="Kenya Nyeri AA", slug="kenya-nyeri-aa", sku="NW-1006",
            category=category, price=Decimal("27.50"), stock=4,
        )

    def test_palette_searches_models_and_objects(self):
        self.client.force_login(self.user)
        data = self.client.get(reverse("admin:djadmin_search"), {"q": "kenya"}).json()
        self.assertEqual(data["query"], "kenya")
        self.assertTrue(any(obj["label"] == "Kenya Nyeri AA" for obj in data["objects"]))

    def test_palette_lists_models_when_query_is_empty(self):
        self.client.force_login(self.user)
        data = self.client.get(reverse("admin:djadmin_search")).json()
        self.assertTrue(any(entry["label"] == "Products" for entry in data["models"]))
        self.assertEqual(data["objects"], [])

    def test_palette_respects_permissions(self):
        self.client.force_login(self.staff)  # staff, but no model permissions
        data = self.client.get(reverse("admin:djadmin_search"), {"q": "kenya"}).json()
        self.assertEqual(data["models"], [])
        self.assertEqual(data["objects"], [])

    def test_palette_requires_login(self):
        response = self.client.get(reverse("admin:djadmin_search"))
        self.assertEqual(response.status_code, 302)


class TrendTests(TestCase):
    def test_dashboard_trend_uses_a_date_field(self):
        User = get_user_model()
        user = User.objects.create_superuser("root", "root@example.com", "pw-for-tests")
        category = Category.objects.create(name="Tea", slug="tea")
        now = timezone.now()
        for index in range(3):  # this week
            Product.objects.create(
                name=f"Recent {index}", slug=f"recent-{index}", sku=f"R-{index}",
                category=category, price=Decimal("10"), created_at=now,
            )
        Product.objects.create(  # the week before
            name="Older", slug="older", sku="O-1", category=category,
            price=Decimal("10"), created_at=now - timezone.timedelta(days=10),
        )
        self.client.force_login(user)
        stats = {s["label"]: s for s in self.client.get(reverse("admin:index")).context["djadmin_stats"]}
        trend = stats["Products"]["trend"]
        self.assertEqual(trend["recent"], 3)
        self.assertEqual(trend["percent"], 200)  # 3 vs 1
        self.assertTrue(trend["up"])
