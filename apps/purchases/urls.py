from django.urls import path

from apps.purchases import views

urlpatterns = [
    path("purchases/", views.purchase_directory, name="purchase_directory"),
    path("purchases/new/", views.record_purchase, name="record_purchase"),
    path("purchases/items/", views.item_options, name="item_options"),
    path("purchases/<int:pk>/", views.purchase_detail, name="purchase_detail"),
    path("purchases/<int:pk>/edit/", views.edit_purchase, name="edit_purchase"),
    path("purchases/<int:pk>/delete/", views.delete_purchase, name="delete_purchase"),
]
