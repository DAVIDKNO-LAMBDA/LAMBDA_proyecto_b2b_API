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
        """
        Retorna usuarios según permisos jerárquicos:
        - Superusuario: todos los usuarios
        - Admin empresa: usuarios de su empresa
        - Jefe área: usuarios de su área específica
        """
        usuario_actual = self.request.user
        activos = self.request.query_params.get("activos", "true").lower()
        
        # Usar el método de gestión jerárquica del modelo
        qs = usuario_actual.obtener_usuarios_gestionables()
        
        # Filtrar por estado activo si se solicita
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
        """
        Retorna usuarios que el usuario actual puede gestionar
        """
        return self.request.user.obtener_usuarios_gestionables()

    def update(self, request, *args, **kwargs):
        usuario_objetivo = self.get_object()
        
        # Verificar permisos jerárquicos
        if not request.user.puede_gestionar_usuario(usuario_objetivo):
            return Response(
                {"detail": "No tienes permisos para gestionar este usuario."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prevenimos que se modifiquen campos críticos como el email o la empresa
        data = request.data.copy()
        data.pop("email", None)
        data.pop("empresa", None)
        ser = self.get_serializer(usuario_objetivo, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(
            {"detail": f"Usuario '{usuario_objetivo.email}' actualizado correctamente."}, 
            status=status.HTTP_200_OK
        )

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
        # Obtener el usuario objetivo y verificar permisos jerárquicos
        try:
            usuario_objetivo = User.objects.get(id=usuario_id)
        except User.DoesNotExist:
            return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar permisos jerárquicos
        if not request.user.puede_gestionar_usuario(usuario_objetivo):
            return Response(
                {"detail": "No tienes permisos para gestionar este usuario."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        permiso_codename = request.data.get("permiso")
        asignar = bool(request.data.get("asignar", True))
        if not permiso_codename:
            return Response({"detail": "Debes enviar 'permiso'."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            permiso = Permission.objects.get(codename=permiso_codename)
        except Permission.DoesNotExist:
            return Response({"detail": f"El permiso '{permiso_codename}' no existe."}, status=status.HTTP_400_BAD_REQUEST)
        
        if asignar:
            usuario_objetivo.user_permissions.add(permiso)
            accion = "asignado"
        else:
            usuario_objetivo.user_permissions.remove(permiso)
            accion = "removido"
        return Response(
            {"detail": f"Permiso '{permiso_codename}' {accion} a {usuario_objetivo.email} correctamente."}, 
            status=status.HTTP_200_OK
        )

class ToggleGrupoUsuarioView(APIView):
    """
    Asigna o remueve un usuario de un grupo (rol).
    """
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def post(self, request, usuario_id):
        # Obtener el usuario objetivo y verificar permisos jerárquicos
        try:
            usuario_objetivo = User.objects.get(id=usuario_id)
        except User.DoesNotExist:
            return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar permisos jerárquicos
        if not request.user.puede_gestionar_usuario(usuario_objetivo):
            return Response(
                {"detail": "No tienes permisos para gestionar este usuario."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        grupo_nombre = request.data.get("grupo")
        asignar = bool(request.data.get("asignar", True))
        if not grupo_nombre:
            return Response({"detail": "Debes enviar 'grupo'."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            grupo = Group.objects.get(name=grupo_nombre)
        except Group.DoesNotExist:
            return Response({"detail": f"El grupo '{grupo_nombre}' no existe."}, status=status.HTTP_400_BAD_REQUEST)
        
        if asignar:
            usuario_objetivo.groups.add(grupo)
            accion = "asignado"
        else:
            usuario_objetivo.groups.remove(grupo)
            accion = "removido"
        return Response({"detail": f"Grupo '{grupo_nombre}' {accion} a {usuario_objetivo.email} correctamente."}, status=status.HTTP_200_OK)


# =============================================
# 🆕 VISTAS ESPECÍFICAS PARA GESTIÓN JERÁRQUICA POR ÁREA
# =============================================

class UsuariosAreaJefeView(generics.ListAPIView):
    """
    Vista específica para que los jefes de área listen solo usuarios de su área
    """
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        usuario_actual = self.request.user
        
        # Solo jefes de área pueden acceder
        if not (usuario_actual.es_jefe_area or usuario_actual.tiene_rol_jefe_area()) or not usuario_actual.area:
            return User.objects.none()
            
        # Retornar usuarios de su área específica (excluyéndose a sí mismo)
        return User.objects.filter(
            area=usuario_actual.area,
            empresa=usuario_actual.empresa
        ).exclude(id=usuario_actual.id).order_by("nombres", "apellidos")

class AreasAsignablesJefeView(APIView):
    """
    Lista las áreas donde el usuario actual puede asignar personal
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        areas_asignables = request.user.obtener_areas_asignables()
        areas_data = [
            {
                'id': area.id,
                'nombre': area.nombre,
                'descripcion': area.descripcion,
                'tipo': area.tipo,
                'es_area_base': getattr(area, 'es_area_base', False)
            }
            for area in areas_asignables
        ]
        
        return Response({
            'areas_asignables': areas_data,
            'total': areas_asignables.count(),
            'permisos': {
                'es_admin_empresa': request.user.es_admin_empresa(),
                'es_jefe_area': request.user.es_jefe_area or request.user.tiene_rol_jefe_area(),
                'puede_asignar_multiple_areas': request.user.es_admin_empresa()
            }
        })

class AsignarUsuarioAreaView(APIView):
    """
    Asigna un usuario a un área específica con verificación jerárquica
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        usuario_id = request.data.get('usuario_id')
        area_id = request.data.get('area_id')
        
        if not usuario_id or not area_id:
            return Response(
                {"detail": "Se requieren 'usuario_id' y 'area_id'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            usuario_objetivo = User.objects.get(id=usuario_id)
            from Empresas.models import Area
            area_objetivo = Area.objects.get(id=area_id)
        except (User.DoesNotExist, Area.DoesNotExist):
            return Response(
                {"detail": "Usuario o área no encontrados."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar permisos jerárquicos
        if not request.user.puede_gestionar_usuario(usuario_objetivo):
            return Response(
                {"detail": "No tienes permisos para gestionar este usuario."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not request.user.puede_asignar_a_area(area_objetivo):
            return Response(
                {"detail": "No tienes permisos para asignar usuarios a esta área."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Realizar la asignación
        area_anterior = usuario_objetivo.area
        usuario_objetivo.area = area_objetivo
        usuario_objetivo.save()
        
        logger.info(
            f"Usuario {usuario_objetivo.email} asignado de área "
            f"'{area_anterior.nombre if area_anterior else 'Sin área'}' "
            f"a '{area_objetivo.nombre}' por {request.user.email}"
        )
        
        return Response({
            "detail": f"Usuario {usuario_objetivo.email} asignado exitosamente al área {area_objetivo.nombre}.",
            "usuario": {
                "id": usuario_objetivo.id,
                "email": usuario_objetivo.email,
                "nombre_completo": usuario_objetivo.nombre_completo
            },
            "area_anterior": {
                "id": area_anterior.id if area_anterior else None,
                "nombre": area_anterior.nombre if area_anterior else "Sin área"
            },
            "area_nueva": {
                "id": area_objetivo.id,
                "nombre": area_objetivo.nombre
            }
        })

class EstadisticasAreaJefeView(APIView):
    """
    Estadísticas para jefes de área sobre su gestión
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        usuario_actual = request.user
        
        if not (usuario_actual.es_jefe_area or usuario_actual.tiene_rol_jefe_area()) or not usuario_actual.area:
            return Response(
                {"detail": "Solo jefes de área pueden acceder a estas estadísticas."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener usuarios del área
        usuarios_area = User.objects.filter(
            area=usuario_actual.area,
            empresa=usuario_actual.empresa
        ).exclude(id=usuario_actual.id)
        
        # Calcular estadísticas
        total_usuarios = usuarios_area.count()
        usuarios_activos = usuarios_area.filter(is_active=True).count()
        usuarios_pendientes = usuarios_area.filter(estado='pendiente_activacion').count()
        
        return Response({
            'area': {
                'id': usuario_actual.area.id,
                'nombre': usuario_actual.area.nombre,
                'descripcion': usuario_actual.area.descripcion,
                'es_area_base': getattr(usuario_actual.area, 'es_area_base', False)
            },
            'estadisticas_usuarios': {
                'total': total_usuarios,
                'activos': usuarios_activos,
                'pendientes_activacion': usuarios_pendientes,
                'inactivos': total_usuarios - usuarios_activos
            },
            'permisos_jefe': {
                'puede_asignar_roles': usuario_actual.es_admin_empresa() or usuario_actual.es_jefe_area or usuario_actual.tiene_rol_jefe_area(),
                'puede_crear_usuarios': usuario_actual.es_admin_empresa(),
                'puede_asignar_a_otras_areas': usuario_actual.es_admin_empresa()
            }
        })

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
    serializer = ActivarCuentaSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Actualizar contraseña
    usuario.set_password(serializer.validated_data['password'])
    
    # Actualizar datos opcionales
    if serializer.validated_data.get('nombres'):
        usuario.nombres = serializer.validated_data['nombres']
    
    if serializer.validated_data.get('apellidos'):
        usuario.apellidos = serializer.validated_data['apellidos']
    
    if serializer.validated_data.get('celular'):
        usuario.celular = serializer.validated_data['celular']
    
    # Activar usuario
    usuario.estado = 'activo'
    usuario.fecha_activacion = timezone.now()
    usuario.token_activacion = None
    
    # Guardar con update_fields para activar signal
    usuario.save(update_fields=[
        'password', 'nombres', 'apellidos', 'celular', 
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
    elif (user.es_jefe_area or user.tiene_rol_jefe_area()) and user.area:
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
    
    elif user.es_jefe_area() or user.tiene_rol_jefe_area():
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
    if not (user.es_admin_empresa() or user.es_jefe_area or user.tiene_rol_jefe_area()):
        return Response(
            {"error": "No tienes permisos para crear usuarios"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = CrearEmpleadoSerializer(data=request.data)
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
    
    elif user.es_jefe_area or user.tiene_rol_jefe_area():
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
    campos_permitidos = ['nombres', 'apellidos', 'cargo', 'celular']
    
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
    """
    Crea un nuevo empleado (HU05) - VERSIÓN MEJORADA CON ACTIVACIÓN OBLIGATORIA
    Todos los usuarios empresa requieren activación por correo
    """
    user = request.user
    
    # Validar permisos jerárquicos
    if not user.has_perm('Usuarios.puede_crear_usuarios'):
        return Response(
            {"error": "No tienes permiso para crear usuarios"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = CrearEmpleadoSerializer(data=request.data, context={'request': request})
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # 🆕 CREAR EMPLEADO CON ACTIVACIÓN OBLIGATORIA
    empleado = serializer.save()
    
    # Verificar que el empleado requiere activación (usuarios empresa)
    if empleado.requiere_activacion():
        # Crear token de activación automáticamente
        activacion = ActivacionUsuario.objects.create(usuario=empleado)
        
        # 🆕 ENVÍO AUTOMÁTICO DE CORREO DE ACTIVACIÓN
        try:
            enviar_correo_activacion_usuario(empleado, user)
            logger.info(
                f"✅ Empleado {empleado.email} creado exitosamente "
                f"(Empresa: {empleado.empresa.nombre}, Área: {empleado.area.nombre if empleado.area else 'Sin área'}) "
                f"- Correo de activación enviado"
            )
            mensaje_activacion = "Se ha enviado un correo de activación al empleado."
        except Exception as e:
            logger.error(f"❌ Error enviando correo a {empleado.email}: {str(e)}")
            mensaje_activacion = "ADVERTENCIA: No se pudo enviar el correo de activación. Contacta al empleado manualmente."
    else:
        # Usuario Lambda - puede estar activo directamente
        mensaje_activacion = "Usuario Lambda creado y activado automáticamente."
        logger.info(f"✅ Usuario Lambda {empleado.email} creado y activado")
    
    return Response(
        {
            "mensaje": "Empleado creado exitosamente.",
            "activacion": mensaje_activacion,
            "empleado": {
                "id": empleado.id,
                "email": empleado.email,
                "nombre_completo": empleado.nombre_completo,
                "empresa": empleado.empresa.nombre if empleado.empresa else None,
                "area": empleado.area.nombre if empleado.area else None,
                "estado": empleado.estado,
                "requiere_activacion": empleado.requiere_activacion(),
                "puede_autenticarse": empleado.puede_autenticarse()
            },
            "siguiente_paso": (
                "El empleado debe revisar su correo y completar la activación de su cuenta."
                if empleado.requiere_activacion() 
                else "El usuario puede iniciar sesión inmediatamente."
            )
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reenviar_activacion(request):
    """
    Reenvía correo de activación para usuarios pendientes
    Solo usuarios con permisos pueden solicitar reenvío
    """
    email = request.data.get('email')
    if not email:
        return Response(
            {"error": "Se requiere el email del usuario"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        usuario_objetivo = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {"error": "Usuario no encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Verificar permisos jerárquicos
    if not request.user.puede_gestionar_usuario(usuario_objetivo):
        return Response(
            {"error": "No tienes permisos para gestionar este usuario"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Verificar que el usuario requiere activación
    if not usuario_objetivo.requiere_activacion():
        return Response(
            {"error": "Este usuario no requiere activación (usuario Lambda)"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar que está pendiente de activación
    if usuario_objetivo.estado == 'activo':
        return Response(
            {"error": "Esta cuenta ya está activada"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Crear nuevo token de activación (invalidar el anterior)
    ActivacionUsuario.objects.filter(usuario=usuario_objetivo).update(usado=True)
    nueva_activacion = ActivacionUsuario.objects.create(usuario=usuario_objetivo)
    
    # Enviar correo
    try:
        enviar_correo_activacion_usuario(usuario_objetivo, request.user)
        logger.info(f"✅ Correo de activación reenviado a {usuario_objetivo.email}")
        
        return Response(
            {
                "mensaje": f"Correo de activación reenviado exitosamente a {usuario_objetivo.email}",
                "usuario": {
                    "email": usuario_objetivo.email,
                    "nombre_completo": usuario_objetivo.nombre_completo,
                    "estado": usuario_objetivo.estado
                }
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"❌ Error reenviando correo a {usuario_objetivo.email}: {str(e)}")
        return Response(
            {"error": "No se pudo enviar el correo de activación. Inténtalo más tarde."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def activar_cuenta(request, token):
    """
    Activa cuenta de usuario con token (HU04) - FLUJO MEJORADO
    Requiere completar perfil y establecer contraseña
    """
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
            {"error": "El token ha expirado. Solicita un nuevo enlace de activación."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar que el usuario aún requiere activación
    usuario = activacion.usuario
    if usuario.estado == 'activo':
        return Response(
            {"error": "Esta cuenta ya ha sido activada"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar datos del formulario de activación
    serializer = ActivarCuentaSerializer(
        data=request.data,
        context={'usuario': usuario, 'activacion': activacion}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # 🆕 USAR MÉTODO MEJORADO DE ACTIVACIÓN
    password = serializer.validated_data.get('password')
    usuario.activar_cuenta(password=password)
    
    # Actualizar datos adicionales del perfil si se proporcionan
    if serializer.validated_data.get('celular'):
        usuario.celular = serializer.validated_data['celular']
        usuario.save()
    
    # Marcar token como usado
    activacion.usado = True
    activacion.save()
    
    # 🆕 ASIGNACIÓN AUTOMÁTICA DE ROLES SEGÚN JERARQUÍA
    # Si es primer usuario de la empresa -> Admin Empresa
    # Si no, asignar rol base según área
    if usuario.es_primer_usuario:
        grupo = Group.objects.get(name='Admin Empresa')
        usuario.groups.add(grupo)
        logger.info(f"✅ Rol 'Admin Empresa' asignado a {usuario.email} (primer usuario)")
    else:
        # Asignar rol base Empleado por defecto
        grupo = Group.objects.get(name='Empleado')
        usuario.groups.add(grupo)
        logger.info(f"✅ Rol 'Empleado' asignado a {usuario.email}")
    
    # 🆕 LOG DETALLADO DE ACTIVACIÓN
    logger.info(
        f"✅ Cuenta activada exitosamente: {usuario.email} "
        f"(Empresa: {usuario.empresa.nombre if usuario.empresa else 'Lambda'}, "
        f"Área: {usuario.area.nombre if usuario.area else 'Sin área'})"
    )
    
    return Response(
        {
            "mensaje": "¡Cuenta activada exitosamente! Ya puedes iniciar sesión.",
            "usuario": {
                "id": usuario.id,
                "email": usuario.email,
                "nombre_completo": usuario.nombre_completo,
                "empresa": usuario.empresa.nombre if usuario.empresa else None,
                "area": usuario.area.nombre if usuario.area else None,
                "estado": usuario.estado,
                "fecha_activacion": usuario.fecha_activacion,
                "roles": [grupo.name for grupo in usuario.groups.all()]
            },
            "siguiente_paso": "Puedes iniciar sesión con tu email y la contraseña que estableciste."
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
    if (user.es_jefe_area or user.tiene_rol_jefe_area()) and not user.es_admin_empresa():
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
# 🆕 GESTIÓN DE JEFE DE ÁREA
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_jefe_area(request, pk):
    """
    Asigna o quita el rol de jefe de área a un usuario
    Solo Admin Empresa puede hacerlo
    """
    user = request.user
    usuario_target = get_object_or_404(Usuario, pk=pk, deleted_at__isnull=True)
    
    # Solo Admin Empresa puede asignar jefes
    if not user.es_admin_empresa():
        return Response(
            {"error": "Solo Admin Empresa puede asignar jefes de área"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar que sea de la misma empresa
    if usuario_target.empresa != user.empresa:
        return Response(
            {"error": "Solo puedes asignar jefes de área en tu empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Obtener acción (asignar/quitar)
    es_jefe = request.data.get('es_jefe_area', False)
    
    estado_anterior = usuario_target.es_jefe_area
    usuario_target.es_jefe_area = es_jefe
    usuario_target.save(update_fields=['es_jefe_area', 'updated_at'])
    
    # Si se asigna como jefe, agregar al grupo "Jefe de Área"
    if es_jefe:
        grupo_jefe, _ = Group.objects.get_or_create(name='Jefe de Área')
        usuario_target.groups.add(grupo_jefe)
        accion = "asignado como"
    else:
        # Remover del grupo si existe
        try:
            grupo_jefe = Group.objects.get(name='Jefe de Área')
            usuario_target.groups.remove(grupo_jefe)
        except Group.DoesNotExist:
            pass
        accion = "removido como"
    
    logger.info(
        f"✅ Usuario {usuario_target.email} {accion} jefe de área por {user.email}"
    )
    
    return Response(
        {
            "mensaje": f"Usuario {accion} jefe de área exitosamente",
            "usuario": UsuarioConPermisosSerializer(usuario_target).data,
            "cambio": {
                "estado_anterior": estado_anterior,
                "estado_nuevo": es_jefe,
                "accion": accion
            }
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
    elif user.es_jefe_area() or user.tiene_rol_jefe_area():
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