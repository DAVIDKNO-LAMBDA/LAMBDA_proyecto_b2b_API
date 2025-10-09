# Usuarios/urls.py
from django.urls import path
from Usuarios.views import (
    ActivarCuentaView,
    CrearEmpleadoView,
    ListarUsuariosView,
    UsuarioUpdateView,
    ToggleAdminEmpresaView,
    AsignarPermisoUsuarioView,
)

urlpatterns = [
    # Público (con token)
    path("activar/<uuid:token>/", ActivarCuentaView.as_view(), name="usuarios-activar"),

    # Empleados
    path("crear/", CrearEmpleadoView.as_view(), name="usuarios-crear"),
    path("", ListarUsuariosView.as_view(), name="usuarios-listar"),
    path("<int:pk>/", UsuarioUpdateView.as_view(), name="usuarios-editar"),

    # Admin Empresa: promover/remover admin
    path("<int:usuario_id>/toggle-admin/", ToggleAdminEmpresaView.as_view(), name="usuarios-toggle-admin"),

    # Admin Empresa: asignar/remover permisos por codename (opcional)
    path("<int:usuario_id>/permisos/", AsignarPermisoUsuarioView.as_view(), name="usuarios-permisos"),
]
