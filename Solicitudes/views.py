from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Solicitud, ItemSolicitud, HistorialValidacion
from .serializers import (
    SolicitudSerializer,
    CrearSolicitudSerializer,
    ValidarAbastecimientoSerializer,
    ValidarFinanzasSerializer,
    HistorialValidacionSerializer
)
import logging

logger = logging.getLogger(__name__)


# =============================================
# HU10 - CREAR SOLICITUD INTERNA
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_solicitud(request):
    """
    Crea una solicitud interna de productos (HU10)
    Valida que existan validadores antes de crear
    """
    user = request.user
    
    # Validar que sea usuario de empresa
    if not hasattr(user, 'empresa') or user.empresa is None:
        return Response(
            {"error": "Solo usuarios de empresa pueden crear solicitudes"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar permisos
    if not user.puede_crear_solicitudes():
        return Response(
            {"error": "No tienes permiso para crear solicitudes"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar y crear solicitud
    serializer = CrearSolicitudSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            solicitud = serializer.save()
            logger.info(
                f"✅ Solicitud {solicitud.numero_solicitud} creada por {user.email}"
            )
            
            return Response(
                {
                    "mensaje": "Solicitud creada exitosamente",
                    "solicitud": SolicitudSerializer(solicitud).data
                },
                status=status.HTTP_201_CREATED
            )
    
    except Exception as e:
        logger.error(f"❌ Error creando solicitud: {str(e)}")
        return Response(
            {"error": f"Error creando solicitud: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# HU11 - LISTAR SOLICITUDES
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_solicitudes(request):
    """
    Lista solicitudes según el rol del usuario (HU11)
    - Admin Empresa: Todas las de su empresa
    - Jefe de Área: Las de su área
    - Empleado: Solo las propias
    """
    user = request.user
    
    if not hasattr(user, 'empresa') or user.empresa is None:
        return Response(
            {"error": "Solo usuarios de empresa pueden listar solicitudes"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Filtrar según permisos
    if user.has_perm('Usuarios.puede_ver_todas_solicitudes'):
        # Admin Empresa ve todas de su empresa
        solicitudes = Solicitud.objects.filter(
            empresa=user.empresa,
            deleted_at__isnull=True
        ).select_related(
            'empresa', 'solicitante', 'validador_abastecimiento', 'validador_finanzas'
        ).prefetch_related('items__producto')
    
    elif user.has_perm('Usuarios.puede_ver_solicitudes_area'):
        # Jefe de Área ve las de su área
        solicitudes = Solicitud.objects.filter(
            empresa=user.empresa,
            solicitante__area=user.area,
            deleted_at__isnull=True
        ).select_related(
            'empresa', 'solicitante', 'validador_abastecimiento', 'validador_finanzas'
        ).prefetch_related('items__producto')
    
    else:
        # Empleado ve solo las propias
        solicitudes = Solicitud.objects.filter(
            solicitante=user,
            deleted_at__isnull=True
        ).select_related(
            'empresa', 'solicitante', 'validador_abastecimiento', 'validador_finanzas'
        ).prefetch_related('items__producto')
    
    # Filtros opcionales por query params
    estado = request.query_params.get('estado')
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    
    fecha_desde = request.query_params.get('fecha_desde')
    if fecha_desde:
        solicitudes = solicitudes.filter(created_at__gte=fecha_desde)
    
    fecha_hasta = request.query_params.get('fecha_hasta')
    if fecha_hasta:
        solicitudes = solicitudes.filter(created_at__lte=fecha_hasta)
    
    serializer = SolicitudSerializer(solicitudes, many=True)
    
    return Response(
        {
            "count": solicitudes.count(),
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_solicitud(request, pk):
    """
    Obtiene el detalle de una solicitud específica
    """
    user = request.user
    solicitud = get_object_or_404(
        Solicitud,
        pk=pk,
        deleted_at__isnull=True
    )
    
    # Validar acceso
    if user.es_admin_empresa():
        if solicitud.empresa != user.empresa:
            return Response(
                {"error": "No tienes acceso a esta solicitud"},
                status=status.HTTP_403_FORBIDDEN
            )
    elif user.es_jefe_area():
        if solicitud.solicitante.area != user.area:
            return Response(
                {"error": "Solo puedes ver solicitudes de tu área"},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        if solicitud.solicitante != user:
            return Response(
                {"error": "Solo puedes ver tus propias solicitudes"},
                status=status.HTTP_403_FORBIDDEN
            )
    
    serializer = SolicitudSerializer(solicitud)
    
    # Agregar historial de validaciones
    historial = HistorialValidacion.objects.filter(
        solicitud=solicitud
    ).select_related('validador')
    
    return Response(
        {
            "solicitud": serializer.data,
            "historial": HistorialValidacionSerializer(historial, many=True).data
        },
        status=status.HTTP_200_OK
    )


# =============================================
# HU12 - VALIDACIÓN DE ABASTECIMIENTO
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validar_abastecimiento(request, pk):
    """
    Valida una solicitud desde el área de Abastecimiento (HU12)
    Solo usuarios con permiso validador_abastecimiento pueden hacerlo
    """
    user = request.user
    
    # Validar que sea validador de abastecimiento
    if not user.es_validador_abastecimiento():
        return Response(
            {"error": "No tienes permiso para validar abastecimiento"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    solicitud = get_object_or_404(
        Solicitud,
        pk=pk,
        empresa=user.empresa,
        deleted_at__isnull=True
    )
    
    # Validar que esté en estado correcto
    if solicitud.estado != Solicitud.EstadoSolicitud.PENDIENTE_ABASTECIMIENTO:
        return Response(
            {
                "error": f"La solicitud está en estado '{solicitud.get_estado_display()}', no puede ser validada"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar datos
    serializer = ValidarAbastecimientoSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accion = serializer.validated_data['accion']
    comentario = serializer.validated_data['comentario']
    items_modificados = serializer.validated_data.get('items_modificados', [])
    
    try:
        with transaction.atomic():
            # Guardar snapshot del estado anterior
            snapshot = {
                'estado': solicitud.estado,
                'monto_total': float(solicitud.monto_total),
                'items': [
                    {
                        'id': item.id,
                        'producto': item.producto.nombre,
                        'cantidad': item.cantidad,
                        'cantidad_aprobada': item.cantidad_aprobada
                    }
                    for item in solicitud.items.all()
                ]
            }
            
            if accion == 'aprobar':
                solicitud.estado = Solicitud.EstadoSolicitud.PENDIENTE_FINANZAS
                solicitud.stock_validado = True
                
            elif accion == 'rechazar':
                solicitud.estado = Solicitud.EstadoSolicitud.RECHAZADA_ABASTECIMIENTO
                
            elif accion == 'modificar':
                # Modificar cantidades de items
                for item_mod in items_modificados:
                    item_id = item_mod.get('id')
                    nueva_cantidad = item_mod.get('cantidad_aprobada')
                    
                    item = ItemSolicitud.objects.get(id=item_id, solicitud=solicitud)
                    item.cantidad_aprobada = nueva_cantidad
                    item.save()
                
                solicitud.estado = Solicitud.EstadoSolicitud.PENDIENTE_FINANZAS
                solicitud.stock_validado = True
            
            # Actualizar campos de validación
            solicitud.validador_abastecimiento = user
            solicitud.fecha_validacion_abastecimiento = timezone.now()
            solicitud.comentario_abastecimiento = comentario
            solicitud.save()
            
            # Crear registro en historial
            HistorialValidacion.objects.create(
                solicitud=solicitud,
                tipo_validacion=HistorialValidacion.TipoValidacion.ABASTECIMIENTO,
                accion=accion,
                validador=user,
                comentario=comentario,
                datos_anteriores=snapshot
            )
            
            logger.info(
                f"✅ Solicitud {solicitud.numero_solicitud} {accion} por {user.email} (Abastecimiento)"
            )
            
            return Response(
                {
                    "mensaje": f"Solicitud {accion} exitosamente",
                    "solicitud": SolicitudSerializer(solicitud).data
                },
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        logger.error(f"❌ Error validando abastecimiento: {str(e)}")
        return Response(
            {"error": f"Error en validación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# HU13 - VALIDACIÓN FINANCIERA
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validar_finanzas(request, pk):
    """
    Valida una solicitud desde el área Financiera (HU13)
    Solo usuarios con permiso validador_finanzas pueden hacerlo
    Valida límite de aprobación del usuario
    """
    user = request.user
    
    # Validar que sea validador financiero
    if not user.es_validador_finanzas():
        return Response(
            {"error": "No tienes permiso para validar finanzas"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    solicitud = get_object_or_404(
        Solicitud,
        pk=pk,
        empresa=user.empresa,
        deleted_at__isnull=True
    )
    
    # Validar que esté en estado correcto
    if solicitud.estado != Solicitud.EstadoSolicitud.PENDIENTE_FINANZAS:
        return Response(
            {
                "error": f"La solicitud está en estado '{solicitud.get_estado_display()}', no puede ser validada"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar datos
    serializer = ValidarFinanzasSerializer(
        data=request.data,
        context={'request': request, 'solicitud': solicitud}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accion = serializer.validated_data['accion']
    comentario = serializer.validated_data['comentario']
    
    try:
        with transaction.atomic():
            # Guardar snapshot del estado anterior
            snapshot = {
                'estado': solicitud.estado,
                'monto_total': float(solicitud.monto_total),
                'presupuesto_aprobado': solicitud.presupuesto_aprobado
            }
            
            if accion == 'aprobar':
                solicitud.estado = Solicitud.EstadoSolicitud.APROBADA
                solicitud.presupuesto_aprobado = True
                
            elif accion == 'rechazar':
                solicitud.estado = Solicitud.EstadoSolicitud.RECHAZADA_FINANZAS
            
            # Actualizar campos de validación
            solicitud.validador_finanzas = user
            solicitud.fecha_validacion_finanzas = timezone.now()
            solicitud.comentario_finanzas = comentario
            solicitud.save()
            
            # Crear registro en historial
            HistorialValidacion.objects.create(
                solicitud=solicitud,
                tipo_validacion=HistorialValidacion.TipoValidacion.FINANZAS,
                accion=accion,
                validador=user,
                comentario=comentario,
                datos_anteriores=snapshot
            )
            
            logger.info(
                f"✅ Solicitud {solicitud.numero_solicitud} {accion} por {user.email} (Finanzas)"
            )
            
            return Response(
                {
                    "mensaje": f"Solicitud {accion} exitosamente",
                    "solicitud": SolicitudSerializer(solicitud).data
                },
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        logger.error(f"❌ Error validando finanzas: {str(e)}")
        return Response(
            {"error": f"Error en validación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# ENDPOINTS AUXILIARES
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def solicitudes_pendientes_abastecimiento(request):
    """
    Lista solicitudes pendientes de validación de abastecimiento
    Solo para validadores de abastecimiento
    """
    user = request.user
    
    if not user.es_validador_abastecimiento():
        return Response(
            {"error": "No tienes permiso para ver estas solicitudes"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    solicitudes = Solicitud.objects.filter(
        empresa=user.empresa,
        estado=Solicitud.EstadoSolicitud.PENDIENTE_ABASTECIMIENTO,
        deleted_at__isnull=True
    ).select_related(
        'empresa', 'solicitante'
    ).prefetch_related('items__producto')
    
    serializer = SolicitudSerializer(solicitudes, many=True)
    
    return Response(
        {
            "count": solicitudes.count(),
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def solicitudes_pendientes_finanzas(request):
    """
    Lista solicitudes pendientes de validación financiera
    Solo para validadores financieros
    """
    user = request.user
    
    if not user.es_validador_finanzas():
        return Response(
            {"error": "No tienes permiso para ver estas solicitudes"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    solicitudes = Solicitud.objects.filter(
        empresa=user.empresa,
        estado=Solicitud.EstadoSolicitud.PENDIENTE_FINANZAS,
        deleted_at__isnull=True
    ).select_related(
        'empresa', 'solicitante', 'validador_abastecimiento'
    ).prefetch_related('items__producto')
    
    serializer = SolicitudSerializer(solicitudes, many=True)
    
    return Response(
        {
            "count": solicitudes.count(),
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancelar_solicitud(request, pk):
    """
    Cancela una solicitud (solo el solicitante o admin empresa)
    Solo si está en estado borrador o pendiente
    """
    user = request.user
    solicitud = get_object_or_404(
        Solicitud,
        pk=pk,
        deleted_at__isnull=True
    )
    
    # Validar permisos
    if solicitud.solicitante != user and not user.es_admin_empresa():
        return Response(
            {"error": "Solo el solicitante o admin empresa pueden cancelar"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar que se pueda cancelar
    estados_cancelables = [
        Solicitud.EstadoSolicitud.BORRADOR,
        Solicitud.EstadoSolicitud.PENDIENTE_ABASTECIMIENTO,
    ]
    
    if solicitud.estado not in estados_cancelables:
        return Response(
            {
                "error": f"No se puede cancelar una solicitud en estado '{solicitud.get_estado_display()}'"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    solicitud.estado = Solicitud.EstadoSolicitud.CANCELADA
    solicitud.deleted_at = timezone.now()
    solicitud.save()
    
    logger.info(f"✅ Solicitud {solicitud.numero_solicitud} cancelada por {user.email}")
    
    return Response(
        {"mensaje": "Solicitud cancelada exitosamente"},
        status=status.HTTP_200_OK
    )
