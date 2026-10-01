from django.urls import path

from . import views


urlpatterns = [
    path('accounts/', views.account_list, name='accounting-account-list'),
    path('accounts/add/', views.account_create, name='accounting-account-create'),
    path('accounts/<int:pk>/', views.account_detail, name='accounting-account-detail'),
    path('accounts/<int:pk>/edit/', views.account_update, name='accounting-account-update'),
    path('adjustments/add/', views.manual_adjustment, name='accounting-manual-adjustment'),
    path('transfers/add/', views.transfer_create, name='accounting-transfer-create'),
    path('transfers/<int:pk>/edit/', views.transfer_update, name='accounting-transfer-update'),
]
