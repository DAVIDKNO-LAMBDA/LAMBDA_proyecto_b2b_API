from django.urls import path
from .views import EmpresaList, EmpresaCreate, EmpresaUpdate

urlpatterns = [
    path("empresas/", EmpresaList.as_view(), name="empresasList"),
    path("empresas/create/", EmpresaCreate.as_view(), name="empresaCreate"),
    path("empresas/update/<int:pk>/", EmpresaUpdate.as_view(), name="empresaUpdate"),
]
