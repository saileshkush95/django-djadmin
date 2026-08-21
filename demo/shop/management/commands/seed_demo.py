"""Fill the demo database with believable data (and an admin user)."""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from shop.models import Category, Customer, Order, OrderItem, Product, Review, Tag

CATEGORIES = [
    ("Coffee", "Single-origin beans and house blends."),
    ("Tea", "Loose leaf, sourced directly from growers."),
    ("Brewing gear", "Grinders, kettles, scales and drippers."),
    ("Pantry", "Syrups, chocolate and everything else."),
    ("Merch", "Mugs, totes and the occasional t-shirt."),
]

TAGS = ["organic", "fair-trade", "decaf", "limited", "bestseller", "gift", "new"]

PRODUCTS = [
    ("Ethiopia Yirgacheffe", "Coffee", "24.00", "11.50"),
    ("Colombia Huila", "Coffee", "19.50", "9.00"),
    ("Sumatra Mandheling", "Coffee", "21.00", "10.25"),
    ("House Espresso Blend", "Coffee", "17.00", "7.40"),
    ("Decaf Brazil", "Coffee", "18.00", "8.90"),
    ("Kenya Nyeri AA", "Coffee", "27.50", "13.00"),
    ("Sencha Superior", "Tea", "14.00", "5.60"),
    ("Assam Second Flush", "Tea", "12.50", "4.90"),
    ("Jasmine Pearls", "Tea", "22.00", "9.10"),
    ("Earl Grey Reserve", "Tea", "13.50", "5.20"),
    ("Hand Grinder Pro", "Brewing gear", "89.00", "44.00"),
    ("Gooseneck Kettle 1L", "Brewing gear", "72.00", "36.50"),
    ("Pour-over Dripper", "Brewing gear", "28.00", "11.00"),
    ("Precision Scale", "Brewing gear", "54.00", "26.00"),
    ("Filter Papers (100)", "Brewing gear", "8.50", "2.80"),
    ("Vanilla Syrup", "Pantry", "11.00", "3.60"),
    ("Dark Chocolate 70%", "Pantry", "6.50", "2.10"),
    ("Oat Milk Barista", "Pantry", "3.20", "1.30"),
    ("Northwind Mug", "Merch", "16.00", "5.50"),
    ("Canvas Tote", "Merch", "21.00", "7.20"),
]

FIRST_NAMES = [
    "Ada", "Rui", "Mei", "Omar", "Iris", "Tomas", "Nadia", "Kofi", "Lena", "Yuki",
    "Priya", "Diego", "Sofia", "Anton", "Grace", "Hugo", "Amara", "Noor", "Ivan", "Clara",
]
LAST_NAMES = [
    "Okafor", "Lindqvist", "Tanaka", "Rossi", "Mbeki", "Novak", "Haddad", "Silva",
    "Kowalski", "Fernandez", "Andersen", "Nakamura", "Dubois", "Petrov", "Costa", "Mensah",
]
CITIES = [
    ("Lisbon", "Portugal"), ("Berlin", "Germany"), ("Osaka", "Japan"), ("Nairobi", "Kenya"),
    ("Toronto", "Canada"), ("Porto", "Portugal"), ("Austin", "United States"),
    ("Copenhagen", "Denmark"), ("Accra", "Ghana"), ("Melbourne", "Australia"),
]
REVIEW_TITLES = [
    "Exactly what I wanted", "Great value", "Will buy again", "Better than expected",
    "Solid, but pricey", "My new daily driver", "Arrived fast", "Not quite for me",
]
REVIEW_BODIES = [
    "Balanced and sweet, no bitterness at all.",
    "Shipping was quick and the packaging held up perfectly.",
    "Does the job. I'd like a slightly finer grind setting.",
    "Third order this year — consistent every time.",
    "Good, though I expected a bit more body.",
]

STATUS_WEIGHTS = [
    (Order.Status.PENDING, 12),
    (Order.Status.PAID, 22),
    (Order.Status.SHIPPED, 20),
    (Order.Status.DELIVERED, 38),
    (Order.Status.CANCELLED, 5),
    (Order.Status.REFUNDED, 3),
]


