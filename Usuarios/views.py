# --- BLOQUE DE IMPORTS CORREGIDO Y ORGANIZADO ---

# Imports de Django
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils import timezone

# Imports de Django REST Framework
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny

# Imports locales de la app
from .models import ActivacionUsuario, Usuario
from .serializers import (
    UsuarioSerializer,
    CrearEmpleadoSerializer,
    ActivarCuentaSerializer,
    PermisoSerializer,
    GrupoSerializer,
    AsignarAreaSerializer,
    AsignarPermisosEspecialesSerializer,
    UsuarioConPermisosSerializer
)
from Base.correos import enviar_correo_activacion_usuario
import logging

# Obtenemos el modelo de Usuario activo
User = get_user_model()

logger = logging.getLogger(__name__)


# --- VISTAS CORREGIDAS Y ORGANIZADAS ---

class CrearEmpleadoView(generics.CreateAPIView):
    """
    Crea un nuevo empleado (usuario) dentro de la empresa del administrador que hace la petición.
    El usuario se crea como inactivo y se le envía un correo para activar su cuenta.
    """
    serializer_class = CrearEmpleadoSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    # El queryset es necesario para la comprobación de permisos de DjangoModelPermissions
    queryset = User.objects.all()

class ListarUsuariosView(generics.ListAPIView):
    """
    Lista los usuarios de la empresa del usuario autenticado.
    Permite filtrar por usuarios activos con el query param `?activos=true/false`.
    """
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        empresa = self.request.user.empresa
        activos = self.request.query_params.get("activos", "true").lower()
        qs = User.objects.filter(empresa=empresa)
        if activos in ("true", "1", "yes", "t"):
            qs = qs.filter(is_active=True)
        return qs.order_by("nombres", "apellidos")

