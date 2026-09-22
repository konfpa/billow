from django.urls import path

from apps.purchases import views

urlpatterns = [
    path("purchases/", views.purchase_directory, name="purchase_directory"),
    path("purchases/new/", views.record_purchase, name="record_purchase"),
    path("purchases/<int:pk>/", views.purchase_detail, name="purchase_detail"),
]
