"""Settings for the test suite: production settings, independent of any `.env`."""

import os

# Everything below pins the handful of variables the suite cares about. This
# stops config/settings.py reading `.env` at all, so the rest fall back to
# their declared defaults rather than to whatever this machine has configured.
os.environ["DJANGO_READ_DOT_ENV"] = "False"

os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_HTTPS_ONLY"] = "False"
os.environ["DJANGO_EMAIL_HOST"] = ""
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key")

# The suite runs against a real Postgres, because that is the only engine this
# app supports and a test passing on another one proves less than it appears
# to. Override this to point at your own server.
os.environ.setdefault(
    "DJANGO_DATABASE_URL",
    "postgres://postgres:postgres@localhost:5432/billow_test",
)

# Outside DEBUG the settings module requires a bucket to be configured. Nothing
# here reaches it: STORAGES below replaces the backend entirely.
os.environ.setdefault("DJANGO_S3_BUCKET", "test")
os.environ.setdefault("DJANGO_S3_ACCESS_KEY_ID", "test")
os.environ.setdefault("DJANGO_S3_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("DJANGO_S3_ENDPOINT_URL", "https://test.invalid")

from config.settings import *  # noqa: F403

# Manifest storage needs `collectstatic` to have run, and the S3 backend would
# have the suite talking to a bucket over the network.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