class Command(BaseCommand):
    help = "Seed the demo shop with categories, products, customers, orders and reviews."

    def add_arguments(self, parser):
        parser.add_argument("--orders", type=int, default=120, help="How many orders to create.")
        parser.add_argument("--customers", type=int, default=45, help="How many customers to create.")
        parser.add_argument("--flush", action="store_true", help="Delete existing shop data first.")
        parser.add_argument("--seed", type=int, default=42, help="Random seed, for reproducible data.")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        now = timezone.now()

        if options["flush"]:
            for model in (OrderItem, Order, Review, Product, Tag, Category, Customer):
                model.objects.all().delete()
            self.stdout.write(self.style.WARNING("Existing shop data removed."))

        user = self._ensure_superuser()

        categories = {}
        for name, description in CATEGORIES:
            categories[name], _ = Category.objects.get_or_create(
                name=name,
                defaults={
                    "slug": slugify(name),
                    "description": description,
                    "created_at": now - timedelta(days=rng.randint(120, 400)),
                },
            )

        tags = [Tag.objects.get_or_create(name=name, defaults={"slug": slugify(name)})[0] for name in TAGS]

        products = []
        for index, (name, category, price, cost) in enumerate(PRODUCTS):
            stock = rng.choice([0, 3, 8, 14, 26, 40, 75, 120])
            product, _ = Product.objects.get_or_create(
                sku=f"NW-{1000 + index}",
                defaults={
                    "name": name,
                    "slug": slugify(name),
                    "category": categories[category],
                    "status": rng.choices(
                        [Product.Status.ACTIVE, Product.Status.DRAFT, Product.Status.ARCHIVED],
                        weights=[78, 14, 8],
                    )[0],
                    "price": Decimal(price),
                    "cost": Decimal(cost),
                    "stock": stock,
                    "reorder_level": rng.choice([5, 10, 15, 20]),
                    "is_featured": rng.random() < 0.25,
                    "description": f"{name} — sourced by Northwind Trading. {rng.choice(REVIEW_BODIES)}",
                    "created_at": now - timedelta(days=rng.randint(1, 300), hours=rng.randint(0, 23)),
                },
            )
            if not product.tags.exists():
                product.tags.set(rng.sample(tags, rng.randint(1, 3)))
            products.append(product)

        customers = list(Customer.objects.all())
        wanted = options["customers"]
        while len(customers) < wanted:
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            city, country = rng.choice(CITIES)
            email = f"{first.lower()}.{last.lower()}{rng.randint(1, 999)}@example.com"
            if Customer.objects.filter(email=email).exists():
                continue
            customers.append(
                Customer.objects.create(
                    first_name=first,
                    last_name=last,
                    email=email,
                    phone=f"+{rng.randint(1, 99)} {rng.randint(100, 999)} {rng.randint(100000, 999999)}",
                    city=city,
                    country=country,
                    is_vip=rng.random() < 0.18,
                    created_at=now - timedelta(days=rng.randint(0, 260), hours=rng.randint(0, 23)),
                )
            )

        sellable = [p for p in products if p.status != Product.Status.ARCHIVED] or products
        statuses = [status for status, _ in STATUS_WEIGHTS]
        weights = [weight for _, weight in STATUS_WEIGHTS]
        start = Order.objects.count()

        for index in range(options["orders"]):
            # Skew recent: half the orders land in the last three weeks so the
            # dashboard's week-over-week trends have something to show.
            age_days = rng.choice([rng.randint(0, 20), rng.randint(0, 20), rng.randint(21, 180)])
            created = now - timedelta(days=age_days, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
            status = rng.choices(statuses, weights=weights)[0]
            order = Order.objects.create(
                reference=f"NW-{now.year}-{start + index + 1:04d}",
                customer=rng.choice(customers),
                status=status,
                shipping_address=f"{rng.randint(1, 240)} Harbour Road\n{rng.choice(CITIES)[0]}",
                created_at=created,
                shipped_at=created + timedelta(days=rng.randint(1, 4))
                if status in {Order.Status.SHIPPED, Order.Status.DELIVERED}
                else None,
            )
            for product in rng.sample(sellable, rng.randint(1, 4)):
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=rng.randint(1, 3),
                    unit_price=product.price,
                )

        if not Review.objects.exists():
            for _ in range(60):
                Review.objects.create(
                    product=rng.choice(products),
                    customer=rng.choice(customers),
                    rating=rng.choices([5, 4, 3, 2, 1], weights=[45, 30, 14, 7, 4])[0],
                    title=rng.choice(REVIEW_TITLES),
                    body=rng.choice(REVIEW_BODIES),
                    is_published=rng.random() < 0.7,
                    created_at=now - timedelta(days=rng.randint(0, 120), hours=rng.randint(0, 23)),
                )

        self._seed_admin_log(rng, now, user or get_user_model().objects.filter(is_superuser=True).first())

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded: {c} categories, {p} products, {u} customers, {o} orders, {r} reviews.".format(
                    c=Category.objects.count(),
                    p=Product.objects.count(),
                    u=Customer.objects.count(),
                    o=Order.objects.count(),
                    r=Review.objects.count(),
                )
            )
        )
        if user:
            self.stdout.write(self.style.SUCCESS("Log in at /admin/ with  admin / admin"))

    def _seed_admin_log(self, rng, now, user):
        """Give the dashboard's activity chart something to plot."""
        if user is None or LogEntry.objects.exists():
            return
        pools = []
        for model in (Product, Order, Customer, Review, Category):
            content_type = ContentType.objects.get_for_model(model)
            objects = list(model.objects.all()[:40])
            if objects:
                pools.append((content_type, objects))
        if not pools:
            return
        entries = []
        for _ in range(220):
            content_type, objects = rng.choice(pools)
            obj = rng.choice(objects)
            flag = rng.choices([ADDITION, CHANGE, DELETION], weights=[40, 52, 8])[0]
            entries.append(
                LogEntry(
                    user=user,
                    content_type=content_type,
                    object_id=str(obj.pk),
                    object_repr=str(obj)[:200],
                    action_flag=flag,
                    change_message="[]" if flag == DELETION else '[{"changed": {"fields": ["status"]}}]',
                    action_time=now - timedelta(days=rng.randint(0, 29), hours=rng.randint(0, 23)),
                )
            )
        LogEntry.objects.bulk_create(entries)

    def _ensure_superuser(self):
        User = get_user_model()
        if User.objects.filter(username="admin").exists():
            return None
        return User.objects.create_superuser("admin", "admin@example.com", "admin")
