"""A URLconf with a view that refuses without naming a permission."""

from django.core.exceptions import PermissionDenied
from django.urls import path

from config.urls import handler403
from config.urls import urlpatterns as project_urls


def a_bare_refusal(_request):
    raise PermissionDenied


urlpatterns = [path("refused/", a_bare_refusal), *project_urls]

__all__ = ["handler403", "urlpatterns"]
