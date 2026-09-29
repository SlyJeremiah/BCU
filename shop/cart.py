from decimal import Decimal

from .models import Product


class Cart:
    """Session cart: {product_id: quantity}."""

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault("cart", {})

    def _save(self):
        self.session.modified = True

    def add(self, product, qty=1):
        key = str(product.pk)
        new = self.data.get(key, 0) + qty
        if product.is_digital:
            new = 1
        else:
            new = min(new, product.stock)
        if new > 0:
            self.data[key] = new
        self._save()

    def set(self, product, qty):
        key = str(product.pk)
        if qty <= 0:
            self.data.pop(key, None)
        else:
            self.data[key] = 1 if product.is_digital else min(qty, product.stock)
        self._save()

    def remove(self, product):
        self.data.pop(str(product.pk), None)
        self._save()

    def clear(self):
        self.session["cart"] = {}
        self._save()

    def items(self):
        products = Product.objects.filter(pk__in=self.data.keys(), is_active=True)
        out = []
        for p in products:
            q = self.data[str(p.pk)]
            out.append({"product": p, "quantity": q, "line_total": p.price * q})
        return out

    @property
    def total(self):
        return sum((i["line_total"] for i in self.items()), Decimal("0"))

    def has_physical(self):
        return any(not i["product"].is_digital for i in self.items())

    def __len__(self):
        return sum(self.data.values())
