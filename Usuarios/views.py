from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission

from Usuarios.models import Usuario, ActivacionUsuario
from Usuarios.serializers import (
    UsuarioSerializer,
    CrearEmpleadoSerializer,
    ActivarCuentaSerializer,
)
from Usuarios.permissions import IsAdminEmpresa
from Usuarios.decorators import MethodPermissionsMixin, require_admin_empresa


# =====================================================
# Activar cuenta (admin empresa o empleado)
# =====================================================
class ActivarCuentaView(generics.GenericAPIView):
    """
    Activa una cuenta a partir del token enviado por correo.
    """
    serializer_class = ActivarCuentaSerializer
    authentication_classes = []   # público (con token)
    permission_classes = []       # público (con token)

    def post(self, request, token):
        activacion = get_object_or_404(ActivacionUsuario, token=token)

        ser = self.get_serializer(
            data=request.data,
            context={"usuario": activacion.usuario, "activacion": activacion}
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(
            {"detail": "Cuenta activada correctamente. Ya puedes iniciar sesión."},
            status=status.HTTP_200_OK
        )


# =====================================================
# 🔹 Crear Empleados (Admin Empresa o Jefe de Área)
# =====================================================
class CrearEmpleadoView(generics.CreateAPIView):
    """
    Permite crear empleados:
      - Admin Empresa: en cualquier área de su empresa (puede marcar es_admin_empresa).
      - Jefe de Área: solo en su área (no puede marcar es_admin_empresa).
    Las señales envían el correo de activación automáticamente.
    """
    serializer_class = CrearEmpleadoSerializer
    permission_classes = [permissions.IsAuthenticated]
    # La validación fina (admin vs jefe) se hace en el serializer.


# =====================================================
# 🔹 Listar Usuarios (por empresa, paginado)
# =====================================================
class ListarUsuariosView(generics.ListAPIView):
    """
    Lista usuarios de la empresa del usuario autenticado.
    Filtros opcionales:
      - ?activos=true/false  (por defecto true)
    """
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        empresa = self.request.user.empresa
        activos = self.request.query_params.get("activos", "true").lower()
        qs = Usuario.objects.filter(empresa=empresa)
        if activos in ("true", "1", "yes", "t"):
            qs = qs.filter(is_active=True)
        return qs.order_by("nombres", "apellidos")


# =====================================================
# 🔹 Editar Usuario (solo Admin Empresa, dentro de su empresa)
# =====================================================
class UsuarioUpdateView(generics.UpdateAPIView):
    """
    Permite al Admin Empresa editar datos básicos de un usuario de SU empresa.
    No permite cambiar email ni empresa por API.
    """
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminEmpresa]
    lookup_field = "pk"

    def get_queryset(self):
        return Usuario.objects.filter(empresa=self.request.user.empresa)

    def update(self, request, *args, **kwargs):
        usuario = self.get_object()
        data = request.data.copy()
        data.pop("email", None)
        data.pop("empresa", None)

        serializer = self.get_serializer(usuario, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": f"Usuario '{usuario.email}' actualizado correctamente."},
            status=status.HTTP_200_OK
        )


# =====================================================
# 🔹 Promover / remover Admin de Empresa
# =====================================================
class ToggleAdminEmpresaView(MethodPermissionsMixin, generics.GenericAPIView):
    """
    Admin Empresa puede promover o remover a otro usuario como Admin Empresa
    dentro de su misma empresa.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminEmpresa]

    @require_admin_empresa  # decorador compatible: DRF seguirá usando permission_classes
    def post(self, request, usuario_id):
        admin = request.user
        usuario = get_object_or_404(Usuario, pk=usuario_id, empresa=admin.empresa)
        nuevo_estado = bool(request.data.get("es_admin_empresa"))
        usuario.es_admin_empresa = nuevo_estado
        usuario.save(update_fields=["es_admin_empresa"])
        accion = "promovido" if nuevo_estado else "removido"
        return Response(
            {"detail": f"Usuario {accion} como admin de empresa."},
            status=status.HTTP_200_OK
        )


# =====================================================
# 🔹 Asignar / remover permisos por codename (opcional)
#    Útil si quieres usar codenames nativos:
#    - valida_financiero
#    - valida_abastecimiento
#    - valida_logistica
#    - valida_venta
# =====================================================
class AsignarPermisoUsuarioView(MethodPermissionsMixin, APIView):
    """
    Admin Empresa asigna/remueve permisos nativos (codenames) a usuarios de su empresa.
    Body:
      {
        "permiso": "valida_financiero",
        "asignar": true
      }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminEmpresa]

    @require_admin_empresa
    def post(self, request, usuario_id):
        usuario = get_object_or_404(Usuario, id=usuario_id, empresa=request.user.empresa)
        permiso_codename = request.data.get("permiso")
        asignar = bool(request.data.get("asignar", True))

        if not permiso_codename:
            return Response({"detail": "Debes enviar 'permiso'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            permiso = Permission.objects.get(codename=permiso_codename)
        except Permission.DoesNotExist:
            return Response(
                {"detail": f"El permiso '{permiso_codename}' no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if asignar:
            usuario.user_permissions.add(permiso)
            accion = "asignado"
        else:
            usuario.user_permissions.remove(permiso)
            accion = "removido"

        return Response(
            {"detail": f"Permiso '{permiso_codename}' {accion} a {usuario.email} correctamente."},
            status=status.HTTP_200_OK
        )
