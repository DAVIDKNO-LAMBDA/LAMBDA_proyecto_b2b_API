from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.http import HttpResponse, FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Factura, ReportePeriodico, ConfiguracionReporte
from .serializers import (
    FacturaSerializer, FacturaListSerializer, GenerarFacturaSerializer,
    ReportePeriodicoSerializer, GenerarReporteSerializer,
    ConfiguracionReporteSerializer, DashboardSerializer
)
from .services.facturacion_service import facturacion_service
from .services.pdf_generator import pdf_generator, excel_generator
from Pedidos.models import Pedido
from Empresas.models import Empresa
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# =============================================
# GESTIÓN DE FACTURAS (HU24)
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_facturas(request):
    """
    Lista facturas según permisos del usuario
    """
    user = request.user
    
    # Filtrar según usuario
    if user.es_usuario_lambda():
        # Lambda ve todas las facturas
        facturas = Factura.objects.filter(deleted_at__isnull=True)
    elif hasattr(user, 'empresa') and user.empresa:
        # Usuario de empresa ve solo sus facturas
        facturas = Factura.objects.filter(
            empresa_cliente=user.empresa,
            deleted_at__isnull=True
        )
    else:
        return Response(
            {"error": "Usuario sin permisos para ver facturas"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Filtros opcionales
    estado = request.query_params.get('estado')
    if estado:
        facturas = facturas.filter(estado=estado)
    
    empresa_id = request.query_params.get('empresa_id')
    if empresa_id and user.es_usuario_lambda():
        facturas = facturas.filter(empresa_cliente_id=empresa_id)
    
    fecha_desde = request.query_params.get('fecha_desde')
    if fecha_desde:
        facturas = facturas.filter(fecha_emision__gte=fecha_desde)
    
    fecha_hasta = request.query_params.get('fecha_hasta')
    if fecha_hasta:
        facturas = facturas.filter(fecha_emision__lte=fecha_hasta)
    
    # Solo vencidas
    solo_vencidas = request.query_params.get('vencidas') == 'true'
    if solo_vencidas:
        facturas = facturas.filter(
            fecha_vencimiento__lt=timezone.now().date(),
            estado__in=[Factura.EstadoFactura.ENVIADA, Factura.EstadoFactura.GENERADA]
        )
    
    # Optimizar consultas
    facturas = facturas.select_related(
        'empresa_cliente', 'pedido', 'generada_por'
    ).prefetch_related('items')
    
    # Paginación
    page_size = int(request.query_params.get('page_size', 20))
    page = int(request.query_params.get('page', 1))
    start = (page - 1) * page_size
    end = start + page_size
    
    total = facturas.count()
    facturas_paginadas = facturas[start:end]
    
    serializer = FacturaListSerializer(facturas_paginadas, many=True)
    
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
def detalle_factura(request, pk):
    """
    Obtiene el detalle completo de una factura
    """
    user = request.user
    
    # Filtrar según permisos
    if user.es_usuario_lambda():
        factura = get_object_or_404(Factura, pk=pk, deleted_at__isnull=True)
    elif hasattr(user, 'empresa') and user.empresa:
        factura = get_object_or_404(
            Factura, 
            pk=pk, 
            empresa_cliente=user.empresa,
            deleted_at__isnull=True
        )
    else:
        return Response(
            {"error": "No tienes acceso a esta factura"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = FacturaSerializer(factura)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_factura(request):
    """
    Genera una factura desde un pedido pagado (HU24)
    Solo usuarios Lambda pueden generar facturas
    """
    user = request.user
    
    if not user.es_usuario_lambda():
        return Response(
            {"error": "Solo usuarios de Lambda pueden generar facturas"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = GenerarFacturaSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Obtener pedido
        pedido = get_object_or_404(
            Pedido, 
            id=serializer.validated_data['pedido_id'],
            deleted_at__isnull=True
        )
        
        # Generar factura
        factura = facturacion_service.generar_factura_desde_pedido(
            pedido=pedido,
            usuario_generador=user,
            observaciones=serializer.validated_data.get('observaciones', ''),
            enviar_email=serializer.validated_data.get('enviar_email', True)
        )
        
        logger.info(f"✅ Factura {factura.numero_factura} generada por {user.email}")
        
        return Response(
            {
                "mensaje": "Factura generada exitosamente",
                "factura": FacturaSerializer(factura).data
            },
            status=status.HTTP_201_CREATED
        )
    
    except Exception as e:
        logger.error(f"❌ Error generando factura: {str(e)}")
        return Response(
            {"error": f"Error generando factura: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def descargar_factura_pdf(request, pk):
    """
    Descarga el PDF de una factura
    """
    user = request.user
    
    # Filtrar según permisos
    if user.es_usuario_lambda():
        factura = get_object_or_404(Factura, pk=pk, deleted_at__isnull=True)
    elif hasattr(user, 'empresa') and user.empresa:
        factura = get_object_or_404(
            Factura, 
            pk=pk, 
            empresa_cliente=user.empresa,
            deleted_at__isnull=True
        )
    else:
        return Response(
            {"error": "No tienes acceso a esta factura"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not factura.archivo_pdf:
        return Response(
            {"error": "La factura no tiene PDF generado"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        response = FileResponse(
            factura.archivo_pdf.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="factura_{factura.numero_factura}.pdf"'
        return response
    
    except Exception as e:
        logger.error(f"Error descargando PDF de factura {factura.numero_factura}: {str(e)}")
        return Response(
            {"error": "Error descargando archivo PDF"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# GENERACIÓN DE REPORTES (HU25)
# =============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_reporte(request):
    """
    Genera reportes personalizados (HU25)
    Solo usuarios Lambda pueden generar reportes
    """
    user = request.user
    
    if not user.es_usuario_lambda():
        return Response(
            {"error": "Solo usuarios de Lambda pueden generar reportes"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = GenerarReporteSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Crear registro de reporte
        reporte = ReportePeriodico.objects.create(
            nombre=serializer.validated_data['nombre'],
            tipo=serializer.validated_data['tipo'],
            formato=serializer.validated_data['formato'],
            fecha_inicio=serializer.validated_data['fecha_inicio'],
            fecha_fin=serializer.validated_data['fecha_fin'],
            empresa_filtro_id=serializer.validated_data.get('empresa_filtro'),
            generado_por=user
        )
        
        # Generar contenido según tipo
        contenido, stats = _generar_contenido_reporte(reporte)
        
        # Actualizar estadísticas
        reporte.total_registros = stats.get('total_registros', 0)
        reporte.monto_total = stats.get('monto_total', 0)
        reporte.resumen_json = stats
        reporte.save()
        
        logger.info(f"✅ Reporte {reporte.nombre} generado por {user.email}")
        
        return Response(
            {
                "mensaje": "Reporte generado exitosamente",
                "reporte": ReportePeriodicoSerializer(reporte).data
            },
            status=status.HTTP_201_CREATED
        )
    
    except Exception as e:
        logger.error(f"❌ Error generando reporte: {str(e)}")
        return Response(
            {"error": f"Error generando reporte: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_reportes(request):
    """
    Dashboard con estadísticas y gráficos para reportes (HU26)
    """
    user = request.user
    
    if not user.es_usuario_lambda():
        return Response(
            {"error": "Solo usuarios de Lambda pueden ver el dashboard"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Fecha base para cálculos
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        fin_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Estadísticas generales
        stats = {
            'total_facturas_mes': Factura.objects.filter(
                fecha_emision__range=[inicio_mes, fin_mes]
            ).count(),
            
            'total_facturado_mes': Factura.objects.filter(
                fecha_emision__range=[inicio_mes, fin_mes],
                estado__in=[Factura.EstadoFactura.ENVIADA, Factura.EstadoFactura.PAGADA]
            ).aggregate(total=Sum('total'))['total'] or 0,
            
            'facturas_pendientes': Factura.objects.filter(
                estado__in=[Factura.EstadoFactura.GENERADA, Factura.EstadoFactura.ENVIADA]
            ).count(),
            
            'reportes_programados': ConfiguracionReporte.objects.filter(
                activo=True
            ).count(),
            
            'ultima_actualizacion': timezone.now(),
        }
        
        # Ventas últimos 6 meses
        ventas_meses = []
        for i in range(6):
            mes_inicio = (hoy.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            mes_fin = (mes_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            total_mes = Factura.objects.filter(
                fecha_emision__range=[mes_inicio, mes_fin]
            ).aggregate(total=Sum('total'))['total'] or 0
            
            ventas_meses.append({
                'mes': mes_inicio.strftime('%Y-%m'),
                'nombre': mes_inicio.strftime('%B %Y'),
                'total': float(total_mes)
            })
        
        stats['ventas_ultimos_meses'] = list(reversed(ventas_meses))
        
        # Top 5 empresas por facturación
        empresas_top = list(
            Factura.objects.filter(
                fecha_emision__range=[inicio_mes, fin_mes]
            ).values(
                'empresa_cliente__nombre'
            ).annotate(
                total_facturado=Sum('total'),
                cantidad_facturas=Count('id')
            ).order_by('-total_facturado')[:5]
        )
        
        stats['empresas_top'] = empresas_top
        
        # Productos más vendidos (desde pedidos)
        productos_vendidos = list(
            Pedido.objects.filter(
                created_at__date__range=[inicio_mes, fin_mes],
                estado=Pedido.EstadoPedido.FACTURADO
            ).values(
                'items__producto__nombre'
            ).annotate(
                total_vendido=Sum('items__cantidad_final'),
                ingresos=Sum('items__cantidad_final') * Sum('items__precio_unitario_final')
            ).order_by('-total_vendido')[:10]
        )
        
        stats['productos_mas_vendidos'] = productos_vendidos
        
        serializer = DashboardSerializer(data=stats)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"❌ Error generando dashboard: {str(e)}")
        return Response(
            {"error": f"Error generando dashboard: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================
# FUNCIONES AUXILIARES
# =============================================

def _generar_contenido_reporte(reporte):
    """Genera contenido específico según tipo de reporte"""
    
    if reporte.tipo == 'ventas_periodo':
        return _generar_reporte_ventas(reporte)
    elif reporte.tipo == 'empresas_ranking':
        return _generar_reporte_empresas(reporte)
    elif reporte.tipo == 'pagos_pendientes':
        return _generar_reporte_pagos_pendientes(reporte)
    else:
        raise ValueError(f"Tipo de reporte no soportado: {reporte.tipo}")


def _generar_reporte_ventas(reporte):
    """Genera reporte de ventas por período"""
    
    # Obtener facturas del período
    facturas = Factura.objects.filter(
        fecha_emision__range=[reporte.fecha_inicio, reporte.fecha_fin],
        deleted_at__isnull=True
    )
    
    if reporte.empresa_filtro:
        facturas = facturas.filter(empresa_cliente=reporte.empresa_filtro)
    
    # Generar archivo según formato
    if reporte.formato == 'excel':
        contenido = excel_generator.generar_reporte_ventas_excel(
            facturas, reporte.fecha_inicio, reporte.fecha_fin
        )
    else:
        # PDF por defecto
        contenido = pdf_generator.generar_reporte_ventas_pdf(
            facturas, reporte.fecha_inicio, reporte.fecha_fin
        )
    
    # Estadísticas
    stats = {
        'total_registros': facturas.count(),
        'monto_total': facturas.aggregate(total=Sum('total'))['total'] or 0,
        'promedio_factura': facturas.aggregate(promedio=Avg('total'))['promedio'] or 0,
        'empresas_diferentes': facturas.values('empresa_cliente').distinct().count()
    }
    
    return contenido, stats


def _generar_reporte_empresas(reporte):
    """Genera ranking de empresas por facturación"""
    from django.db.models import Sum, Count
    
    # Obtener facturas del período
    facturas = Factura.objects.filter(
        fecha_emision__range=[reporte.fecha_inicio, reporte.fecha_fin],
        deleted_at__isnull=True
    )
    
    if reporte.empresa_filtro:
        facturas = facturas.filter(empresa_cliente=reporte.empresa_filtro)
    
    # Agrupar por empresa
    empresas_data = facturas.values(
        'empresa_cliente__nombre'
    ).annotate(
        total_facturado=Sum('total'),
        cantidad_facturas=Count('id')
    ).order_by('-total_facturado')
    
    # Generar contenido básico
    contenido = f"Reporte de Empresas - {reporte.fecha_inicio} a {reporte.fecha_fin}\n"
    contenido += f"Total empresas: {empresas_data.count()}\n"
    
    stats = {
        'total_registros': empresas_data.count(),
        'monto_total': sum(item['total_facturado'] for item in empresas_data),
        'empresas_activas': empresas_data.count()
    }
    
    return contenido.encode('utf-8'), stats


def _generar_reporte_pagos_pendientes(reporte):
    """Genera reporte de pagos pendientes"""
    from Pedidos.models import Pedido
    from django.db.models import Sum
    
    # Buscar pedidos con pagos pendientes
    pedidos_pendientes = Pedido.objects.filter(
        estado__in=[
            Pedido.EstadoPedido.PENDIENTE_PAGO,
            Pedido.EstadoPedido.PAGO_VENCIDO
        ],
        created_at__date__range=[reporte.fecha_inicio, reporte.fecha_fin],
        deleted_at__isnull=True
    )
    
    if reporte.empresa_filtro:
        pedidos_pendientes = pedidos_pendientes.filter(empresa_cliente=reporte.empresa_filtro)
    
    # Generar contenido básico
    contenido = f"Reporte de Pagos Pendientes - {reporte.fecha_inicio} a {reporte.fecha_fin}\n"
    contenido += f"Total pedidos pendientes: {pedidos_pendientes.count()}\n"
    
    stats = {
        'total_registros': pedidos_pendientes.count(),
        'monto_total': pedidos_pendientes.aggregate(total=Sum('monto_final'))['total'] or 0,
        'pedidos_vencidos': pedidos_pendientes.filter(estado=Pedido.EstadoPedido.PAGO_VENCIDO).count()
    }
    
    return contenido.encode('utf-8'), stats
