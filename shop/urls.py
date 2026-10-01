from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="product_list"),
    path("shop/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/quote.pdf", views.quote_pdf_view, name="quote_pdf"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<uuid:pk>/", views.order_detail, name="order_detail"),
    path("orders/<uuid:pk>/pdf/", views.order_pdf_view, name="order_pdf"),
    path("orders/<uuid:pk>/download/<int:item_id>/", views.download, name="download"),
    path("donate/", views.donate, name="donate"),
    path("accounts/register/", views.register, name="register"),
]
