"""Settings for the test suite: production settings, independent of any `.env`."""

import os

os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_HTTPS_ONLY"] = "False"
os.environ["DJANGO_EMAIL_HOST"] = ""
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key")

from config.settings import *  # noqa: F403

# Manifest storage needs `collectstatic` to have run.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
