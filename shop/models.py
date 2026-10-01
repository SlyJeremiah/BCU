import uuid
from decimal import Decimal

from django.conf import settings
from django.core.files.storage import storages
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def digital_path(instance, filename):
    return f"digital/{uuid.uuid4().hex}/{filename}"


def pop_path(instance, filename):
    return f"pop/{uuid.uuid4().hex}/{filename}"


def private_storage():
    return storages["private"]


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


LOW_STOCK_BELOW = 10


class Product(models.Model):
    PHYSICAL, DIGITAL = "physical", "digital"
    KINDS = [(PHYSICAL, "Physical merchandise"), (DIGITAL, "Digital product")]

    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=10, choices=KINDS, default=PHYSICAL)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0, help_text="Physical items only")
    image = models.ImageField(upload_to="products/", blank=True)
    digital_file = models.FileField(
        upload_to=digital_path, storage=private_storage, blank=True,
        help_text="Digital products only. Stored privately on Backblaze B2.",
    )
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "product"
            slug, n = base, 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_digital(self):
        return self.kind == self.DIGITAL

    @property
    def is_low_stock(self):
        return not self.is_digital and self.stock < LOW_STOCK_BELOW

    @property
    def in_stock(self):
        return self.is_digital or self.stock > 0

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])

    def __str__(self):
        return self.name


class Order(models.Model):
    PENDING, PAID, SHIPPED, COMPLETED, CANCELLED = "pending", "paid", "shipped", "completed", "cancelled"
    STATUSES = [
        (PENDING, "Awaiting payment confirmation"), (PAID, "Paid"), (SHIPPED, "Shipped / ready for collection"),
        (COMPLETED, "Completed"), (CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders")
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.TextField(blank=True, help_text="Required for physical items")
    city = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, help_text="Transaction reference")
    proof_of_payment = models.FileField(upload_to=pop_path, storage=private_storage, blank=True,
                                        help_text="Customer's proof of payment (private)")
    status = models.CharField(max_length=12, choices=STATUSES, default=PENDING)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    @property
    def total(self):
        return sum((i.line_total for i in self.items.all()), Decimal("0"))

    @property
    def has_physical(self):
        return any(not i.product.is_digital for i in self.items.all())

    @property
    def downloads_unlocked(self):
        return self.status in (self.PAID, self.SHIPPED, self.COMPLETED)

    @property
    def short_id(self):
        return str(self.id)[:8].upper()

    def __str__(self):
        return f"Order {self.short_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def line_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product}"


class Donation(models.Model):
    PENDING, CONFIRMED = "pending", "confirmed"
    STATUSES = [(PENDING, "Awaiting confirmation"), (CONFIRMED, "Confirmed")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    donor_name = models.CharField(max_length=150)
    email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.CharField(max_length=200, blank=True, help_text="e.g. BCU camp, building fund")
    payment_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default=PENDING)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.donor_name} – {self.amount}"
