from django.urls import path

from apps.customers import views

urlpatterns = [
    path("customers/", views.customer_directory, name="customer_directory"),
    path("customers/new/", views.record_customer, name="record_customer"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.edit_customer, name="edit_customer"),
    path(
        "customers/<int:pk>/archive/",
        views.archive_customer,
        name="archive_customer",
    ),
    path(
        "customers/<int:pk>/restore/",
        views.restore_customer,
        name="restore_customer",
    ),
]
