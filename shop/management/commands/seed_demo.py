from django.core.management.base import BaseCommand

from shop.models import Category, Product


class Command(BaseCommand):
    help = "Create demo categories and products"

    def handle(self, *args, **opts):
        apparel, _ = Category.objects.get_or_create(name="Apparel")
        media, _ = Category.objects.get_or_create(name="Sermons & Resources")
        items = [
            ("BCU Red Tie", apparel, "physical", "6.00", 40, "Official BCU red tie."),
            ("BCU Badge", apparel, "physical", "2.50", 100, "Embroidered BCU badge."),
            ("BCU White Blazer", apparel, "physical", "45.00", 10, "Official white BCU blazer."),
            ("BCU Hymn Book (PDF)", media, "digital", "3.00", 0, "Digital hymn collection."),
            ("Annual Convention Sermon (MP3)", media, "digital", "2.00", 0, "Audio of the convention sermon."),
        ]
        for name, cat, kind, price, stock, desc in items:
            Product.objects.get_or_create(name=name, defaults=dict(
                category=cat, kind=kind, price=price, stock=stock, description=desc))
        self.stdout.write(self.style.SUCCESS("Demo data created."))
