# BCU Shop
Online shop for the **Boys Christian Union (BCU)** of **The Methodist Church in Zimbabwe**.

Stack: Django 5 + Django REST Framework (JWT) + HTMX templates, Neon Postgres, Backblaze B2 (S3 API), Vercel.

- **Storefront**: products (physical + digital), HTMX cart/search, accounts, order history, donations.
- **Payments**: mobile money (EcoCash/OneMoney/InnBucks). Customer enters the transaction reference; staff mark the order *Paid* in `/admin/`, which emails the customer and unlocks digital downloads.
- **Storage**: product images in a *public* B2 bucket; digital files in a *private* bucket served via 5-minute signed URLs.
- **API**: `/api/products/`, `/api/categories/`, `/api/orders/` (JWT), `/api/donations/`, `/api/register/`, `/api/token/`.

## Local dev
```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate && python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```
Without B2/Neon env vars it uses SQLite + local folders. See `.env.example` for all settings.

## Deploy (Vercel)
1. Create Neon DB and two B2 buckets (public + private; create an app key with access to both).
2. Import the GitHub repo in Vercel and set the env vars from `.env.example` (`DJANGO_DEBUG=0`).
3. Run `python manage.py migrate` and `createsuperuser` once against the Neon `DATABASE_URL` from your machine.
4. Static files are pre-collected into `staticfiles/` (re-run `python manage.py collectstatic` and commit after CSS changes).
5. For browser uploads/CORS on B2 you only need CORS if uploading from the browser; admin uploads go through Django. Note Vercel request bodies are limited to ~4.5 MB, so upload large digital files directly to the private B2 bucket and paste the object key in the admin *digital file* field.
