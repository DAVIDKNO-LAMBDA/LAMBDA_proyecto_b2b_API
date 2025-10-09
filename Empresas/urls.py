# Empresas/urls.py
from django.urls import path
from Empresas.views import (
    EmpresaCreateView,
    EmpresaListView,
    EmpresaUpdateView,
    AreaCreateView,
    AreaUpdateView,
)

urlpatterns = [
    # EMPRESAS (prefijo efectivo: /api/empresas/)
    path("", EmpresaListView.as_view(), name="empresas-listar"),
    path("crear/", EmpresaCreateView.as_view(), name="empresas-crear"),
    path("<int:pk>/", EmpresaUpdateView.as_view(), name="empresas-editar"),

    # ÁREAS (prefijo efectivo: /api/empresas/areas/)
    path("areas/crear/", AreaCreateView.as_view(), name="areas-crear"),
    path("areas/<int:pk>/", AreaUpdateView.as_view(), name="areas-editar"),
]
