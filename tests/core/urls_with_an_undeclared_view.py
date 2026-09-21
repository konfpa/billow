"""A URLconf with a view that declares no permission and is not exempt."""

from django.http import HttpResponse
from django.urls import path

from config.urls import urlpatterns as project_urls


def an_undeclared_view(_request) -> HttpResponse:
    return HttpResponse("open to everyone")


urlpatterns = [
    path("undeclared/", an_undeclared_view, name="an_undeclared_view"),
    *project_urls,
]
