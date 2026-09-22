from django.urls import path

from apps.catalogue import views

urlpatterns = [
    path("items/", views.item_directory, name="item_directory"),
    path("items/new/", views.record_item, name="record_item"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("items/<int:pk>/edit/", views.edit_item, name="edit_item"),
    path("items/<int:pk>/duplicate/", views.duplicate_item, name="duplicate_item"),
    path("brands/", views.brand_directory, name="brand_directory"),
    path("brands/new/", views.record_brand, name="record_brand"),
    path("brands/<int:pk>/edit/", views.edit_brand, name="edit_brand"),
    path("categories/", views.category_directory, name="category_directory"),
    path("categories/new/", views.record_category, name="record_category"),
    path("categories/<int:pk>/edit/", views.edit_category, name="edit_category"),
]
