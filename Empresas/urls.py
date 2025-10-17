from django.urls import path
from .views import (
    EmpresaListCreateAPIView,
    EmpresaRetrieveUpdateDestroyAPIView,
    AreaListCreateAPIView,
    AreaRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path('empresas/', EmpresaListCreateAPIView.as_view(), name='empresa-list-create'),
    path('empresas/<int:pk>/', EmpresaRetrieveUpdateDestroyAPIView.as_view(), name='empresa-detail'),
    path('areas/', AreaListCreateAPIView.as_view(), name='area-list-create'),
    path('areas/<int:pk>/', AreaRetrieveUpdateDestroyAPIView.as_view(), name='area-detail'),
]
