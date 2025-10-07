from django.urls import path
from Empresas.views import EmpresaCreateView, EmpresaListView, EmpresaUpdateView, AreaCreateView, AreaUpdateView

urlpatterns = [
    # EMPRESAS
    path("empresas/", EmpresaListView.as_view(), name="listar_empresas"),
    path("empresas/crear/", EmpresaCreateView.as_view(), name="crear_empresa"),
    path("empresas/<int:pk>/", EmpresaUpdateView.as_view(), name="editar_empresa"),

    # ÁREAS
    path("areas/crear/", AreaCreateView.as_view(), name="crear_area"),
    path("areas/<int:pk>/", AreaUpdateView.as_view(), name="editar_area"),
]