from django.urls import path
from .views import EmpresaListCreate, EmpresaUpdate, AreaListCreate

urlpatterns = [
    path("empresas/", EmpresaListCreate.as_view(), name="empresas-list-create"),
    path("empresas/<int:pk>/update/", EmpresaUpdate.as_view(), name="empresas-update"),
    path("empresas/<int:empresa_id>/areas/", AreaListCreate.as_view(), name="areas-list-create"),
]
