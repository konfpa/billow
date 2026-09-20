"""Root URL configuration.

Reference: https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from config.health import healthz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path(settings.ADMIN_URL, admin.site.urls),
]

if settings.DEBUG:
    # In production the reverse proxy (or WhiteNoise) serves these; Django
    # only stands in for it during development.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "billow administration"
admin.site.site_title = "billow"
admin.site.index_title = "billow"
