"""Django settings for the billow project.

Every environment-specific value is read from the environment (optionally via a
`.env` file at the repository root); see `.env.example` for the full list.

Reference: https://docs.djangoproject.com/en/6.1/ref/settings/
"""

from pathlib import Path

import environ
from django.utils.csp import CSP

# ---------------------------------------------------------------------------
# Paths and environment
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

# An insecure fallback is tolerable while DEBUG is on, but production must fail
# loudly rather than silently run on a throwaway key.
if DEBUG:
    SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="django-insecure-dev-only-key")
else:
    SECRET_KEY = env.str("DJANGO_SECRET_KEY")

# Supports zero-downtime key rotation: keep the previous key here until all
# outstanding sessions and signed values have expired.
SECRET_KEY_FALLBACKS = env.list("DJANGO_SECRET_KEY_FALLBACKS", default=[])

# The container healthcheck reaches the app over loopback, so those hosts are
# always accepted regardless of the public hostnames configured.
ALLOWED_HOSTS = [
    *env.list("DJANGO_ALLOWED_HOSTS", default=[]),
    "localhost",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

ADMINS = env.list("DJANGO_ADMINS", default=[])
MANAGERS = ADMINS

# ---------------------------------------------------------------------------
# Applications and middleware
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simple_history",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Must sit directly after SecurityMiddleware so static files are served
    # without paying for the rest of the stack.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    # Stamps the acting user onto historical records; must run after
    # AuthenticationMiddleware.
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env("DJANGO_DB_PATH", cast=Path, default=BASE_DIR / "db.sqlite3"),
        # Billing data warrants all-or-nothing requests: any unhandled
        # exception rolls the whole request back.
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {
            # WAL lets readers run concurrently with a writer; NORMAL sync is
            # safe under WAL and far cheaper than FULL. busy_timeout makes
            # writers queue instead of raising "database is locked".
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA busy_timeout=5000;"
                "PRAGMA foreign_keys=ON;"
                "PRAGMA temp_store=MEMORY;"
            ),
            # Take the write lock up front so concurrent transactions fail at
            # BEGIN rather than halfway through with SQLITE_BUSY.
            "transaction_mode": "IMMEDIATE",
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "admin:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = env.str("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT", cast=Path, default=BASE_DIR / "media")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Manifest hashing in production only: it requires `collectstatic` to
        # have run, which would break `runserver`.
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

# Without an SMTP host, mail is written to stdout instead of being sent.
SMTP_HOST = env.str("DJANGO_EMAIL_HOST", default="")

if SMTP_HOST:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": SMTP_HOST,
                "port": env.int("DJANGO_EMAIL_PORT", default=587),
                "username": env.str("DJANGO_EMAIL_HOST_USER", default=""),
                "password": env.str("DJANGO_EMAIL_HOST_PASSWORD", default=""),
                "use_tls": env.bool("DJANGO_EMAIL_USE_TLS", default=True),
                "use_ssl": env.bool("DJANGO_EMAIL_USE_SSL", default=False),
                "timeout": env.int("DJANGO_EMAIL_TIMEOUT", default=10),
            },
        },
    }
else:
    MAILERS = {
        "default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"},
    }

DEFAULT_FROM_EMAIL = env.str("DJANGO_DEFAULT_FROM_EMAIL", default="billow@localhost")
SERVER_EMAIL = env.str("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = "[billow] "

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

# TLS is terminated at the reverse proxy, so Django learns the original scheme
# from the header the proxy sets. The proxy MUST overwrite it on every request.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# One switch for everything that assumes HTTPS, so a plain-HTTP deployment
# (internal network, staging) stays usable without running in DEBUG.
HTTPS_ONLY = env.bool("DJANGO_HTTPS_ONLY", default=not DEBUG)

SECURE_SSL_REDIRECT = HTTPS_ONLY
SECURE_HSTS_SECONDS = (
    env.int("DJANGO_HSTS_SECONDS", default=31536000) if HTTPS_ONLY else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = HTTPS_ONLY
SECURE_HSTS_PRELOAD = HTTPS_ONLY
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True

# The healthcheck hits plain HTTP over loopback; redirecting it to HTTPS would
# make the container permanently unhealthy.
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]

SESSION_COOKIE_SECURE = HTTPS_ONLY
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = HTTPS_ONLY
CSRF_COOKIE_SAMESITE = "Lax"

X_FRAME_OPTIONS = "DENY"

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
}

# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

# Moving the admin off the well-known path cuts most drive-by credential
# stuffing; it is obscurity, not a substitute for strong passwords.
ADMIN_URL = env.str("DJANGO_ADMIN_URL", default="admin/")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL = env.str("DJANGO_LOG_LEVEL", default="INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        # Containers collect logs from stdout/stderr; writing to files would
        # hide them inside the container filesystem.
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "filters": ["require_debug_false"],
        },
    },
    "root": {
        "handlers": ["console", "mail_admins"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        # Clears the handlers Django attaches by default so records reach the
        # root handlers exactly once.
        "django": {"handlers": [], "level": LOG_LEVEL},
        # Bots probing with bogus Host headers would otherwise mail the admins
        # on every scan.
        "django.security.DisallowedHost": {
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
