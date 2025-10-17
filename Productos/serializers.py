from rest_framework import serializers
from .models import Producto, MovimientoInventario


class ProductoSerializer(serializers.ModelSerializer):
    """Serializer completo para Producto"""
    stock_disponible = serializers.ReadOnlyField()
    stock_bajo_minimo = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio',
            'stock_fisico', 'stock_reservado', 'stock_disponible',
            'umbral_minimo', 'estado', 'stock_bajo_minimo',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['stock_disponible', 'created_at', 'updated_at']
    
    def get_stock_bajo_minimo(self, obj):
        """Indica si el stock está bajo el mínimo"""
        return obj.stock_disponible < obj.umbral_minimo


class ProductoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    stock_disponible = serializers.ReadOnlyField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'precio', 'stock_disponible',
            'umbral_minimo', 'estado'
        ]


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    """Serializer completo para MovimientoInventario"""
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario_responsable.nombre_completo', read_only=True)
    
    class Meta:
        model = MovimientoInventario
        fields = [
            'id', 'producto', 'producto_nombre', 'tipo', 'tipo_display',
            'cantidad', 'descripcion', 'solicitud', 'pedido',
            'usuario_responsable', 'usuario_nombre',
            'created_at'
        ]
        read_only_fields = ['created_at']


class CrearMovimientoSerializer(serializers.ModelSerializer):
    """Serializer para crear movimientos manualmente"""
    
    class Meta:
        model = MovimientoInventario
        fields = ['producto', 'tipo', 'cantidad', 'descripcion']
    
    def validate(self, data):
        producto = data.get('producto')
        tipo = data.get('tipo')
        cantidad = data.get('cantidad')
        
        # Validar producto activo
        if not producto.estado:
            raise serializers.ValidationError({
                'producto': 'El producto está inactivo'
            })
        
        # Validar stock suficiente para salidas y reservas
        if tipo in ['SALIDA', 'RESERVA']:
            if producto.stock_disponible < cantidad:
                raise serializers.ValidationError({
                    'cantidad': f'Stock insuficiente. Disponible: {producto.stock_disponible}'
                })
        
        # Validar liberación
        if tipo == 'LIBERACION':
            if producto.stock_reservado < cantidad:
                raise serializers.ValidationError({
                    'cantidad': f'No puede liberar más de lo reservado. Reservado: {producto.stock_reservado}'
                })
        
        return data
    
    def create(self, validated_data):
        # El usuario responsable viene del request
        validated_data['usuario_responsable'] = self.context['request'].user
        return super().create(validated_data)


class ReservarStockSerializer(serializers.Serializer):
    """Serializer para reservar stock"""
    cantidad = serializers.IntegerField(min_value=1)
    solicitud_id = serializers.IntegerField(required=False)
    
    def validate_cantidad(self, value):
        producto = self.context['producto']
        if producto.stock_disponible < value:
            raise serializers.ValidationError(
                f'Stock insuficiente. Disponible: {producto.stock_disponible}'
            )
        return value


class LiberarStockSerializer(serializers.Serializer):
    """Serializer para liberar stock reservado"""
    cantidad = serializers.IntegerField(min_value=1)
    
    def validate_cantidad(self, value):
        producto = self.context['producto']
        if producto.stock_reservado < value:
            raise serializers.ValidationError(
                f'No puede liberar más de lo reservado. Reservado: {producto.stock_reservado}'
            )
        return value
