from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.db.models import Count, F, Sum
from django.utils import timezone


class BCUAdminSite(admin.AdminSite):
    site_header = "BCU Shop Administration"
    site_title = "BCU Shop Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        from .models import Donation, Order, OrderItem, Product

        paid = [Order.PAID, Order.SHIPPED, Order.COMPLETED]
        month_ago = timezone.now() - timedelta(days=30)
        revenue = OrderItem.objects.filter(order__status__in=paid).aggregate(t=Sum(F("price") * F("quantity")))["t"] or Decimal("0")
        revenue_30 = OrderItem.objects.filter(order__status__in=paid, order__created__gte=month_ago).aggregate(
            t=Sum(F("price") * F("quantity")))["t"] or Decimal("0")
        donations = Donation.objects.filter(status=Donation.CONFIRMED).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        top = (OrderItem.objects.filter(order__status__in=paid).values("product__name")
               .annotate(sold=Sum("quantity")).order_by("-sold")[:5])
        ctx = {
            "stats": [
                ("Orders awaiting payment", Order.objects.filter(status=Order.PENDING).count(), "pending"),
                ("Revenue (confirmed)", revenue, "money"),
                ("Revenue, last 30 days", revenue_30, "money"),
                ("Donations confirmed", donations, "money"),
                ("Donations pending", Donation.objects.filter(status=Donation.PENDING).count(), "pending"),
                ("Low stock (≤5)", Product.objects.filter(kind=Product.PHYSICAL, is_active=True, stock__lte=5).count(), "pending"),
            ],
            "recent_orders": Order.objects.select_related("user").order_by("-created")[:6],
            "top_products": top,
        }
        return super().index(request, {**ctx, **(extra_context or {})})
