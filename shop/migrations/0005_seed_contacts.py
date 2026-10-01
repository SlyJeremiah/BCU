from django.db import migrations

CONTACTS = [
    ("Tailor", "Mr. Mabure", "+263 77 370 7319"),
    ("Jerseys producer", "Mrs. Chihoro", "+263 71 844 1525"),
    ("Pins", "Fairkiss", "+263 78 868 4283"),
    ("Cards and Constitution", "Mr. Mudzinganirwa", "0772480223"),
]


def seed(apps, schema_editor):
    Contact = apps.get_model("shop", "Contact")
    for i, (role, name, phone) in enumerate(CONTACTS):
        Contact.objects.get_or_create(role=role, defaults={"name": name, "phone": phone, "order": i})


class Migration(migrations.Migration):
    dependencies = [("shop", "0004_executive_contact")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
