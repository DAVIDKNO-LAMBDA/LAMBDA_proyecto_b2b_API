from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission, Group
from Usuarios.models import Usuario, ActivacionUsuario
from Usuarios.serializers import UsuarioSerializer, CrearEmpleadoSerializer, ActivarCuentaSerializer

class ActivarCuentaView(generics.GenericAPIView):
    serializer_class = ActivarCuentaSerializer
    authentication_classes = []
    permission_classes = []
    def post(self, request, token):
        activacion = get_object_or_404(ActivacionUsuario, token=token)
        ser = self.get_serializer(data=request.data, context={"usuario": activacion.usuario, "activacion": activacion})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": "Cuenta activada correctamente. Ya puedes iniciar sesión."}, status=status.HTTP_200_OK)

class CrearEmpleadoView(generics.CreateAPIView):
    serializer_class = CrearEmpleadoSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

class ListarUsuariosView(generics.ListAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    def get_queryset(self):
        empresa = self.request.user.empresa
        activos = self.request.query_params.get("activos", "true").lower()
        qs = Usuario.objects.filter(empresa=empresa)
        if activos in ("true","1","yes","t"):
            qs = qs.filter(is_active=True)
        return qs.order_by("nombres","apellidos")

class UsuarioUpdateView(generics.UpdateAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    lookup_field = "pk"
    def get_queryset(self):
        return Usuario.objects.filter(empresa=self.request.user.empresa)
    def update(self, request, *args, **kwargs):
        usuario = self.get_object()
        data = request.data.copy()
        data.pop("email", None)
        data.pop("empresa", None)
        ser = self.get_serializer(usuario, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": f"Usuario '{usuario.email}' actualizado correctamente."}, status=status.HTTP_200_OK)

class AsignarPermisoUsuarioView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    def post(self, request, usuario_id):
        usuario = get_object_or_404(Usuario, id=usuario_id, empresa=request.user.empresa)
        permiso_codename = request.data.get("permiso")
        asignar = bool(request.data.get("asignar", True))
        if not permiso_codename:
            return Response({"detail": "Debes enviar 'permiso'."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            permiso = Permission.objects.get(codename=permiso_codename)
        except Permission.DoesNotExist:
            return Response({"detail": f"El permiso '{permiso_codename}' no existe."}, status=status.HTTP_400_BAD_REQUEST)
        if asignar:
            usuario.user_permissions.add(permiso)
            accion = "asignado"
        else:
            usuario.user_permissions.remove(permiso)
            accion = "removido"
        return Response({"detail": f"Permiso '{permiso_codename}' {accion} a {usuario.email} correctamente."}, status=status.HTTP_200_OK)

class ToggleGrupoUsuarioView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    def post(self, request, usuario_id):
        usuario = get_object_or_404(Usuario, id=usuario_id, empresa=request.user.empresa)
        grupo_nombre = request.data.get("grupo")
        asignar = bool(request.data.get("asignar", True))
        if not grupo_nombre:
            return Response({"detail": "Debes enviar 'grupo'."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            grupo = Group.objects.get(name=grupo_nombre)
        except Group.DoesNotExist:
            return Response({"detail": f"El grupo '{grupo_nombre}' no existe."}, status=status.HTTP_400_BAD_REQUEST)
        if asignar:
            usuario.groups.add(grupo)
            accion = "asignado"
        else:
            usuario.groups.remove(grupo)
            accion = "removido"
        return Response({"detail": f"Grupo '{grupo_nombre}' {accion} a {usuario.email} correctamente."}, status=status.HTTP_200_OK)
