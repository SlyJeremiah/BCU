from django.contrib import admin

from .emails import send_status_update
from .models import Category, Donation, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "price", "stock", "is_active")
    list_filter = ("kind", "is_active", "category")
    search_fields = ("name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "price", "quantity")
    can_delete = False


@admin.action(description="Mark selected orders as paid (unlocks downloads)")
def mark_paid(modeladmin, request, queryset):
    for order in queryset.filter(status=Order.PENDING):
        order.status = Order.PAID
        order.save()
        send_status_update(order)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("short_id", "full_name", "email", "status", "payment_reference", "created")
    list_filter = ("status",)
    search_fields = ("full_name", "email", "payment_reference", "id")
    inlines = [OrderItemInline]
    actions = [mark_paid]

    def save_model(self, request, obj, form, change):
        old = Order.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if change and old != obj.status:
            send_status_update(obj)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("donor_name", "amount", "purpose", "status", "payment_reference", "created")
    list_filter = ("status",)
    actions = ["confirm"]

    @admin.action(description="Confirm selected donations")
    def confirm(self, request, queryset):
        queryset.update(status=Donation.CONFIRMED)
