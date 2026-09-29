from django.conf import settings

from .cart import Cart


def shop(request):
    return {"SHOP": settings.SHOP, "cart_count": len(Cart(request))}
