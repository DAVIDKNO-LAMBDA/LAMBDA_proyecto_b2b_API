from django.urls import path
from Usuarios.views import (
    ActivarCuentaView, CrearEmpleadoView, ListarUsuariosView,
    UsuarioUpdateView, AsignarJefeAreaView
)

urlpatterns = [
    path("usuarios/activar/<uuid:token>/", ActivarCuentaView.as_view(), name="activar_cuenta"),
    path("usuarios/crear/", CrearEmpleadoView.as_view(), name="crear_empleado"),
    path("usuarios/", ListarUsuariosView.as_view(), name="listar_usuarios"),
    path("usuarios/<int:pk>/", UsuarioUpdateView.as_view(), name="editar_usuario"),
    path("usuarios/<int:usuario_id>/asignar-jefe/", AsignarJefeAreaView.as_view(), name="asignar_jefe_area"),
]
