from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Producto, MovimientoInventario
from .serializers import (
    ProductoSerializer,
    ProductoListSerializer,
    MovimientoInventarioSerializer,
    CrearMovimientoSerializer,
    ReservarStockSerializer,
    LiberarStockSerializer
)
import logging

logger = logging.getLogger(__name__)


# =============================================
# VISTAS DE PRODUCTOS
# =============================================

class ProductoListAPIView(generics.ListAPIView):
    """
    Lista todos los productos activos
    GET /api/productos/
    """
    queryset = Producto.objects.filter(estado=True, deleted_at__isnull=True)
    serializer_class = ProductoListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro opcional para productos bajo mínimo
        bajo_minimo = self.request.query_params.get('bajo_minimo')
        if bajo_minimo == 'true':
            return [p for p in queryset if p.stock_disponible < p.umbral_minimo]
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Si es una lista filtrada por bajo_minimo, manejar diferente
        if isinstance(queryset, list):
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        return super().list(request, *args, **kwargs)


class ProductoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Detalle, actualización y eliminación de producto
    GET/PUT/PATCH/DELETE /api/productos/{id}/
    """
    queryset = Producto.objects.filter(deleted_at__isnull=True)
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_destroy(self, instance):
        # Soft delete
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.estado = False
        instance.save()


class ProductoCreateAPIView(generics.CreateAPIView):
    """
    Crear nuevo producto
    POST /api/productos/crear/
    """
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]


# =============================================
# VISTAS DE MOVIMIENTOS
# =============================================

class MovimientoInventarioListAPIView(generics.ListAPIView):
    """
    Lista movimientos de inventario
    GET /api/productos/movimientos/
    """
    queryset = MovimientoInventario.objects.select_related(
        'producto', 'usuario_responsable'
    ).filter(deleted_at__isnull=True)
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        producto_id = self.request.query_params.get('producto')
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        return queryset


class MovimientoInventarioCreateAPIView(generics.CreateAPIView):
    """
    Crear movimiento de inventario manual
    POST /api/productos/movimientos/crear/
    """
    queryset = MovimientoInventario.objects.all()
    serializer_class = CrearMovimientoSerializer
    permission_classes = [IsAuthenticated]


# =============================================
# ENDPOINTS ESPECIALES
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def productos_bajo_minimo(request):
    """
    Lista productos con stock bajo el umbral mínimo
    GET /api/productos/bajo-minimo/
    """
    productos = Producto.objects.filter(
        estado=True,
        deleted_at__isnull=True
    )
    
    productos_criticos = [
        p for p in productos 
        if p.stock_disponible < p.umbral_minimo
    ]
    
    serializer = ProductoListSerializer(productos_criticos, many=True)
    
    return Response({
        "count": len(productos_criticos),
        "productos": serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reservar_stock(request, pk):
    """
    Reserva stock de un producto
    POST /api/productos/{id}/reservar/
    Body: {"cantidad": 10, "solicitud_id": 1}
    """
    producto = get_object_or_404(Producto, pk=pk, deleted_at__isnull=True)
    
    serializer = ReservarStockSerializer(
        data=request.data,
        context={'producto': producto}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            cantidad = serializer.validated_data['cantidad']
            solicitud_id = serializer.validated_data.get('solicitud_id')
            
            # Crear movimiento de reserva
            movimiento = MovimientoInventario.objects.create(
                producto=producto,
                tipo=MovimientoInventario.TipoMovimiento.RESERVA,
                cantidad=cantidad,
                descripcion=f"Reserva para solicitud #{solicitud_id}" if solicitud_id else "Reserva manual",
                usuario_responsable=request.user,
                solicitud_id=solicitud_id
            )
            
            logger.info(f"✅ Stock reservado: {cantidad} uds de {producto.nombre}")
            
            return Response({
                "mensaje": "Stock reservado exitosamente",
                "producto": ProductoSerializer(producto).data,
                "movimiento": MovimientoInventarioSerializer(movimiento).data
            }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"❌ Error reservando stock: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def liberar_stock(request, pk):
    """
    Libera stock reservado de un producto
    POST /api/productos/{id}/liberar/
    Body: {"cantidad": 10}
    """
    producto = get_object_or_404(Producto, pk=pk, deleted_at__isnull=True)
    
    serializer = LiberarStockSerializer(
        data=request.data,
        context={'producto': producto}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            cantidad = serializer.validated_data['cantidad']
            
            # Crear movimiento de liberación
            movimiento = MovimientoInventario.objects.create(
                producto=producto,
                tipo=MovimientoInventario.TipoMovimiento.LIBERACION,
                cantidad=cantidad,
                descripcion="Liberación de stock reservado",
                usuario_responsable=request.user
            )
            
            logger.info(f"✅ Stock liberado: {cantidad} uds de {producto.nombre}")
            
            return Response({
                "mensaje": "Stock liberado exitosamente",
                "producto": ProductoSerializer(producto).data,
                "movimiento": MovimientoInventarioSerializer(movimiento).data
            }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"❌ Error liberando stock: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_producto(request, pk):
    """
    Consulta el stock actual de un producto
    GET /api/productos/{id}/stock/
    """
    producto = get_object_or_404(Producto, pk=pk, deleted_at__isnull=True)
    
    return Response({
        "producto_id": producto.id,
        "nombre": producto.nombre,
        "stock_fisico": producto.stock_fisico,
        "stock_reservado": producto.stock_reservado,
        "stock_disponible": producto.stock_disponible,
        "umbral_minimo": producto.umbral_minimo,
        "alerta_bajo_stock": producto.stock_disponible < producto.umbral_minimo
    })
