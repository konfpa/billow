from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


@login_required
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html")
