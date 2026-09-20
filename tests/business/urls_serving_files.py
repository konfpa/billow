"""A URLconf that routes static and media through Django, as DEBUG does.

Outside DEBUG neither prefix resolves, so a request for one 404s at the
resolver and the gate is never consulted — which is no proof that it would
let the file through. Here they resolve, so the gate has to.
"""

from django.conf import settings
from django.urls import path
from django.views.static import serve

from config.urls import urlpatterns as project_urls


def serve_media(request, path):
    # Read per request: the suite points MEDIA_ROOT at a temporary directory.
    return serve(request, path, document_root=settings.MEDIA_ROOT)


def serve_static(request, path):
    return serve(request, path, document_root=settings.STATICFILES_DIRS[0])


urlpatterns = [
    path("media/<path:path>", serve_media),
    path("static/<path:path>", serve_static),
    *project_urls,
]
