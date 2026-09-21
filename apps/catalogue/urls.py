from django.urls import path

from apps.catalogue import views

urlpatterns = [
    path("items/", views.item_directory, name="item_directory"),
    path("items/new/", views.record_item, name="record_item"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("items/<int:pk>/edit/", views.edit_item, name="edit_item"),
]
