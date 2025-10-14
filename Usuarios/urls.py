from django.urls import path
from Usuarios.views import (
    ActivarCuentaView, CrearEmpleadoView, ListarUsuariosView, UsuarioUpdateView,
    AsignarPermisoUsuarioView, ToggleGrupoUsuarioView,
)

urlpatterns = [
    path("activar/<uuid:token>/", ActivarCuentaView.as_view(), name="usuarios-activar"),
    path("crear/", CrearEmpleadoView.as_view(), name="usuarios-crear"),
    path("", ListarUsuariosView.as_view(), name="usuarios-listar"),
    path("<int:pk>/", UsuarioUpdateView.as_view(), name="usuarios-editar"),
    path("<int:usuario_id>/permisos/", AsignarPermisoUsuarioView.as_view(), name="usuarios-permisos"),
    path("<int:usuario_id>/grupos/", ToggleGrupoUsuarioView.as_view(), name="usuarios-grupos"),
]
