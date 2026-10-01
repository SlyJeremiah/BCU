from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Order, Product

User = get_user_model()


class ShopFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bob", "bob@example.com", "pw12345678")
        self.tie = Product.objects.create(name="Tie", price="6.00", stock=3)
        self.pdf = Product.objects.create(name="Hymns", price="3.00", kind="digital")

    def _checkout(self, pids):
        self.client.login(username="bob", password="pw12345678")
        for pid in pids:
            self.client.post(reverse("cart_add", args=[pid]), {"quantity": 2})
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("checkout"), {
                "full_name": "Bob", "email": "bob@example.com", "phone": "077",
                "address": "1 Main St", "city": "Harare", "payment_reference": "EC123"})

    def test_full_flow_and_stock(self):
        r = self._checkout([self.tie.pk, self.pdf.pk])
        order = Order.objects.get()
        self.assertRedirects(r, reverse("order_detail", args=[order.pk]))
        self.tie.refresh_from_db()
        self.assertEqual(self.tie.stock, 1)
        self.assertEqual(str(order.total), "15.00")
        self.assertEqual(len(mail.outbox), 1)

    def test_download_locked_until_paid(self):
        self._checkout([self.pdf.pk])
        order = Order.objects.get()
        item = order.items.get()
        url = reverse("download", args=[order.pk, item.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        order.status = Order.PAID
        order.save()
        self.pdf.digital_file.save("h.pdf", __import__("django.core.files.base", fromlist=["ContentFile"]).ContentFile(b"x"))
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_orders_are_private(self):
        self._checkout([self.tie.pk])
        order = Order.objects.get()
        User.objects.create_user("eve", password="pw12345678")
        self.client.login(username="eve", password="pw12345678")
        self.assertEqual(self.client.get(reverse("order_detail", args=[order.pk])).status_code, 404)

    def test_api_jwt_order(self):
        c = APIClient()
        tok = c.post("/api/token/", {"username": "bob", "password": "pw12345678"}).data["access"]
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        r = c.post("/api/orders/", {"full_name": "Bob", "email": "b@e.com", "phone": "1", "address": "a", "city": "c",
                                    "lines": [{"product": self.tie.pk, "quantity": 99}]}, format="json")
        self.assertEqual(r.status_code, 400)  # exceeds stock
        r = c.post("/api/orders/", {"full_name": "Bob", "email": "b@e.com", "phone": "1", "address": "a", "city": "c",
                                    "lines": [{"product": self.tie.pk, "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(c.get("/api/products/").status_code, 200)

    def test_order_pdf(self):
        self._checkout([self.tie.pk])
        order = Order.objects.get()
        r = self.client.get(reverse("order_pdf", args=[order.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))
        User.objects.create_user("eve", password="pw12345678")
        self.client.login(username="eve", password="pw12345678")
        self.assertEqual(self.client.get(reverse("order_pdf", args=[order.pk])).status_code, 404)

    def test_donation(self):
        r = self.client.post(reverse("donate"), {"donor_name": "A", "email": "a@a.com", "amount": "10"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
