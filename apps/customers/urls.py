from django.urls import path

from apps.customers import views

urlpatterns = [
    path("customers/", views.customer_directory, name="customer_directory"),
    path("customers/new/", views.record_customer, name="record_customer"),
    path("customers/<int:pk>/edit/", views.edit_customer, name="edit_customer"),
]
