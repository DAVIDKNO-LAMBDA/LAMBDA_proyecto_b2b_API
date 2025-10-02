from django.urls import path
from .views import ActivateAccount, EmpleadosList, EmpleadoCreate, EmpleadoUpdate

urlpatterns = [
    path("auth/activate/", ActivateAccount.as_view(), name="authActivate"),
    path("empleados/", EmpleadosList.as_view(), name="empleadosList"),
    path("empleados/create/", EmpleadoCreate.as_view(), name="empleadosCreate"),
    path("empleados/update/<int:pk>/", EmpleadoUpdate.as_view(), name="empleadosUpdate"),
]
