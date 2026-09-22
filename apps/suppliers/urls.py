from django.urls import path

from apps.suppliers import views

urlpatterns = [
    path("suppliers/", views.supplier_directory, name="supplier_directory"),
    path("suppliers/new/", views.record_supplier, name="record_supplier"),
    path("suppliers/<int:pk>/", views.supplier_detail, name="supplier_detail"),
    path("suppliers/<int:pk>/edit/", views.edit_supplier, name="edit_supplier"),
    path(
        "suppliers/<int:pk>/archive/",
        views.archive_supplier,
        name="archive_supplier",
    ),
    path(
        "suppliers/<int:pk>/restore/",
        views.restore_supplier,
        name="restore_supplier",
    ),
]
