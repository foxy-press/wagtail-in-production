import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DEBUG", "1") == "1"
# In production the key must come from the environment: a missing variable fails loudly at startup.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret") if DEBUG else os.environ["SECRET_KEY"]
# Every Site hostname must be here too, or Django answers 400 (chapter 8). ".localhost" matches any subdomain.
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,.localhost,127.0.0.1").split(",")
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")

INSTALLED_APPS = [
    "core",
    "pages",
    "blog",
    "wagtail.api.v2",
    "wagtail.api.v3",
    "rest_framework",
    "wagtail.locales",
    "wagtail.contrib.simple_translation",
    "wagtail.contrib.search_promotions",
    "wagtail.contrib.frontend_cache",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.settings",
    "wagtail.contrib.sitemaps",
    "wagtail.contrib.table_block",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "core.middleware.PageViewMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite for development; PostgreSQL in production and CI (chapter 15), configured from the environment.
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "studio"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("DATABASE_PATH", BASE_DIR / "db.sqlite3"),
        }
    }

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True

# Translation (chapter 8). Content languages must also be in LANGUAGES.
WAGTAIL_I18N_ENABLED = True
LANGUAGES = WAGTAIL_CONTENT_LANGUAGES = [("en-gb", "English"), ("cy", "Welsh")]
# Copying a page for translation also creates its missing parents in the target locale.
WAGTAILSIMPLETRANSLATION_SYNC_PAGE_TREE = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# In production, collectstatic adds a content hash to every file name (app.3f2a9c1b.css), so the web server
# can cache static files for a year (chapter 15).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage."
        + ("StaticFilesStorage" if DEBUG else "ManifestStaticFilesStorage")
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

WAGTAIL_SITE_NAME = "Studio"
WAGTAILADMIN_BASE_URL = SITE_URL
WAGTAIL_ADMIN_PATH = os.environ.get("WAGTAIL_ADMIN_PATH", "studio-admin/").strip("/") + "/"
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
WAGTAILIMAGES_EXTENSIONS = ["gif", "jpg", "jpeg", "png", "webp", "avif"]
WAGTAILDOCS_EXTENSIONS = ["pdf", "docx", "xlsx", "csv", "txt"]
WAGTAIL_ENABLE_UPDATE_CHECK = False

# Headless (chapter 7)
WAGTAILAPI_BASE_URL = SITE_URL  # absolute URLs for images and documents in API responses
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")  # where the headless front end lives, if there is one
FRONTEND_REBUILD_HOOK = os.environ.get("FRONTEND_REBUILD_HOOK", "")  # e.g. a static host's deploy hook URL

# Performance (chapter 10)
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}  # use Redis or Memcached in production
# Purge pages from a caching proxy or CDN when they're published. Each backend is enabled only when configured.
WAGTAILFRONTENDCACHE = {}
if os.environ.get("VARNISH_URL"):
    WAGTAILFRONTENDCACHE["varnish"] = {
        "BACKEND": "wagtail.contrib.frontend_cache.backends.HTTPBackend",
        "LOCATION": os.environ["VARNISH_URL"],
    }

# Fail on anything Wagtail removes in its next major version (chapter 13). Set STRICT_DEPRECATIONS=1 in CI.
# `python -W error::...` and PYTHONWARNINGS don't work for this: importing wagtail calls
# warnings.simplefilter("default", RemovedInWagtail90Warning), which takes priority. So import wagtail
# first, then add the filter, before Django loads any app.
if os.environ.get("STRICT_DEPRECATIONS") == "1":
    import warnings

    import wagtail  # noqa: F401
    from wagtail.utils.deprecation import RemovedInWagtail90Warning

    warnings.filterwarnings("error", category=RemovedInWagtail90Warning)

# Production security (chapter 14). Studio runs behind a proxy that terminates HTTPS (chapter 15).
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    CSRF_TRUSTED_ORIGINS = [f"https://{host.lstrip('.')}" for host in ALLOWED_HOSTS if host and host[0] != "."]
