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

# The test suite sets this so that it configures itself entirely from
# tests/settings.py. Without the opt-out, every variable that file does not pin
# is still answered by whatever a developer happens to have in their `.env`,
# and the suite tests a different configuration on each machine.
if env.bool("DJANGO_READ_DOT_ENV", default=True):
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
    "apps.accounts",
    "apps.business",
    "apps.core",
    "apps.customers",
    "apps.suppliers",
    "apps.catalogue",
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
    # Holds billow shut until the Business is complete; needs the request's
    # user, so it runs after AuthenticationMiddleware.
    "apps.business.middleware.SetupGateMiddleware",
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

_database = env.db_url("DJANGO_DATABASE_URL")
_database_options = _database.get("OPTIONS", {})

DATABASES = {
    "default": {
        **_database,
        # Billing data warrants all-or-nothing requests: any unhandled
        # exception rolls the whole request back.
        "ATOMIC_REQUESTS": True,
        # Reuse connections across requests rather than reconnecting on each.
        # Every thread holds its own; docker/gunicorn.conf.py works out what
        # that totals against the server's max_connections.
        "CONN_MAX_AGE": env.int("DJANGO_CONN_MAX_AGE", default=60),
        # A pooler or a failover can close a connection this process still
        # believes in; without this the first query on it raises instead of
        # transparently reconnecting.
        "CONN_HEALTH_CHECKS": True,
        # Merged rather than replaced: the URL's own options (sslmode,
        # connect_timeout) are parsed into OPTIONS and would be dropped.
        "OPTIONS": {
            **_database_options,
            # Bounds a statement that would otherwise hold locks indefinitely.
            # It is a connection parameter, so it applies to migrations too;
            # compose.prod.yaml sets it to 0 for the migrate service.
            #
            # Appended to whatever the URL's own `options` carried rather than
            # assigned: a `?options=-c search_path%3Dtenant` would otherwise be
            # dropped here and every query would read the wrong schema. Later
            # `-c` flags win, so the timeout still applies.
            "options": " ".join(
                part
                for part in (
                    _database_options.get("options"),
                    f"-c statement_timeout={env.int('DJANGO_STATEMENT_TIMEOUT_MS', default=30000)}",
                )
                if part
            ),
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

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

# billow has its own front door; the admin's login page is for the admin.
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

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
_media_root = env("DJANGO_MEDIA_ROOT", cast=Path, default=BASE_DIR / "media")

# A relative override would otherwise resolve against the process CWD, which
# differs between a shell, a manage.py run and the container entrypoint.
MEDIA_ROOT = _media_root if _media_root.is_absolute() else BASE_DIR / _media_root

# Uploads live in S3-compatible object storage, because nothing that serves
# this app has a writable disk: the container filesystem is read-only and no
# volume is mounted. Under DEBUG they go to MEDIA_ROOT instead, so local
# development needs no bucket and no credentials.
if DEBUG:
    _media_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}
else:
    _media_storage = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env.str("DJANGO_S3_BUCKET"),
            "access_key": env.str("DJANGO_S3_ACCESS_KEY_ID"),
            "secret_key": env.str("DJANGO_S3_SECRET_ACCESS_KEY"),
            # What makes this any S3-compatible provider rather than AWS.
            "endpoint_url": env.str("DJANGO_S3_ENDPOINT_URL"),
            "region_name": env.str("DJANGO_S3_REGION", default=""),
            # Serve through the CDN hostname in front of the bucket when there
            # is one, so objects are not fetched from the origin per request.
            "custom_domain": env.str("DJANGO_S3_CUSTOM_DOMAIN", default="") or None,
            # Neither B2 nor R2 implements ACLs; sending one is an error rather
            # than a no-op. Object visibility is a bucket-level setting there.
            "default_acl": None,
            "querystring_auth": env.bool("DJANGO_S3_QUERYSTRING_AUTH", default=True),
            "querystring_expire": env.int("DJANGO_S3_QUERYSTRING_EXPIRE", default=3600),
            # Keep an upload that collides with an existing name rather than
            # overwriting it: these are invoices and attachments, not a cache.
            "file_overwrite": False,
            "signature_version": "s3v4",
            "addressing_style": env.str(
                "DJANGO_S3_ADDRESSING_STYLE", default="virtual"
            ),
        },
    }

STORAGES = {
    "default": _media_storage,
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

# No application code sends mail yet. This is configured ahead of that because
# the mail_admins handler in LOGGING is the only route an unhandled production
# exception has out of the process, and because deployment credentials are
# easier to set once here than to retrofit later when the first sender lands.
#
# Without an SMTP host, mail is written to stdout instead of being sent.
_smtp_host = env.str("DJANGO_EMAIL_HOST", default="")

if _smtp_host:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": _smtp_host,
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
_https_only = env.bool("DJANGO_HTTPS_ONLY", default=not DEBUG)

SECURE_SSL_REDIRECT = _https_only
SECURE_HSTS_SECONDS = (
    env.int("DJANGO_HSTS_SECONDS", default=31536000) if _https_only else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _https_only
SECURE_HSTS_PRELOAD = _https_only
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True

# The healthcheck hits plain HTTP over loopback; redirecting it to HTTPS would
# make the container permanently unhealthy.
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]

SESSION_COOKIE_SECURE = _https_only
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = _https_only
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

_log_level = env.str("DJANGO_LOG_LEVEL", default="INFO").upper()

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
        "level": _log_level,
    },
    "loggers": {
        # Clears the handlers Django attaches by default so records reach the
        # root handlers exactly once.
        "django": {"handlers": [], "level": _log_level},
        # Bots probing with bogus Host headers would otherwise mail the admins
        # on every scan.
        "django.security.DisallowedHost": {
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
