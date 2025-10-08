from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid

from Usuarios.models import Usuario, ActivacionUsuario
from Usuarios.serializers import UsuarioSerializer, CrearUsuarioSerializer, ActivacionSerializer
from Usuarios.decorators import permiso_requerido


# =====================================================
# 🔹 Activar cuenta de usuario o jefe de empresa
# =====================================================
class ActivarCuentaView(APIView):
    """
    Permite activar la cuenta de un usuario (jefe o empleado)
    usando el token que se envía al correo electrónico.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        activacion = get_object_or_404(ActivacionUsuario, token=token)

        # Verificar si ya fue usada o expiró
        if activacion.usado:
            return Response({"detail": "Este enlace ya fue usado."}, status=status.HTTP_400_BAD_REQUEST)
        if activacion.fecha_expiracion < timezone.now():
            return Response({"detail": "El enlace de activación ha expirado."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ActivacionSerializer(data=request.data)
        if serializer.is_valid():
            usuario = activacion.usuario
            usuario.nombres = serializer.validated_data["nombres"]
            usuario.celular = serializer.validated_data["celular"]
            usuario.cargo = serializer.validated_data["cargo"]
            usuario.set_password(serializer.validated_data["password"])
            usuario.is_active = True
            usuario.save()

            # Marcar token como usado
            activacion.usado = True
            activacion.save()

            return Response(
                {"detail": "Cuenta activada correctamente. Ya puedes iniciar sesión."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# 🔹 Crear Empleados (solo AdminEmpresa)
# =====================================================
class CrearEmpleadoView(generics.CreateAPIView):
    """
    Permite al admin de empresa crear empleados.
    - Genera un token de activación por correo.
    """
    serializer_class = CrearUsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    @permiso_requerido("Usuarios.es_admin_empresa")
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        empleado = serializer.save(
            empresa=request.user.empresa,
            is_active=False
        )

        # Crear token de activación
        token = uuid.uuid4()
        ActivacionUsuario.objects.create(
            usuario=empleado,
            token=token,
            fecha_expiracion=timezone.now() + timedelta(days=2)
        )

        # Enviar correo al empleado con el enlace
        activation_link = f"http://127.0.0.1:8000/api/usuarios/activar/{token}/"
        subject = f"Activación de cuenta en {request.user.empresa.nombre}"
        message = (
            f"¡Hola {empleado.nombres or 'nuevo empleado'}!\n\n"
            f"Has sido registrado en la empresa '{request.user.empresa.nombre}'.\n\n"
            f"Activa tu cuenta haciendo clic en el siguiente enlace (válido por 2 días):\n"
            f"{activation_link}\n\n"
            f"Tu usuario es: {empleado.email}\n\n"
            f"Atentamente,\nEquipo de {request.user.empresa.nombre}"
        )

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [empleado.email],
                fail_silently=False,
            )
            print(f"📧 Correo de activación enviado a {empleado.email}")
        except Exception as e:
            print(f"⚠️ Error al enviar correo a {empleado.email}: {e}")

        return Response(
            {"detail": f"Empleado {empleado.email} creado correctamente. Se envió correo de activación."},
            status=status.HTTP_201_CREATED
        )


# =====================================================
# 🔹 Listar Usuarios (por empresa)
# =====================================================
class ListarUsuariosView(generics.ListAPIView):
    """
    Lista todos los empleados activos de la empresa actual.
    """
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        empresa = self.request.user.empresa
        return Usuario.objects.filter(empresa=empresa, estado=True)


# =====================================================
# 🔹 Editar Usuarios (solo AdminEmpresa)
# =====================================================
class UsuarioUpdateView(generics.UpdateAPIView):
    """
    Permite al admin editar la información básica de un usuario.
    """
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Usuario.objects.filter(empresa=self.request.user.empresa)

    @permiso_requerido("Usuarios.es_admin_empresa")
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
# 🔹 Asignar / Remover Permisos (Jefe de área)
# =====================================================
class AsignarJefeAreaView(APIView):
    """
    Permite asignar o remover permisos especiales a usuarios dentro de una empresa.
    """
    permission_classes = [permissions.IsAuthenticated]

    @permiso_requerido("Usuarios.es_admin_empresa")
    def post(self, request, usuario_id):
        usuario = get_object_or_404(Usuario, id=usuario_id, empresa=request.user.empresa)
        permiso_codename = request.data.get("permiso")
        asignar = request.data.get("asignar", True)

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
