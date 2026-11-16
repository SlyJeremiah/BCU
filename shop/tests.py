from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Contact, Executive, Order, Product

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

    def test_cart_remove_offers_undo(self):
        self.client.post(reverse("cart_add", args=[self.tie.pk]), {"quantity": 2})
        hx = {"HTTP_HX_REQUEST": "true"}
        r = self.client.post(reverse("cart_remove", args=[self.tie.pk]), **hx)
        self.assertContains(r, "Undo")
        self.assertContains(r, 'hx-swap-oob="innerHTML:#cart-badge"')
        self.assertEqual(self.client.get(reverse("cart")).context["items"], [])
        r = self.client.post(reverse("cart_undo"), **hx)
        self.assertNotContains(r, "Undo")
        items = self.client.get(reverse("cart")).context["items"]
        self.assertEqual(items[0]["quantity"], 2)

    def test_quote_pdf(self):
        self.client.login(username="bob", password="pw12345678")
        self.assertRedirects(self.client.get(reverse("quote_pdf")), reverse("cart"))
        self.client.post(reverse("cart_add", args=[self.tie.pk]), {"quantity": 2})
        r = self.client.get(reverse("quote_pdf"))
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(r["Content-Type"], "application/pdf")

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


class TeamAndContactTests(TestCase):
    def test_landing_shows_only_active_executives(self):
        Executive.objects.create(name="Ann Moyo", position="Chairperson")
        Executive.objects.create(name="Hidden Person", position="Secretary", is_active=False)
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Ann Moyo")
        self.assertContains(r, "Meet")
        self.assertNotContains(r, "Hidden Person")

    def test_no_team_section_when_empty(self):
        self.assertNotContains(self.client.get(reverse("home")), 'id="team"')

    def test_contacts_seeded_and_tel_links(self):
        self.assertEqual(Contact.objects.count(), 4)
        self.assertEqual(Contact.objects.get(role="Cards and Constitution").tel, "+263772480223")
        self.assertEqual(Contact.objects.get(role="Tailor").tel, "+263773707319")

    def test_admin_dashboard_lists_contacts(self):
        u = User.objects.create_superuser("adm", "a@a.com", "pw12345678")
        self.client.force_login(u)
        r = self.client.get("/admin/")
        self.assertContains(r, "Mr. Mabure")
        self.assertContains(r, "Fairkiss")
        self.assertEqual(self.client.get("/admin/shop/executive/").status_code, 200)


class FooterAndHelpTests(TestCase):
    PORTAL = "https://mczconnexionalbcu.vercel.app/admin/"

    def test_footer_links_to_officers_portal_safely_on_every_page(self):
        for url in ["/", "/shop/", "/donate/", "/info/privacy/"]:
            r = self.client.get(url)
            self.assertContains(r, f'href="{self.PORTAL}" target="_blank" rel="noopener noreferrer"', msg_prefix=url)
            self.assertContains(r, "BCU officers", msg_prefix=url)

    def test_help_pages_open_and_unknown_page_404s(self):
        for slug, text in [("how-to-order", "How to order and pay"), ("delivery", "Delivery and downloads"), ("privacy", "Privacy")]:
            r = self.client.get(reverse("info", args=[slug]))
            self.assertContains(r, text)
        self.assertEqual(self.client.get("/info/nonsense/").status_code, 404)

    def test_how_to_order_shows_payment_details(self):
        r = self.client.get(reverse("info", args=["how-to-order"]))
        self.assertContains(r, "BancABC")
        self.assertContains(r, "+263 78 551 0151")

    def test_contact_details_appear_only_when_configured(self):
        self.assertNotContains(self.client.get("/"), "mailto:")
        from django.test import override_settings
        from django.conf import settings
        shop = {**settings.SHOP, "CONTACT_EMAIL": "shop@example.org", "CONTACT_PHONE": "+263770000000"}
        with override_settings(SHOP=shop):
            r = self.client.get("/")
            self.assertContains(r, "mailto:shop@example.org")
            self.assertContains(r, "tel:+263770000000")
