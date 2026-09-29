from django.db import transaction

from .emails import send_order_created
from .models import Order, OrderItem, Product


class CheckoutError(Exception):
    pass


@transaction.atomic
def create_order(user, data, lines):
    """lines: iterable of (product_id, quantity). Validates stock and decrements it."""
    lines = [(int(pid), int(q)) for pid, q in lines if int(q) > 0]
    if not lines:
        raise CheckoutError("Your cart is empty.")
    products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[l[0] for l in lines], is_active=True)}
    order = Order.objects.create(user=user, **data)
    physical = False
    for pid, qty in lines:
        p = products.get(pid)
        if not p:
            raise CheckoutError("A product in your cart is no longer available.")
        if p.is_digital:
            qty = 1
        else:
            physical = True
            if qty > p.stock:
                raise CheckoutError(f"Only {p.stock} of “{p.name}” left in stock.")
            p.stock -= qty
            p.save(update_fields=["stock"])
        OrderItem.objects.create(order=order, product=p, price=p.price, quantity=qty)
    if physical and not (order.address and order.city):
        raise CheckoutError("A delivery address and city are required for physical items.")
    transaction.on_commit(lambda: send_order_created(order))
    return order