class UsuarioUpdateView(generics.UpdateAPIView):
    """
    Actualiza parcialmente los datos de un usuario específico de la empresa.
    """
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    lookup_field = "pk"

    def get_queryset(self):
        return User.objects.filter(empresa=self.request.user.empresa)

    def update(self, request, *args, **kwargs):
        usuario = self.get_object()
        # Prevenimos que se modifiquen campos críticos como el email o la empresa
        data = request.data.copy()
        data.pop("email", None)
        data.pop("empresa", None)
        ser = self.get_serializer(usuario, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": f"Usuario '{usuario.email}' actualizado correctamente."}, status=status.HTTP_200_OK)

class ActivarCuentaView(generics.GenericAPIView):
    """
    Activa la cuenta de un usuario a través de un token único.
    Esta vista no requiere autenticación.
    """
    serializer_class = ActivarCuentaSerializer
    authentication_classes = []
    permission_classes = []

    def post(self, request, token):
        activacion = get_object_or_404(ActivacionUsuario, token=token)
        ser = self.get_serializer(data=request.data, context={"usuario": activacion.usuario, "activacion": activacion})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": "Cuenta activada correctamente. Ya puedes iniciar sesión."}, status=status.HTTP_200_OK)

class UsuarioActualView(APIView):
    """
    Devuelve los datos del usuario que está actualmente autenticado.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)

class AsignarPermisoUsuarioView(APIView):
    """
    Asigna o remueve un permiso específico a un usuario.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def post(self, request, usuario_id):
        usuario = get_object_or_404(User, id=usuario_id, empresa=request.user.empresa)
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
    """
    Asigna o remueve un usuario de un grupo (rol).
    """
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def post(self, request, usuario_id):
        usuario = get_object_or_404(User, id=usuario_id, empresa=request.user.empresa)
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


# =============================================
# ACTIVACIÓN DE CUENTA
# =============================================

@api_view(['POST'])
@permission_classes([AllowAny])
def activar_usuario(request, token):
    """
    Activa la cuenta de un usuario usando el token enviado por correo
    """
    try:
        usuario = Usuario.objects.get(
            token_activacion=token, 
            estado='pendiente_activacion'
        )
    except Usuario.DoesNotExist:
        return Response(
            {"error": "Token inválido o usuario ya activado"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Validar datos del formulario de activación
    serializer = ActivarUsuarioSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Actualizar contraseña
    usuario.set_password(serializer.validated_data['password'])
    
    # Actualizar datos opcionales
    if serializer.validated_data.get('first_name'):
        usuario.first_name = serializer.validated_data['first_name']
    
    if serializer.validated_data.get('last_name'):
        usuario.last_name = serializer.validated_data['last_name']
    
    if serializer.validated_data.get('celular'):
        usuario.celular = serializer.validated_data['celular']
    
    # Activar usuario
    usuario.estado = 'activo'
    usuario.fecha_activacion = timezone.now()
    usuario.token_activacion = None
    
    # Guardar con update_fields para activar signal
    usuario.save(update_fields=[
        'password', 'first_name', 'last_name', 'celular', 
        'estado', 'fecha_activacion', 'token_activacion'
    ])
    
    return Response({
        "mensaje": "Cuenta activada exitosamente",
        "usuario": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre_completo": usuario.get_full_name(),
            "empresa": usuario.empresa.nombre if usuario.empresa else None,
            "area": usuario.area.nombre if usuario.area else None,
            "roles": [g.name for g in usuario.groups.all()],
        }
    }, status=status.HTTP_200_OK)


# =============================================
# CRUD DE USUARIOS
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_usuarios(request):
    """
    Lista usuarios según permisos del usuario autenticado
    """
    user = request.user
    
    # Usuarios de Lambda ven todos los usuarios de Lambda
    if user.es_usuario_lambda():
        usuarios = Usuario.objects.filter(empresa__isnull=True)
    
    # Admin de Empresa ve usuarios de su empresa
    elif user.es_admin_empresa():
        usuarios = Usuario.objects.filter(empresa=user.empresa)
    
    # Jefe de Área ve usuarios de su área
    elif user.es_jefe_area() and user.area:
        usuarios = Usuario.objects.filter(empresa=user.empresa, area=user.area)
    
    # Otros solo ven su perfil
    else:
        usuarios = Usuario.objects.filter(id=user.id)
    
    serializer = UsuarioSerializer(usuarios, many=True)
    return Response({
        "count": usuarios.count(),
        "results": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_usuario(request, pk):
    """
    Obtiene detalle de un usuario específico
    """
    user = request.user
    usuario = get_object_or_404(Usuario, pk=pk)
    
    # Validar permisos de lectura
    if user.es_usuario_lambda():
        if usuario.empresa:  # Lambda solo ve usuarios Lambda
            return Response(
                {"error": "No tienes permisos para ver este usuario"},
                status=status.HTTP_403_FORBIDDEN
            )
    
    elif user.es_admin_empresa():
        if usuario.empresa != user.empresa:
            return Response(
                {"error": "Solo puedes ver usuarios de tu empresa"},
                status=status.HTTP_403_FORBIDDEN
            )
    
    elif user.es_jefe_area():
        if usuario.empresa != user.empresa or usuario.area != user.area:
            return Response(
                {"error": "Solo puedes ver usuarios de tu área"},
                status=status.HTTP_403_FORBIDDEN
            )
    
    else:
        if usuario.id != user.id:
            return Response(
                {"error": "Solo puedes ver tu propio perfil"},
                status=status.HTTP_403_FORBIDDEN
            )
    
    serializer = UsuarioSerializer(usuario)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_usuario(request):
    """
    Crea un nuevo usuario (empleado)
    Solo Admin Empresa y Jefe de Área pueden crear usuarios
    """
    user = request.user
    
    # Validar permisos
    if not (user.es_admin_empresa() or user.es_jefe_area()):
        return Response(
            {"error": "No tienes permisos para crear usuarios"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = UsuarioCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Obtener el área del request
    area = serializer.validated_data.get('area')
    
    # Validar según el rol del creador
    if user.es_admin_empresa():
        # Admin Empresa puede asignar a cualquier área de su empresa
        if area and area.empresa != user.empresa:
            return Response(
                {"error": "Solo puedes asignar áreas de tu empresa"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear usuario
        nuevo_usuario = serializer.save(
            empresa=user.empresa,
            creado_por=user
        )
    
    elif user.es_jefe_area():
        # Jefe de Área debe especificar área
        if not area:
            return Response(
                {"error": "Debes especificar un área"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar que sea de su empresa
        if area.empresa != user.empresa:
            return Response(
                {"error": "Solo puedes asignar áreas de tu empresa"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear usuario
        nuevo_usuario = serializer.save(
            empresa=user.empresa,
            creado_por=user
        )
    
    # Guardar referencia del creador para el signal
    nuevo_usuario._creador = user
    nuevo_usuario.save()
    
    logger.info(f"✅ Usuario {nuevo_usuario.email} creado por {user.email}")
    
    return Response({
        "mensaje": "Usuario creado exitosamente. Se ha enviado correo de activación.",
        "usuario": UsuarioSerializer(nuevo_usuario).data
    }, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def actualizar_usuario(request, pk):
    """
    Actualiza datos básicos de un usuario
    """
    user = request.user
    usuario = get_object_or_404(Usuario, pk=pk)
    
    # Solo Admin Empresa o el propio usuario pueden actualizar
    if not (user.es_admin_empresa() or user.id == usuario.id):
        return Response(
            {"error": "No tienes permisos para actualizar este usuario"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Admin solo puede actualizar usuarios de su empresa
    if user.es_admin_empresa() and usuario.empresa != user.empresa:
        return Response(
            {"error": "Solo puedes actualizar usuarios de tu empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Campos actualizables
    campos_permitidos = ['first_name', 'last_name', 'cargo', 'celular']
    
    for campo in campos_permitidos:
        if campo in request.data:
            setattr(usuario, campo, request.data[campo])
    
    usuario.save()
    
    logger.info(f"✅ Usuario {usuario.email} actualizado por {user.email}")
    
    return Response({
        "mensaje": "Usuario actualizado exitosamente",
        "usuario": UsuarioSerializer(usuario).data
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_usuario(request, pk):
    """
    Desactiva un usuario (no lo elimina físicamente)
    Solo Admin Empresa puede hacerlo
    """
    user = request.user
    
    if not user.es_admin_empresa():
        return Response(
            {"error": "Solo Admin Empresa puede eliminar usuarios"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    usuario = get_object_or_404(Usuario, pk=pk)
    
    # Validar que sea de la misma empresa
    if usuario.empresa != user.empresa:
        return Response(
            {"error": "Solo puedes eliminar usuarios de tu empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # No puede eliminarse a sí mismo
    if usuario.id == user.id:
        return Response(
            {"error": "No puedes eliminar tu propio usuario"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Desactivar usuario
    usuario.is_active = False
    usuario.deleted_at = timezone.now()
    usuario.save()
    
    logger.info(f"✅ Usuario {usuario.email} desactivado por {user.email}")
    
    return Response(
        {"mensaje": "Usuario desactivado exitosamente"},
        status=status.HTTP_200_OK
    )


# =============================================
# GESTIÓN DE USUARIOS (YA EXISTENTES - MANTENER)
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_empleados(request):
    """Lista empleados de la empresa del usuario autenticado"""
    user = request.user
    
    if not hasattr(user, 'empresa') or user.empresa is None:
        return Response(
            {"error": "Solo usuarios de empresa pueden listar empleados"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    empleados = Usuario.objects.filter(
        empresa=user.empresa,
        deleted_at__isnull=True
    ).select_related('empresa', 'area')
    
    serializer = UsuarioSerializer(empleados, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_empleado(request):
    """Crea un nuevo empleado (HU05)"""
    user = request.user
    
    # Validar permisos
    if not user.has_perm('Usuarios.puede_crear_usuarios'):
        return Response(
            {"error": "No tienes permiso para crear usuarios"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = CrearEmpleadoSerializer(data=request.data, context={'request': request})
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    empleado = serializer.save()
    
    # Crear token de activación
    activacion = ActivacionUsuario.objects.create(usuario=empleado)
    
    # Enviar correo
    try:
        enviar_correo_activacion_usuario(empleado, user)
        logger.info(f"✅ Empleado {empleado.email} creado y correo enviado")
    except Exception as e:
        logger.error(f"❌ Error enviando correo a {empleado.email}: {str(e)}")
    
    return Response(
        {
            "mensaje": "Empleado creado exitosamente. Se ha enviado correo de activación.",
            "empleado": UsuarioSerializer(empleado).data
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
def activar_cuenta(request, token):
    """Activa cuenta de usuario con token (HU04)"""
    try:
        activacion = ActivacionUsuario.objects.select_related('usuario').get(
            token=token,
            usado=False
        )
    except ActivacionUsuario.DoesNotExist:
        return Response(
            {"error": "Token inválido o ya usado"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if activacion.expirado():
        return Response(
            {"error": "El token ha expirado"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ActivarCuentaSerializer(
        data=request.data,
        context={'usuario': activacion.usuario, 'activacion': activacion}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    usuario = serializer.save()
    
    # Asignar rol por defecto si es primer usuario
    if usuario.es_primer_usuario:
        grupo = Group.objects.get(name='Admin Empresa')
        usuario.groups.add(grupo)
        logger.info(f"✅ Rol 'Admin Empresa' asignado a {usuario.email}")
    else:
        grupo = Group.objects.get(name='Empleado')
        usuario.groups.add(grupo)
        logger.info(f"✅ Rol 'Empleado' asignado a {usuario.email}")
    
    return Response(
        {
            "mensaje": "Cuenta activada exitosamente",
            "usuario": UsuarioSerializer(usuario).data
        },
        status=status.HTTP_200_OK
    )


# =============================================
# 🆕 GESTIÓN DE ÁREAS (HU08)
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_area(request, pk):
    """
    Asigna o cambia el área de un usuario (HU08)
    Solo Admin Empresa o Jefe de Área pueden hacerlo
    """
    user = request.user
    usuario_target = get_object_or_404(Usuario, pk=pk, deleted_at__isnull=True)
    
    # Validar permisos
    if not user.has_perm('Usuarios.puede_asignar_areas'):
        return Response(
            {"error": "No tienes permiso para asignar áreas"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar que sea de la misma empresa
    if usuario_target.empresa != user.empresa:
        return Response(
            {"error": "Solo puedes asignar áreas a usuarios de tu empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Si es Jefe de Área, solo puede asignar a SU área
    if user.es_jefe_area() and not user.es_admin_empresa():
        area_id = request.data.get('area_id')
        if area_id and int(area_id) != user.area_id:
            return Response(
                {"error": "Jefe de Área solo puede asignar usuarios a su propia área"},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Validar datos
    serializer = AsignarAreaSerializer(
        data=request.data,
        context={'usuario': usuario_target}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Asignar área
    area = serializer.validated_data.get('area_id')
    area_anterior = usuario_target.area
    
    usuario_target.area = area
    usuario_target.save(update_fields=['area', 'updated_at'])
    
    logger.info(
        f"✅ Área cambiada para {usuario_target.email}: "
        f"{area_anterior.nombre if area_anterior else 'Sin área'} → "
        f"{area.nombre if area else 'Sin área'} "
        f"por {user.email}"
    )
    
    return Response(
        {
            "mensaje": "Área asignada exitosamente",
            "usuario": UsuarioSerializer(usuario_target).data,
            "cambio": {
                "area_anterior": area_anterior.nombre if area_anterior else None,
                "area_nueva": area.nombre if area else None
            }
        },
        status=status.HTTP_200_OK
    )


# =============================================
# 🆕 GESTIÓN DE PERMISOS ESPECIALES (HU09)
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_permisos_especiales(request, pk):
    """
    Asigna permisos especiales a un usuario (HU09)
    Ejemplo: marcar como validador_finanzas, validador_abastecimiento
    Solo Admin Empresa puede hacerlo
    """
    user = request.user
    usuario_target = get_object_or_404(Usuario, pk=pk, deleted_at__isnull=True)
    
    # Solo Admin Empresa
    if not user.es_admin_empresa():
        return Response(
            {"error": "Solo Admin Empresa puede asignar permisos especiales"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar que sea de la misma empresa
    if usuario_target.empresa != user.empresa:
        return Response(
            {"error": "Solo puedes asignar permisos a usuarios de tu empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar datos
    serializer = AsignarPermisosEspecialesSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Construir diccionario de permisos personalizados
    permisos_anteriores = usuario_target.permisos_personalizados.copy()
    
    # Actualizar permisos
    usuario_target.permisos_personalizados.update(serializer.validated_data)
    usuario_target.save(update_fields=['permisos_personalizados', 'updated_at'])
    
    logger.info(
        f"✅ Permisos especiales actualizados para {usuario_target.email} por {user.email}: "
        f"{serializer.validated_data}"
    )
    
    return Response(
        {
            "mensaje": "Permisos especiales asignados exitosamente",
            "usuario": UsuarioConPermisosSerializer(usuario_target).data,
            "cambios": {
                "permisos_anteriores": permisos_anteriores,
                "permisos_nuevos": usuario_target.permisos_personalizados
            }
        },
        status=status.HTTP_200_OK
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remover_permisos_especiales(request, pk):
    """
    Remueve TODOS los permisos especiales de un usuario
    Solo Admin Empresa puede hacerlo
    """
    user = request.user
    usuario_target = get_object_or_404(Usuario, pk=pk, deleted_at__isnull=True)
    
    # Solo Admin Empresa
    if not user.es_admin_empresa():
        return Response(
            {"error": "Solo Admin Empresa puede remover permisos especiales"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar que sea de la misma empresa
    if usuario_target.empresa != user.empresa:
        return Response(
            {"error": "Solo puedes gestionar permisos de usuarios de tu empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    permisos_anteriores = usuario_target.permisos_personalizados.copy()
    
    # Limpiar permisos especiales
    usuario_target.permisos_personalizados = {}
    usuario_target.save(update_fields=['permisos_personalizados', 'updated_at'])
    
    logger.info(
        f"✅ Permisos especiales removidos de {usuario_target.email} por {user.email}"
    )
    
    return Response(
        {
            "mensaje": "Permisos especiales removidos exitosamente",
            "usuario": UsuarioSerializer(usuario_target).data,
            "permisos_removidos": permisos_anteriores
        },
        status=status.HTTP_200_OK
    )


# =============================================
# 🆕 CONSULTA DE PERMISOS Y GRUPOS
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_permisos_disponibles(request):
    """
    Lista todos los permisos disponibles en el sistema
    Solo Admin Empresa puede verlos
    """
    user = request.user
    
    if not user.es_admin_empresa():
        return Response(
            {"error": "Solo Admin Empresa puede ver permisos disponibles"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Filtrar permisos relevantes para empresas
    permisos = Permission.objects.filter(
        content_type__app_label__in=['Usuarios', 'Empresas']
    ).select_related('content_type').order_by('content_type__app_label', 'codename')
    
    serializer = PermisoSerializer(permisos, many=True)
    
    return Response(
        {
            "count": permisos.count(),
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_grupos_disponibles(request):
    """
    Lista todos los grupos/roles disponibles
    Solo Admin Empresa puede verlos
    """
    user = request.user
    
    if not user.es_admin_empresa():
        return Response(
            {"error": "Solo Admin Empresa puede ver grupos disponibles"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Excluir "Admin Lambda" para empresas
    grupos = Group.objects.exclude(name='Admin Lambda').prefetch_related('permissions')
    
    serializer = GrupoSerializer(grupos, many=True)
    
    return Response(
        {
            "count": grupos.count(),
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ver_permisos_usuario(request, pk):
    """
    Ver todos los permisos de un usuario específico
    Incluye permisos de grupos + permisos individuales + permisos especiales
    """
    user = request.user
    usuario = get_object_or_404(Usuario, pk=pk, deleted_at__isnull=True)
    
    # Validar permisos
    # Admin Empresa puede ver todos de su empresa
    # Jefes de área pueden ver los de su área
    # Otros solo pueden ver su propio perfil
    
    if user.es_admin_empresa():
        if usuario.empresa != user.empresa:
            return Response(
                {"error": "Solo puedes ver permisos de usuarios de tu empresa"},
                status=status.HTTP_403_FORBIDDEN
            )
    elif user.es_jefe_area():
        if usuario.area != user.area:
            return Response(
                {"error": "Solo puedes ver permisos de usuarios de tu área"},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        if usuario.id != user.id:
            return Response(
                {"error": "Solo puedes ver tus propios permisos"},
                status=status.HTTP_403_FORBIDDEN
            )
    
    serializer = UsuarioConPermisosSerializer(usuario)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_rol(request, pk):
    """
    Asigna un rol (grupo) a un usuario
    Solo Admin Empresa puede hacerlo
    """
    user = request.user
    usuario_target = get_object_or_404(Usuario, pk=pk, deleted_at__isnull=True)
    
    # Solo Admin Empresa
    if not user.has_perm('Usuarios.puede_asignar_roles'):
        return Response(
            {"error": "No tienes permiso para asignar roles"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar que sea de la misma empresa
    if usuario_target.empresa != user.empresa:
        return Response(
            {"error": "Solo puedes asignar roles a usuarios de tu empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Obtener rol del request
    nombre_rol = request.data.get('rol')
    if not nombre_rol:
        return Response(
            {"error": "Debe especificar el campo 'rol'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar que el rol exista y no sea "Admin Lambda"
    roles_permitidos = ['Admin Empresa', 'Jefe de Área', 'Empleado']
    if nombre_rol not in roles_permitidos:
        return Response(
            {
                "error": f"Rol inválido. Roles permitidos: {', '.join(roles_permitidos)}"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        grupo = Group.objects.get(name=nombre_rol)
    except Group.DoesNotExist:
        return Response(
            {"error": f"El grupo '{nombre_rol}' no existe. Ejecuta: python manage.py bootstrap_roles"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Limpiar roles anteriores y asignar nuevo
    roles_anteriores = list(usuario_target.groups.values_list('name', flat=True))
    usuario_target.groups.clear()
    usuario_target.groups.add(grupo)
    
    logger.info(
        f"✅ Rol '{nombre_rol}' asignado a {usuario_target.email} por {user.email}. "
        f"Roles anteriores: {roles_anteriores}"
    )
    
    return Response(
        {
            "mensaje": f"Rol '{nombre_rol}' asignado exitosamente",
            "usuario": UsuarioConPermisosSerializer(usuario_target).data,
            "cambio": {
                "roles_anteriores": roles_anteriores,
                "rol_nuevo": nombre_rol
            }
        },
        status=status.HTTP_200_OK
    )


# =============================================
# 🆕 VALIDACIÓN DE VALIDADORES (PARA HU10)
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verificar_validadores_empresa(request):
    """
    Verifica si la empresa tiene al menos un validador financiero
    y uno de abastecimiento (requisito para HU10)
    """
    user = request.user
    
    if not hasattr(user, 'empresa') or user.empresa is None:
        return Response(
            {"error": "Solo usuarios de empresa pueden consultar validadores"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Buscar validadores activos
    validadores_finanzas = Usuario.objects.filter(
        empresa=user.empresa,
        is_active=True,
        deleted_at__isnull=True,
        permisos_personalizados__validador_finanzas=True
    ).values('id', 'nombres', 'apellidos', 'email', 'area__nombre')
    
    validadores_abastecimiento = Usuario.objects.filter(
        empresa=user.empresa,
        is_active=True,
        deleted_at__isnull=True,
        permisos_personalizados__validador_abastecimiento=True
    ).values('id', 'nombres', 'apellidos', 'email', 'area__nombre')
    
    tiene_validadores = (
        validadores_finanzas.exists() and 
        validadores_abastecimiento.exists()
    )
    
    return Response(
        {
            "empresa": user.empresa.nombre,
            "tiene_validadores_completos": tiene_validadores,
            "validadores_finanzas": {
                "cantidad": validadores_finanzas.count(),
                "usuarios": list(validadores_finanzas)
            },
            "validadores_abastecimiento": {
                "cantidad": validadores_abastecimiento.count(),
                "usuarios": list(validadores_abastecimiento)
            },
            "mensaje": (
                "✅ La empresa puede crear solicitudes" if tiene_validadores 
                else "❌ Faltan validadores. No se pueden crear solicitudes aún."
            )
        },
        status=status.HTTP_200_OK
    )