from django.conf import settings
from django.core.mail import send_mail


def _money(v):
    return f"{settings.SHOP['CURRENCY_SYMBOL']}{v:.2f}"


def _lines(order):
    return "\n".join(f"  {i.quantity} x {i.product.name} – {_money(i.line_total)}" for i in order.items.all())


def send_order_created(order):
    body = (
        f"Hello {order.full_name},\n\nThank you for your order {order.short_id} with {settings.SHOP['NAME']}.\n\n"
        f"{_lines(order)}\n\nTotal: {_money(order.total)}\n\n"
        f"{settings.SHOP['PAYMENT_INSTRUCTIONS']}\nNumber: {settings.SHOP['PAYMENT_NUMBER']} "
        f"({settings.SHOP['PAYMENT_NAME']})\n\nWe will email you once your payment is confirmed."
    )
    send_mail(f"Order {order.short_id} received", body, None, [order.email], fail_silently=True)
    if settings.SHOP_ADMIN_EMAIL:
        send_mail(
            f"New order {order.short_id}",
            f"{order.full_name} ({order.email}, {order.phone}) placed an order totalling {_money(order.total)}.\n"
            f"Payment ref: {order.payment_reference or '-'}",
            None, [settings.SHOP_ADMIN_EMAIL], fail_silently=True,
        )


def send_status_update(order):
    extra = "\nYou can download digital items from your order page." if order.downloads_unlocked else ""
    send_mail(
        f"Order {order.short_id}: {order.get_status_display()}",
        f"Hello {order.full_name},\n\nYour order {order.short_id} is now: {order.get_status_display()}.{extra}\n",
        None, [order.email], fail_silently=True,
    )


def send_donation_received(donation):
    send_mail(
        "Thank you for your donation",
        f"Dear {donation.donor_name},\n\nThank you for pledging {_money(donation.amount)} to "
        f"{settings.SHOP['ORG']}. Please complete the payment:\n{settings.SHOP['PAYMENT_INSTRUCTIONS']}\n"
        f"Number: {settings.SHOP['PAYMENT_NUMBER']}\n\nGod bless you.",
        None, [donation.email], fail_silently=True,
    )
    if settings.SHOP_ADMIN_EMAIL:
        send_mail("New donation pledge", f"{donation.donor_name}: {_money(donation.amount)} ({donation.purpose})",
                  None, [settings.SHOP_ADMIN_EMAIL], fail_silently=True)
