"""A URLconf with a view nobody taught about the setup gate."""

from django.http import HttpResponse
from django.urls import path

from config.urls import urlpatterns as project_urls


def a_new_view(_request) -> HttpResponse:
    return HttpResponse("ungated")


urlpatterns = [path("a-new-view/", a_new_view, name="a_new_view"), *project_urls]
