from django.urls import path

from apps.business import views

urlpatterns = [
    path("settings/business/", views.business_settings, name="business_settings"),
]
