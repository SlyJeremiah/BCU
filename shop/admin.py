import csv

from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponse
from django.utils.html import format_html

from .emails import send_status_update
from .models import LOW_STOCK_BELOW, Category, Contact, Donation, Executive, Order, OrderItem, Product


def badge(status, label):
    return format_html('<span class="bcu-badge {}">{}</span>', status, label)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Products")
    def product_count(self, obj):
        return obj.products.count()


class LowStockFilter(admin.SimpleListFilter):
    title = "stock level"
    parameter_name = "stock_level"

    def lookups(self, request, model_admin):
        return [("low", f"Low stock (under {LOW_STOCK_BELOW})"), ("out", "Out of stock")]

    def queryset(self, request, qs):
        qs = qs.filter(kind=Product.PHYSICAL) if self.value() else qs
        if self.value() == "low":
            return qs.filter(stock__lt=LOW_STOCK_BELOW)
        if self.value() == "out":
            return qs.filter(stock=0)
        return qs


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "category", "kind", "price", "stock_display", "is_active")
    list_display_links = ("thumb", "name")
    list_editable = ("price", "is_active")
    list_filter = ("kind", "is_active", LowStockFilter, "category")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("preview", "created")
    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "kind", "description", "is_active")}),
        ("Pricing & stock", {"fields": ("price", "stock")}),
        ("Media", {"fields": ("image", "preview", "digital_file"),
                   "description": "Digital file is for digital products only and is delivered via expiring links."}),
    )
    actions = ["activate", "deactivate"]

    @admin.display(description="")
    def thumb(self, obj):
        return format_html('<img class="bcu-thumb" src="{}">', obj.image.url) if obj.image else "—"

    @admin.display(description="Preview")
    def preview(self, obj):
        return format_html('<img style="max-width:240px;border-radius:8px" src="{}">', obj.image.url) if obj.image else "—"

    @admin.display(description="Stock", ordering="stock")
    def stock_display(self, obj):
        if obj.is_digital:
            return "Digital"
        if obj.stock == 0:
            return format_html('<b style="color:#d40000">0 · OUT OF STOCK</b>')
        if obj.is_low_stock:
            return format_html('<b style="color:#d40000">{} · LOW STOCK</b>', obj.stock)
        return obj.stock

    @admin.action(description="Show selected products in the shop")
    def activate(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Hide selected products from the shop")
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "price", "quantity")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


def _set_status(modeladmin, request, queryset, status, only_from=None):
    n = 0
    for order in queryset:
        if only_from and order.status not in only_from:
            continue
        order.status = status
        order.save()
        send_status_update(order)
        n += 1
    modeladmin.message_user(request, f"{n} order(s) updated to “{dict(Order.STATUSES)[status]}”.")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("short_id", "full_name", "email", "phone", "total_display", "status_badge", "payment_reference", "pop_link", "created")
    list_filter = ("status", "created")
    search_fields = ("full_name", "email", "phone", "payment_reference", "id")
    date_hierarchy = "created"
    inlines = [OrderItemInline]
    readonly_fields = ("id", "user", "created", "updated", "pop_link", "total_display")
    fieldsets = (
        ("Order", {"fields": ("id", "user", "status", "total_display", "created", "updated")}),
        ("Customer", {"fields": ("full_name", "email", "phone", "address", "city", "notes")}),
        ("Payment", {"fields": ("payment_reference", "pop_link")}),
    )
    actions = ["mark_paid", "mark_shipped", "mark_completed", "cancel_and_restock", "export_csv"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("items")

    @admin.display(description="Total")
    def total_display(self, obj):
        return f"{obj.total:.2f}"

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return badge(obj.status, obj.get_status_display())

    @admin.display(description="Proof of payment")
    def pop_link(self, obj):
        if not obj.proof_of_payment:
            return "—"
        try:
            return format_html('<a href="{}" target="_blank">View PoP</a>', obj.proof_of_payment.url)
        except Exception:
            return "uploaded"

    @admin.action(description="Mark as PAID (confirm payment, unlock downloads)")
    def mark_paid(self, request, queryset):
        _set_status(self, request, queryset, Order.PAID, only_from=[Order.PENDING])

    @admin.action(description="Mark as shipped / ready for collection")
    def mark_shipped(self, request, queryset):
        _set_status(self, request, queryset, Order.SHIPPED, only_from=[Order.PAID])

    @admin.action(description="Mark as completed")
    def mark_completed(self, request, queryset):
        _set_status(self, request, queryset, Order.COMPLETED, only_from=[Order.PAID, Order.SHIPPED])

    @admin.action(description="Cancel and return stock")
    @transaction.atomic
    def cancel_and_restock(self, request, queryset):
        n = 0
        for order in queryset.exclude(status=Order.CANCELLED):
            for item in order.items.select_related("product"):
                if not item.product.is_digital:
                    Product.objects.filter(pk=item.product_id).update(stock=item.product.stock + item.quantity)
            order.status = Order.CANCELLED
            order.save()
            send_status_update(order)
            n += 1
        self.message_user(request, f"{n} order(s) cancelled and stock returned.", messages.WARNING)

    @admin.action(description="Export selected orders to CSV")
    def export_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="orders.csv"'
        w = csv.writer(resp)
        w.writerow(["Order", "Date", "Name", "Email", "Phone", "City", "Items", "Total", "Status", "Payment ref"])
        for o in queryset:
            items = "; ".join(f"{i.quantity}x {i.product.name}" for i in o.items.all())
            w.writerow([o.short_id, o.created.date(), o.full_name, o.email, o.phone, o.city, items,
                        f"{o.total:.2f}", o.get_status_display(), o.payment_reference])
        return resp

    def save_model(self, request, obj, form, change):
        old = Order.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if change and old != obj.status:
            send_status_update(obj)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("donor_name", "email", "amount", "purpose", "status_badge", "payment_reference", "created")
    list_filter = ("status", "created")
    search_fields = ("donor_name", "email", "payment_reference", "purpose")
    date_hierarchy = "created"
    actions = ["confirm"]

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return badge(obj.status, obj.get_status_display())

    @admin.action(description="Confirm selected donations")
    def confirm(self, request, queryset):
        n = queryset.update(status=Donation.CONFIRMED)
        self.message_user(request, f"{n} donation(s) confirmed.")


@admin.register(Executive)
class ExecutiveAdmin(admin.ModelAdmin):
    list_display = ("photo_thumb", "name", "position", "order", "is_active")
    list_display_links = ("photo_thumb", "name")
    list_editable = ("order", "is_active")
    search_fields = ("name", "position")
    actions = ["show", "hide"]

    @admin.display(description="")
    def photo_thumb(self, obj):
        return format_html('<img class="bcu-thumb" style="border-radius:50%" src="{}">', obj.photo.url) if obj.photo else "👤"

    @admin.action(description="Show on the landing page")
    def show(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Hide from the landing page")
    def hide(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("role", "name", "phone", "order")
    list_editable = ("name", "phone", "order")
    search_fields = ("role", "name", "phone")
