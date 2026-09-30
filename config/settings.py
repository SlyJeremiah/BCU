import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "https://*.vercel.app").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "storages",
    "shop",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shop.context_processors.shop",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: Neon Postgres via DATABASE_URL, SQLite locally.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=0, ssl_require=False
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Harare"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# ---- Backblaze B2 (S3-compatible) -------------------------------------------
# Public bucket: product images. Private bucket: digital products (signed URLs).
B2_KEY_ID = os.environ.get("B2_KEY_ID", "")
B2_APP_KEY = os.environ.get("B2_APP_KEY", "")
B2_ENDPOINT_URL = os.environ.get("B2_ENDPOINT_URL", "")  # e.g. https://s3.us-west-004.backblazeb2.com
B2_REGION = os.environ.get("B2_REGION", "us-west-004")
B2_PUBLIC_BUCKET = os.environ.get("B2_PUBLIC_BUCKET", "")
# Optional: if unset, private files share the public bucket under private/ (unguessable names, signed URLs).
B2_PRIVATE_BUCKET = os.environ.get("B2_PRIVATE_BUCKET", "")
USE_B2 = bool(B2_KEY_ID and B2_APP_KEY and B2_ENDPOINT_URL and B2_PUBLIC_BUCKET)

if USE_B2:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": B2_KEY_ID,
                "secret_key": B2_APP_KEY,
                "bucket_name": B2_PUBLIC_BUCKET,
                "endpoint_url": B2_ENDPOINT_URL,
                "region_name": B2_REGION,
                "querystring_auth": False,
                "file_overwrite": False,
                "signature_version": "s3v4",
            },
        },
        "private": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": B2_KEY_ID,
                "secret_key": B2_APP_KEY,
                "bucket_name": B2_PRIVATE_BUCKET or B2_PUBLIC_BUCKET,
                "location": "" if B2_PRIVATE_BUCKET else "private",
                "endpoint_url": B2_ENDPOINT_URL,
                "region_name": B2_REGION,
                "querystring_auth": True,
                "querystring_expire": 300,
                "file_overwrite": False,
                "signature_version": "s3v4",
            },
        },
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "private": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(BASE_DIR / "media_private")},
        },
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }

# ---- DRF / JWT ----------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min"},
}
SIMPLE_JWT = {"ACCESS_TOKEN_LIFETIME": timedelta(hours=1), "REFRESH_TOKEN_LIFETIME": timedelta(days=7)}
CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o]

# ---- Email --------------------------------------------------------------------
if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = True
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "BCU Shop <no-reply@bcushop.org>")
SHOP_ADMIN_EMAIL = os.environ.get("SHOP_ADMIN_EMAIL", "")

# ---- Shop configuration (shown to customers) ------------------------------------
SHOP = {
    "NAME": "BCU Shop",
    "ORG": "Boys Christian Union",
    "CHURCH": "The Methodist Church in Zimbabwe",
    "CURRENCY": os.environ.get("SHOP_CURRENCY", "USD"),
    "CURRENCY_SYMBOL": os.environ.get("SHOP_CURRENCY_SYMBOL", "$"),
    "PAYMENT_INSTRUCTIONS": os.environ.get(
        "PAYMENT_INSTRUCTIONS",
        "Pay by bank transfer or EcoCash, then enter the transaction reference and upload your proof of payment (PoP). "
        "An administrator will confirm your payment.",
    ),
    "ECOCASH_NUMBER": os.environ.get("ECOCASH_NUMBER", "+263 78 551 0151"),
    "ECOCASH_NAME": os.environ.get("ECOCASH_NAME", "BCU Treasurer"),
    "BANK": {
        "Account name": os.environ.get("BANK_ACCOUNT_NAME", "Methodist Church in Zimbabwe Youth"),
        "Bank": os.environ.get("BANK_NAME", "BancABC"),
        "Branch": os.environ.get("BANK_BRANCH", "Heritage"),
        "Branch code": os.environ.get("BANK_BRANCH_CODE", "21125"),
        "Account number": os.environ.get("BANK_ACCOUNT_NUMBER", "12873696633189"),
    },
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
