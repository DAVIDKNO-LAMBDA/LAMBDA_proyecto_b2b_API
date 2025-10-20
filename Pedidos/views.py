from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Pedido, ItemPedido, HistorialValidacionPedido, RecordatorioPago
from .serializers import (
    PedidoSerializer,
    PedidoListSerializer,
    ConvertirSolicitudSerializer,
    ValidarAbastecimientoLambdaSerializer,
    ValidarFinanzasLambdaSerializer,
    GestionarPagoSerializer,
    HistorialValidacionPedidoSerializer,
    RecordatorioPagoSerializer
)
from Productos.models import MovimientoInventario
from Solicitudes.models import Solicitud
import logging

logger = logging.getLogger(__name__)


# =============================================
# HU14 - CONVERSIÓN SOLICITUD A PEDIDO
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convertir_solicitud_a_pedido(request):
    """
    Convierte una solicitud aprobada en pedido externo hacia Lambda (HU14)
    Solo Admin Empresa o solicitante original pueden convertir
    """
    user = request.user
    
    # Validar permisos usando sistema JSON dinámico
    if not (user.es_admin_empresa() or user.permisos_personalizados.get('puede_crear_solicitudes', False)):
        return Response(
            {"error": "No tienes permisos para convertir solicitudes"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ConvertirSolicitudSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            pedido = serializer.save()
            
            logger.info(
                f"✅ Pedido {pedido.numero_pedido} creado desde solicitud {pedido.solicitud_origen.numero_solicitud} por {user.email}"
            )
            
            return Response(
                {
                    "mensaje": "Solicitud convertida a pedido exitosamente",
                    "pedido": PedidoSerializer(pedido).data
                },
                status=status.HTTP_201_CREATED
            )
    
    except Exception as e:
        logger.error(f"❌ Error convirtiendo solicitud a pedido: {str(e)}")
        return Response(
            {"error": f"Error creando pedido: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# ASIGNACIÓN A ÁREAS LAMBDA
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_a_area_abastecimiento(request, pk):
    """
    Asigna un pedido al área de Abastecimiento Lambda para iniciar validaciones
    Solo Admin Lambda puede hacer esta asignación
    """
    user = request.user
    
    # Solo Admin Lambda puede asignar a áreas
    if not (user.es_usuario_lambda() and user.groups.filter(name='Admin Lambda').exists()):
        return Response(
            {"error": "Solo Admin Lambda puede asignar pedidos a áreas"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
    
    # Validar estado
    if pedido.estado != Pedido.EstadoPedido.PENDIENTE_VALIDACION_LAMBDA:
        return Response(
            {
                "error": f"El pedido está en estado '{pedido.get_estado_display()}', no puede ser asignado"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with transaction.atomic():
            # Cambiar estado a pendiente de abastecimiento
            pedido.estado = Pedido.EstadoPedido.PENDIENTE_ABASTECIMIENTO_LAMBDA
            pedido.save(update_fields=['estado', 'updated_at'])
            
            # Crear registro en historial
            HistorialValidacionPedido.objects.create(
                pedido=pedido,
                tipo_validacion=HistorialValidacionPedido.TipoValidacion.ABASTECIMIENTO_LAMBDA,
                accion="asignar_area",
                validador=user,
                comentario="Pedido asignado al área de Abastecimiento Lambda",
                datos_anteriores={'estado_anterior': 'pendiente_validacion_lambda'}
            )
            
            logger.info(
                f"✅ Pedido {pedido.numero_pedido} asignado a Abastecimiento Lambda por {user.email}"
            )
            
            return Response(
                {
                    "mensaje": "Pedido asignado al área de Abastecimiento Lambda exitosamente",
                    "pedido": PedidoSerializer(pedido).data
                },
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        logger.error(f"❌ Error asignando pedido a área: {str(e)}")
        return Response(
            {"error": f"Error en asignación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# LISTAR Y VER PEDIDOS (HU20)
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_pedidos(request):
    """
    Lista pedidos según el rol del usuario (HU20)
    - Lambda: Todos los pedidos
    - Empresa Cliente: Solo sus pedidos
    """
    user = request.user
    
    # Filtrar según usuario
    if user.es_usuario_lambda():
        # Staff Lambda ve todos los pedidos
        pedidos = Pedido.objects.filter(deleted_at__isnull=True)
    elif hasattr(user, 'empresa') and user.empresa:
        # Usuario de empresa ve solo pedidos de su empresa
        pedidos = Pedido.objects.filter(
            empresa_cliente=user.empresa,
            deleted_at__isnull=True
        )
    else:
        return Response(
            {"error": "Usuario sin permisos para ver pedidos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Filtros opcionales
    estado = request.query_params.get('estado')
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    empresa_id = request.query_params.get('empresa_id')
    if empresa_id and user.es_usuario_lambda():
        pedidos = pedidos.filter(empresa_cliente_id=empresa_id)
    
    modalidad_pago = request.query_params.get('modalidad_pago')
    if modalidad_pago:
        pedidos = pedidos.filter(modalidad_pago=modalidad_pago)
    
    fecha_desde = request.query_params.get('fecha_desde')
    if fecha_desde:
        pedidos = pedidos.filter(created_at__gte=fecha_desde)
    
    fecha_hasta = request.query_params.get('fecha_hasta')
    if fecha_hasta:
        pedidos = pedidos.filter(created_at__lte=fecha_hasta)
    
    # Solo vencidos
    solo_vencidos = request.query_params.get('vencidos') == 'true'
    if solo_vencidos:
        pedidos = pedidos.filter(
            modalidad_pago=Pedido.ModalidadPago.DIFERIDO,
            fecha_limite_pago__lt=timezone.now().date(),
            estado__in=[
                Pedido.EstadoPedido.PENDIENTE_PAGO,
                Pedido.EstadoPedido.PAGO_VENCIDO
            ]
        )
    
    # Optimizar consultas
    pedidos = pedidos.select_related(
        'empresa_cliente', 'usuario_solicitante', 'solicitud_origen'
    ).prefetch_related('items__producto')
    
    # Paginación simple
    page_size = int(request.query_params.get('page_size', 20))
    page = int(request.query_params.get('page', 1))
    start = (page - 1) * page_size
    end = start + page_size
    
    total = pedidos.count()
    pedidos_paginados = pedidos[start:end]
    
    serializer = PedidoListSerializer(pedidos_paginados, many=True)
    
    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_pedido(request, pk):
    """
    Obtiene el detalle completo de un pedido
    """
    user = request.user
    
    # Filtrar según permisos
    if user.es_usuario_lambda():
        pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
    elif hasattr(user, 'empresa') and user.empresa:
        pedido = get_object_or_404(
            Pedido, 
            pk=pk, 
            empresa_cliente=user.empresa,
            deleted_at__isnull=True
        )
    else:
        return Response(
            {"error": "No tienes acceso a este pedido"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = PedidoSerializer(pedido)
    
    # Agregar historial de validaciones
    historial = HistorialValidacionPedido.objects.filter(
        pedido=pedido
    ).select_related('validador').order_by('-created_at')
    
    # Agregar recordatorios si existen
    recordatorios = RecordatorioPago.objects.filter(
        pedido=pedido
    ).order_by('fecha_programada')
    
    return Response(
        {
            "pedido": serializer.data,
            "historial": HistorialValidacionPedidoSerializer(historial, many=True).data,
            "recordatorios": RecordatorioPagoSerializer(recordatorios, many=True).data
        },
        status=status.HTTP_200_OK
    )


# =============================================
# VALIDACIONES LAMBDA - ABASTECIMIENTO
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validar_abastecimiento_lambda(request, pk):
    """
    Valida un pedido desde Área Abastecimiento Lambda
    Solo validadores del área específica de abastecimiento Lambda
    """
    user = request.user
    
    # Validar que sea usuario del área específica de abastecimiento Lambda
    if not user.puede_validar_abastecimiento_lambda():
        return Response(
            {"error": "Solo validadores del área de Abastecimiento Lambda pueden validar pedidos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pedido = get_object_or_404(
        Pedido,
        pk=pk,
        deleted_at__isnull=True
    )
    
    # Validar estado
    if pedido.estado != Pedido.EstadoPedido.PENDIENTE_ABASTECIMIENTO_LAMBDA:
        return Response(
            {
                "error": f"El pedido está en estado '{pedido.get_estado_display()}', no puede ser validado"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ValidarAbastecimientoLambdaSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accion = serializer.validated_data['accion']
    comentario = serializer.validated_data['comentario']
    items_modificados = serializer.validated_data.get('items_modificados', [])
    
    try:
        with transaction.atomic():
            # Snapshot del estado anterior
            snapshot = {
                'estado': pedido.estado,
                'monto_total': float(pedido.monto_total),
                'items': [
                    {
                        'id': item.id,
                        'producto': item.producto.nombre,
                        'cantidad_final': item.cantidad_final,
                        'precio_unitario_final': float(item.precio_unitario_final)
                    }
                    for item in pedido.items.all()
                ]
            }
            
            if accion == 'aprobar':
                pedido.estado = Pedido.EstadoPedido.PENDIENTE_FINANZAS_LAMBDA
                pedido.stock_confirmado_lambda = True
                
                # Reservar stock en Lambda
                for item in pedido.items.all():
                    MovimientoInventario.objects.create(
                        producto=item.producto,
                        tipo=MovimientoInventario.TipoMovimiento.RESERVA,
                        cantidad=item.cantidad_final,
                        descripcion=f"Reserva para pedido {pedido.numero_pedido}",
                        usuario_responsable=user,
                        pedido=pedido
                    )
                    item.stock_reservado = True
                    item.save(update_fields=['stock_reservado'])
                
            elif accion == 'rechazar':
                pedido.estado = Pedido.EstadoPedido.RECHAZADO_ABASTECIMIENTO_LAMBDA
                
            elif accion == 'modificar':
                # Modificar items
                for item_mod in items_modificados:
                    item = ItemPedido.objects.get(id=item_mod['id'], pedido=pedido)
                    item.cantidad_final = item_mod['cantidad_final']
                    item.precio_unitario_final = item_mod['precio_unitario_final']
                    item.save()
                
                pedido.estado = Pedido.EstadoPedido.PENDIENTE_FINANZAS_LAMBDA
                pedido.stock_confirmado_lambda = True
            
            # Actualizar campos de validación
            pedido.validador_abastecimiento_lambda = user
            pedido.fecha_validacion_abastecimiento_lambda = timezone.now()
            pedido.comentario_abastecimiento_lambda = comentario
            pedido.save()
            
            # Crear registro en historial
            HistorialValidacionPedido.objects.create(
                pedido=pedido,
                tipo_validacion=HistorialValidacionPedido.TipoValidacion.ABASTECIMIENTO_LAMBDA,
                accion=accion,
                validador=user,
                comentario=comentario,
                datos_anteriores=snapshot
            )
            
            logger.info(
                f"✅ Pedido {pedido.numero_pedido} {accion} por {user.email} (Abastecimiento Lambda)"
            )
            
            return Response(
                {
                    "mensaje": f"Pedido {accion} exitosamente",
                    "pedido": PedidoSerializer(pedido).data
                },
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        logger.error(f"❌ Error validando abastecimiento Lambda: {str(e)}")
        return Response(
            {"error": f"Error en validación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# VALIDACIONES LAMBDA - FINANZAS
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validar_finanzas_lambda(request, pk):
    """
    Valida un pedido desde Área Finanzas Lambda (HU15)
    Define condiciones de pago
    """
    user = request.user
    
    # Validar que sea usuario del área específica de finanzas Lambda
    if not user.puede_validar_finanzas_lambda():
        return Response(
            {"error": "Solo validadores del área de Finanzas Lambda pueden validar pedidos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
    
    # Validar estado
    if pedido.estado != Pedido.EstadoPedido.PENDIENTE_FINANZAS_LAMBDA:
        return Response(
            {
                "error": f"El pedido está en estado '{pedido.get_estado_display()}', no puede ser validado"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ValidarFinanzasLambdaSerializer(
        data=request.data,
        context={'pedido': pedido}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accion = serializer.validated_data['accion']
    comentario = serializer.validated_data['comentario']
    
    try:
        with transaction.atomic():
            snapshot = {
                'estado': pedido.estado,
                'modalidad_pago': pedido.modalidad_pago,
                'fecha_limite_pago': str(pedido.fecha_limite_pago) if pedido.fecha_limite_pago else None,
                'monto_final': float(pedido.monto_final)
            }
            
            if accion == 'aprobar':
                # Aplicar condiciones de pago
                pedido.modalidad_pago = serializer.validated_data['modalidad_pago']
                pedido.fecha_limite_pago = serializer.validated_data.get('fecha_limite_pago')
                pedido.descuento_aplicado = serializer.validated_data.get('descuento_aplicado', 0)
                
                pedido.estado = Pedido.EstadoPedido.APROBADO_LAMBDA
                pedido.credito_aprobado_lambda = True
                
                # Recalcular montos con descuento
                pedido.calcular_monto_total()
                
                if pedido.modalidad_pago == Pedido.ModalidadPago.INMEDIATO:
                    pedido.estado = Pedido.EstadoPedido.PENDIENTE_PAGO
                else:
                    pedido.estado = Pedido.EstadoPedido.PENDIENTE_PAGO
                    # Programar recordatorios automáticamente
                    programar_recordatorios_pago(pedido)
                
            elif accion == 'rechazar':
                pedido.estado = Pedido.EstadoPedido.RECHAZADO_FINANZAS_LAMBDA
                
                # Liberar stock reservado
                for item in pedido.items.filter(stock_reservado=True):
                    MovimientoInventario.objects.create(
                        producto=item.producto,
                        tipo=MovimientoInventario.TipoMovimiento.LIBERACION,
                        cantidad=item.cantidad_final,
                        descripcion=f"Liberación por rechazo de pedido {pedido.numero_pedido}",
                        usuario_responsable=user,
                        pedido=pedido
                    )
                    item.stock_reservado = False
                    item.save(update_fields=['stock_reservado'])
            
            # Actualizar campos de validación
            pedido.validador_finanzas_lambda = user
            pedido.fecha_validacion_finanzas_lambda = timezone.now()
            pedido.comentario_finanzas_lambda = comentario
            pedido.save()
            
            # Crear registro en historial
            HistorialValidacionPedido.objects.create(
                pedido=pedido,
                tipo_validacion=HistorialValidacionPedido.TipoValidacion.FINANZAS_LAMBDA,
                accion=accion,
                validador=user,
                comentario=comentario,
                datos_anteriores=snapshot
            )
            
            logger.info(
                f"✅ Pedido {pedido.numero_pedido} {accion} por {user.email} (Finanzas Lambda)"
            )
            
            return Response(
                {
                    "mensaje": f"Pedido {accion} exitosamente",
                    "pedido": PedidoSerializer(pedido).data
                },
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        logger.error(f"❌ Error validando finanzas Lambda: {str(e)}")
        return Response(
            {"error": f"Error en validación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# GESTIÓN DE PAGOS (HU16)
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gestionar_pago(request, pk):
    """
    Gestiona el pago de un pedido (HU16)
    Solo staff Lambda puede confirmar pagos
    """
    user = request.user
    
    if not user.es_usuario_lambda():
        return Response(
            {"error": "Solo usuarios de Lambda pueden gestionar pagos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
    
    # Validar estado
    estados_validos = [
        Pedido.EstadoPedido.PENDIENTE_PAGO,
        Pedido.EstadoPedido.PAGO_VENCIDO
    ]
    
    if pedido.estado not in estados_validos:
        return Response(
            {
                "error": f"El pedido está en estado '{pedido.get_estado_display()}', no se puede gestionar pago"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = GestionarPagoSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accion = serializer.validated_data['accion']
    
    try:
        with transaction.atomic():
            if accion == 'confirmar_pago':
                pedido.fecha_pago = serializer.validated_data.get('fecha_pago', timezone.now())
                pedido.comprobante_pago = serializer.validated_data['comprobante_pago']
                pedido.metodo_pago = serializer.validated_data['metodo_pago']
                pedido.estado = Pedido.EstadoPedido.PAGO_CONFIRMADO
                
                # TODO: Aquí se podría automatizar la facturación
                # pedido.estado = Pedido.EstadoPedido.FACTURADO
                
                # Crear registro de pago en historial
                HistorialValidacionPedido.objects.create(
                    pedido=pedido,
                    tipo_validacion=HistorialValidacionPedido.TipoValidacion.PAGO,
                    accion=HistorialValidacionPedido.AccionValidacion.PAGO_CONFIRMADO,
                    validador=user,
                    comentario=serializer.validated_data.get('observaciones', ''),
                    monto_pago=serializer.validated_data['monto_pago'],
                    metodo_pago=serializer.validated_data['metodo_pago']
                )
                
                mensaje = "Pago confirmado exitosamente"
                
            elif accion == 'marcar_vencido':
                pedido.estado = Pedido.EstadoPedido.PAGO_VENCIDO
                mensaje = "Pago marcado como vencido"
                
            elif accion == 'extender_plazo':
                # Nueva funcionalidad: extender plazo de pago
                fecha_anterior = pedido.fecha_limite_pago
                pedido.fecha_limite_pago = serializer.validated_data['nueva_fecha_limite']
                
                # Si estaba vencido, volver a pendiente
                if pedido.estado == Pedido.EstadoPedido.PAGO_VENCIDO:
                    pedido.estado = Pedido.EstadoPedido.PENDIENTE_PAGO
                
                # Crear historial de extensión
                HistorialValidacionPedido.objects.create(
                    pedido=pedido,
                    tipo_validacion=HistorialValidacionPedido.TipoValidacion.PAGO,
                    accion=HistorialValidacionPedido.AccionValidacion.MODIFICAR,
                    validador=user,
                    comentario=f"Plazo extendido: {fecha_anterior} → {pedido.fecha_limite_pago}. Motivo: {serializer.validated_data['motivo_extension']}",
                    datos_anteriores={
                        'fecha_limite_anterior': str(fecha_anterior) if fecha_anterior else None,
                        'estado_anterior': pedido.estado
                    }
                )
                
                # Reprogramar recordatorios
                programar_recordatorios_pago(pedido)
                
                mensaje = f"Plazo extendido hasta {pedido.fecha_limite_pago}"
            
            pedido.save()
            
            logger.info(f"✅ Pago de pedido {pedido.numero_pedido} gestionado por {user.email}: {accion}")
            
            return Response(
                {
                    "mensaje": mensaje,
                    "pedido": PedidoSerializer(pedido).data
                },
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        logger.error(f"❌ Error gestionando pago: {str(e)}")
        return Response(
            {"error": f"Error gestionando pago: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_como_facturado(request, pk):
    """
    Marca un pedido como facturado - Estado final del proceso
    Solo staff Lambda puede marcar como facturado
    """
    user = request.user
    
    if not user.es_usuario_lambda():
        return Response(
            {"error": "Solo usuarios de Lambda pueden marcar como facturado"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
    
    # Validar estado
    if pedido.estado != Pedido.EstadoPedido.PAGO_CONFIRMADO:
        return Response(
            {
                "error": f"El pedido debe estar en estado 'Pago Confirmado' para facturar, actualmente está '{pedido.get_estado_display()}'"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with transaction.atomic():
            pedido.estado = Pedido.EstadoPedido.FACTURADO
            pedido.fecha_facturacion = timezone.now().date()
            pedido.save()
            
            # Crear registro en historial
            HistorialValidacionPedido.objects.create(
                pedido=pedido,
                tipo_validacion=HistorialValidacionPedido.TipoValidacion.FACTURACION,
                accion=HistorialValidacionPedido.AccionValidacion.APROBAR,
                validador=user,
                comentario=request.data.get('comentario', 'Pedido facturado')
            )
            
            # Confirmar stock (quitar de inventario definitivamente)
            for item in pedido.items.filter(stock_reservado=True):
                MovimientoInventario.objects.create(
                    producto=item.producto,
                    tipo=MovimientoInventario.TipoMovimiento.SALIDA,
                    cantidad=item.cantidad_final,
                    descripcion=f"Venta facturada - Pedido {pedido.numero_pedido}",
                    usuario_responsable=user,
                    pedido=pedido
                )
                item.stock_reservado = False
                item.save(update_fields=['stock_reservado'])
            
            logger.info(f"✅ Pedido {pedido.numero_pedido} marcado como facturado por {user.email}")
            
            return Response(
                {
                    "mensaje": "Pedido marcado como facturado exitosamente",
                    "pedido": PedidoSerializer(pedido).data
                },
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        logger.error(f"❌ Error marcando como facturado: {str(e)}")
        return Response(
            {"error": f"Error marcando como facturado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# ENDPOINTS AUXILIARES PARA LAMBDA
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pedidos_pendientes_validacion_lambda(request):
    """
    Lista pedidos pendientes de validación general Lambda (recién convertidos)
    Solo para Admin Lambda para asignar a áreas
    """
    user = request.user
    
    if not (user.es_usuario_lambda() and user.groups.filter(name='Admin Lambda').exists()):
        return Response(
            {"error": "Solo Admin Lambda puede ver estos pedidos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pedidos = Pedido.objects.filter(
        estado=Pedido.EstadoPedido.PENDIENTE_VALIDACION_LAMBDA,
        deleted_at__isnull=True
    ).select_related('empresa_cliente', 'usuario_solicitante').prefetch_related('items__producto')
    
    serializer = PedidoListSerializer(pedidos, many=True)
    
    return Response(
        {
            "count": pedidos.count(),
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pedidos_pendientes_abastecimiento_lambda(request):
    """
    Lista pedidos pendientes de validación de abastecimiento en Lambda
    Solo para staff Lambda con permisos
    """
    user = request.user
    
    if not user.puede_validar_abastecimiento_lambda():
        return Response(
            {"error": "Solo validadores del área de Abastecimiento Lambda pueden ver estos pedidos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pedidos = Pedido.objects.filter(
        estado=Pedido.EstadoPedido.PENDIENTE_ABASTECIMIENTO_LAMBDA,
        deleted_at__isnull=True
    ).select_related('empresa_cliente', 'usuario_solicitante').prefetch_related('items__producto')
    
    serializer = PedidoListSerializer(pedidos, many=True)
    
    return Response(
        {
            "count": pedidos.count(),
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pedidos_pendientes_finanzas_lambda(request):
    """
    Lista pedidos pendientes de validación financiera en Lambda
    Solo para staff Lambda con permisos
    """
    user = request.user
    
    if not user.puede_validar_finanzas_lambda():
        return Response(
            {"error": "Solo validadores del área de Finanzas Lambda pueden ver estos pedidos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pedidos = Pedido.objects.filter(
        estado=Pedido.EstadoPedido.PENDIENTE_FINANZAS_LAMBDA,
        deleted_at__isnull=True
    ).select_related('empresa_cliente', 'usuario_solicitante', 'validador_abastecimiento_lambda')
    
    serializer = PedidoListSerializer(pedidos, many=True)
    
    return Response(
        {
            "count": pedidos.count(),
            "results": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_lambda(request):
    """
    Dashboard con estadísticas para Lambda
    """
    user = request.user
    
    if not user.es_usuario_lambda():
        return Response(
            {"error": "Solo usuarios de Lambda pueden ver el dashboard"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Estadísticas generales
    stats = {
        'pedidos_pendientes_abastecimiento': Pedido.objects.filter(
            estado=Pedido.EstadoPedido.PENDIENTE_ABASTECIMIENTO_LAMBDA
        ).count(),
        'pedidos_pendientes_finanzas': Pedido.objects.filter(
            estado=Pedido.EstadoPedido.PENDIENTE_FINANZAS_LAMBDA
        ).count(),
        'pedidos_pendientes_pago': Pedido.objects.filter(
            estado=Pedido.EstadoPedido.PENDIENTE_PAGO
        ).count(),
        'pedidos_vencidos': Pedido.objects.filter(
            estado=Pedido.EstadoPedido.PAGO_VENCIDO
        ).count(),
        'pedidos_hoy': Pedido.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
        'monto_pendiente_pago': Pedido.objects.filter(
            estado__in=[
                Pedido.EstadoPedido.PENDIENTE_PAGO,
                Pedido.EstadoPedido.PAGO_VENCIDO
            ]
        ).aggregate(total=Sum('monto_final'))['total'] or 0
    }
    
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estadisticas_pagos(request):
    """
    Estadísticas detalladas del sistema de pagos para Lambda
    """
    user = request.user
    
    if not user.es_usuario_lambda():
        return Response(
            {"error": "Solo usuarios de Lambda pueden ver estadísticas de pagos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from datetime import datetime, timedelta
    from django.db.models import Sum, Count, Avg, Q
    
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    fin_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Estadísticas generales
    stats = {
        'resumen_general': {
            'pedidos_pendientes_pago': Pedido.objects.filter(
                estado=Pedido.EstadoPedido.PENDIENTE_PAGO
            ).count(),
            'pedidos_vencidos': Pedido.objects.filter(
                estado=Pedido.EstadoPedido.PAGO_VENCIDO
            ).count(),
            'pedidos_pagados_hoy': Pedido.objects.filter(
                estado=Pedido.EstadoPedido.PAGO_CONFIRMADO,
                fecha_pago__date=hoy
            ).count(),
            'monto_pendiente_total': Pedido.objects.filter(
                estado__in=[
                    Pedido.EstadoPedido.PENDIENTE_PAGO,
                    Pedido.EstadoPedido.PAGO_VENCIDO
                ]
            ).aggregate(total=Sum('monto_final'))['total'] or 0,
        },
        
        'estadisticas_mes_actual': {
            'pedidos_creados': Pedido.objects.filter(
                created_at__date__range=[inicio_mes, fin_mes]
            ).count(),
            'pagos_recibidos': Pedido.objects.filter(
                fecha_pago__date__range=[inicio_mes, fin_mes],
                estado=Pedido.EstadoPedido.PAGO_CONFIRMADO
            ).count(),
            'monto_facturado': Pedido.objects.filter(
                fecha_pago__date__range=[inicio_mes, fin_mes],
                estado=Pedido.EstadoPedido.PAGO_CONFIRMADO
            ).aggregate(total=Sum('monto_final'))['total'] or 0,
            'tiempo_promedio_pago': Pedido.objects.filter(
                fecha_pago__date__range=[inicio_mes, fin_mes],
                estado=Pedido.EstadoPedido.PAGO_CONFIRMADO
            ).aggregate(
                promedio=Avg('fecha_pago') - Avg('created_at')
            )['promedio'] or 0,
        },
        
        'recordatorios': {
            'programados_hoy': RecordatorioPago.objects.filter(
                fecha_programada__date=hoy,
                enviado=False
            ).count(),
            'enviados_hoy': RecordatorioPago.objects.filter(
                fecha_envio__date=hoy
            ).count(),
            'proximos_7_dias': RecordatorioPago.objects.filter(
                fecha_programada__date__range=[hoy, hoy + timedelta(days=7)],
                enviado=False
            ).count(),
        },
        
        'top_empresas_morosas': list(
            Pedido.objects.filter(
                estado=Pedido.EstadoPedido.PAGO_VENCIDO
            ).values(
                'empresa_cliente__nombre'
            ).annotate(
                pedidos_vencidos=Count('id'),
                monto_total=Sum('monto_final')
            ).order_by('-monto_total')[:5]
        ),
        
        'metodos_pago_populares': list(
            Pedido.objects.filter(
                estado=Pedido.EstadoPedido.PAGO_CONFIRMADO,
                fecha_pago__date__range=[inicio_mes, fin_mes]
            ).exclude(
                metodo_pago__isnull=True
            ).values(
                'metodo_pago'
            ).annotate(
                cantidad=Count('id'),
                monto_total=Sum('monto_final')
            ).order_by('-cantidad')
        )
    }
    
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ejecutar_procesamiento_pagos(request):
    """
    Ejecuta manualmente el procesamiento de pagos (solo para Lambda)
    Útil para testing y ejecución manual
    """
    user = request.user
    
    if not user.es_usuario_lambda():
        return Response(
            {"error": "Solo usuarios de Lambda pueden ejecutar procesamiento de pagos"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Capturar output del comando
        output = StringIO()
        
        # Parámetros del request
        dry_run = request.data.get('dry_run', False)
        enviar_emails = request.data.get('enviar_emails', False)
        
        args = []
        if dry_run:
            args.append('--dry-run')
        if enviar_emails:
            args.append('--enviar-emails')
        
        # Ejecutar comando
        call_command('procesar_pagos', *args, stdout=output)
        
        resultado = output.getvalue()
        
        logger.info(f"✅ Procesamiento de pagos ejecutado manualmente por {user.email}")
        
        return Response(
            {
                "mensaje": "Procesamiento de pagos ejecutado exitosamente",
                "resultado": resultado,
                "parametros": {
                    "dry_run": dry_run,
                    "enviar_emails": enviar_emails
                }
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"❌ Error ejecutando procesamiento de pagos: {str(e)}")
        return Response(
            {"error": f"Error ejecutando procesamiento: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# FUNCIONES AUXILIARES
# =============================================

def programar_recordatorios_pago(pedido):
    """
    Programa recordatorios automáticos para un pedido con pago diferido (HU19)
    """
    if pedido.modalidad_pago != Pedido.ModalidadPago.DIFERIDO or not pedido.fecha_limite_pago:
        return
    
    from datetime import timedelta
    
    recordatorios = [
        {
            'tipo': RecordatorioPago.TipoRecordatorio.PREVENTIVO,
            'dias_antes': 3,
            'asunto': f'Recordatorio: Pago próximo a vencer - {pedido.numero_pedido}'
        },
        {
            'tipo': RecordatorioPago.TipoRecordatorio.VENCIMIENTO,
            'dias_antes': 0,
            'asunto': f'URGENTE: Pago vence hoy - {pedido.numero_pedido}'
        },
        {
            'tipo': RecordatorioPago.TipoRecordatorio.MORA_1,
            'dias_antes': -15,
            'asunto': f'MORA: Pago vencido hace 15 días - {pedido.numero_pedido}'
        },
        {
            'tipo': RecordatorioPago.TipoRecordatorio.MORA_2,
            'dias_antes': -30,
            'asunto': f'MORA: Pago vencido hace 30 días - {pedido.numero_pedido}'
        },
        {
            'tipo': RecordatorioPago.TipoRecordatorio.MORA_3,
            'dias_antes': -45,
            'asunto': f'MORA: Pago vencido hace 45 días - {pedido.numero_pedido}'
        },
        {
            'tipo': RecordatorioPago.TipoRecordatorio.MORA_4,
            'dias_antes': -60,
            'asunto': f'MORA: Pago vencido hace 60 días - {pedido.numero_pedido}'
        },
        {
            'tipo': RecordatorioPago.TipoRecordatorio.LEGAL,
            'dias_antes': -75,
            'asunto': f'AVISO LEGAL: Acciones legales por mora - {pedido.numero_pedido}'
        },
    ]
    
    for recordatorio in recordatorios:
        fecha_programada = pedido.fecha_limite_pago + timedelta(days=recordatorio['dias_antes'])
        fecha_programada = timezone.make_aware(
            timezone.datetime.combine(fecha_programada, timezone.datetime.min.time())
        )
        
        RecordatorioPago.objects.get_or_create(
            pedido=pedido,
            tipo=recordatorio['tipo'],
            defaults={
                'fecha_programada': fecha_programada,
                'email_destinatario': pedido.empresa_cliente.correo_contacto,
                'asunto': recordatorio['asunto']
            }
        )


# =============================================
# 🔧 ASIGNACIÓN DE ÁREAS LAMBDA 
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_area_lambda(request, pk):
    """
    Permite al Admin Lambda asignar un pedido a un área específica
    para que sea validado por el validador correspondiente.
    
    Payload:
    {
        "area_destino": "abastecimiento" | "finanzas",
        "observaciones": "Motivo de la asignación"
    }
    """
    user = request.user
    
    # 🔒 Verificar permisos - Solo Admin Lambda
    if not user.es_admin_lambda():
        return Response(
            {"error": "Solo Admin Lambda puede asignar pedidos a áreas específicas"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        pedido = Pedido.objects.get(id=pk, deleted_at__isnull=True)
    except Pedido.DoesNotExist:
        return Response(
            {"error": "Pedido no encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # ✅ Verificar estado válido para asignación
    if pedido.estado != Pedido.EstadoPedido.PENDIENTE_VALIDACION_LAMBDA:
        return Response({
            "error": f"Solo se pueden asignar pedidos en estado 'Pendiente Validación Lambda'. Estado actual: {pedido.get_estado_display()}"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 📋 Obtener datos del request
    area_destino = request.data.get('area_destino')
    observaciones = request.data.get('observaciones', '')
    
    # 🔍 Validar área destino
    areas_validas = ['abastecimiento', 'finanzas']
    if area_destino not in areas_validas:
        return Response({
            "error": f"Área destino inválida. Opciones válidas: {', '.join(areas_validas)}"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 🎯 Asignar según el área destino
    try:
        if area_destino == 'abastecimiento':
            # Cambiar estado a pendiente abastecimiento
            pedido.estado = Pedido.EstadoPedido.PENDIENTE_ABASTECIMIENTO_LAMBDA
            mensaje_actividad = f"Pedido asignado al área de Abastecimiento Lambda para validación de stock"
            
        elif area_destino == 'finanzas':
            # Cambiar estado a pendiente finanzas
            pedido.estado = Pedido.EstadoPedido.PENDIENTE_FINANZAS_LAMBDA  
            mensaje_actividad = f"Pedido asignado al área de Finanzas Lambda para validación crediticia"
        
        pedido.save()
        
        # 📝 Registrar en historial
        HistorialValidacionPedido.objects.create(
            pedido=pedido,
            usuario=user,
            accion=HistorialValidacionPedido.AccionValidacion.ASIGNACION_AREA,
            estado_anterior=Pedido.EstadoPedido.PENDIENTE_VALIDACION_LAMBDA,
            estado_nuevo=pedido.estado,
            observaciones=f"{mensaje_actividad}. {observaciones}".strip(),
            area_asignada=area_destino
        )
        
        # 📧 Notificar por email (opcional)
        try:
            from Base.correos import enviar_notificacion_asignacion_area
            enviar_notificacion_asignacion_area(pedido, area_destino, user)
        except Exception as e:
            logger.warning(f"Error al enviar notificación de asignación: {e}")
        
        return Response({
            "success": True,
            "message": mensaje_actividad,
            "pedido": {
                "id": pedido.id,
                "numero_pedido": pedido.numero_pedido,
                "estado": pedido.estado,
                "estado_display": pedido.get_estado_display(),
                "area_asignada": area_destino
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error al asignar área Lambda: {e}")
        return Response({
            "error": "Error interno al asignar el pedido"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
