from rest_framework import serializers
from .models import Solicitud, ItemSolicitud, HistorialValidacion
from Productos.models import Producto
from Usuarios.models import Usuario
from django.utils import timezone


class ItemSolicitudSerializer(serializers.ModelSerializer):
    """Serializer para items de solicitud"""
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    precio_unitario = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    subtotal = serializers.SerializerMethodField()
    stock_disponible = serializers.IntegerField(source='producto.stock_disponible', read_only=True)
    
    class Meta:
        model = ItemSolicitud
        fields = [
            'id', 'producto', 'producto_nombre', 'cantidad', 
            'cantidad_aprobada', 'precio_unitario', 'subtotal',
            'stock_disponible', 'observaciones'
        ]
    
    def get_subtotal(self, obj):
        cantidad = obj.cantidad_aprobada or obj.cantidad
        return float(cantidad * obj.precio_unitario)
    
    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value


class CrearItemSolicitudSerializer(serializers.ModelSerializer):
    """Serializer para crear items (sin precio, se captura automático)"""
    class Meta:
        model = ItemSolicitud
        fields = ['producto', 'cantidad', 'observaciones']
    
    def validate(self, data):
        producto = data.get('producto')
        cantidad = data.get('cantidad')
        
        # Validar stock disponible
        if producto.stock_disponible < cantidad:
            raise serializers.ValidationError({
                'cantidad': f'Stock insuficiente. Disponible: {producto.stock_disponible}'
            })
        
        return data


class SolicitudSerializer(serializers.ModelSerializer):
    """Serializer completo para solicitudes"""
    items = ItemSolicitudSerializer(many=True, read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    solicitante_nombre = serializers.CharField(source='solicitante.nombre_completo', read_only=True)
    validador_abastecimiento_nombre = serializers.CharField(
        source='validador_abastecimiento.nombre_completo', 
        read_only=True
    )
    validador_finanzas_nombre = serializers.CharField(
        source='validador_finanzas.nombre_completo', 
        read_only=True
    )
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Solicitud
        fields = [
            'id', 'numero_solicitud', 'empresa', 'empresa_nombre',
            'solicitante', 'solicitante_nombre', 'justificacion',
            'estado', 'estado_display', 'monto_total', 'items',
            'validador_abastecimiento', 'validador_abastecimiento_nombre',
            'fecha_validacion_abastecimiento', 'comentario_abastecimiento',
            'stock_validado', 'validador_finanzas', 'validador_finanzas_nombre',
            'fecha_validacion_finanzas', 'comentario_finanzas',
            'presupuesto_aprobado', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'numero_solicitud', 'empresa', 'solicitante', 'monto_total',
            'validador_abastecimiento', 'fecha_validacion_abastecimiento',
            'validador_finanzas', 'fecha_validacion_finanzas'
        ]


class CrearSolicitudSerializer(serializers.Serializer):
    """Serializer para crear solicitud con items (HU10)"""
    justificacion = serializers.CharField(max_length=1000)
    items = CrearItemSolicitudSerializer(many=True)
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos un producto")
        
        # Validar productos duplicados
        productos_ids = [item['producto'].id for item in value]
        if len(productos_ids) != len(set(productos_ids)):
            raise serializers.ValidationError("No puede incluir el mismo producto varias veces")
        
        return value
    
    def validate(self, data):
        # Validar que la empresa tenga validadores
        user = self.context['request'].user
        empresa = user.empresa
        
        from Usuarios.models import Usuario
        
        tiene_validador_finanzas = Usuario.objects.filter(
            empresa=empresa,
            is_active=True,
            deleted_at__isnull=True,
            permisos_personalizados__validador_finanzas=True
        ).exists()
        
        tiene_validador_abastecimiento = Usuario.objects.filter(
            empresa=empresa,
            is_active=True,
            deleted_at__isnull=True,
            permisos_personalizados__validador_abastecimiento=True
        ).exists()
        
        if not tiene_validador_finanzas:
            raise serializers.ValidationError(
                "La empresa debe tener al menos un validador financiero antes de crear solicitudes"
            )
        
        if not tiene_validador_abastecimiento:
            raise serializers.ValidationError(
                "La empresa debe tener al menos un validador de abastecimiento antes de crear solicitudes"
            )
        
        return data
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        
        # Crear solicitud
        solicitud = Solicitud.objects.create(
            empresa=user.empresa,
            solicitante=user,
            justificacion=validated_data['justificacion']
        )
        
        # Crear items
        for item_data in items_data:
            ItemSolicitud.objects.create(
                solicitud=solicitud,
                **item_data
            )
        
        return solicitud


class ValidarAbastecimientoSerializer(serializers.Serializer):
    """Serializer para validación de abastecimiento (HU12)"""
    
    class Accion(serializers.ChoiceField):
        def __init__(self, **kwargs):
            kwargs['choices'] = ['aprobar', 'rechazar', 'modificar']
            super().__init__(**kwargs)
    
    accion = Accion()
    comentario = serializers.CharField(required=True)
    items_modificados = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Lista de items con cantidades modificadas"
    )
    
    def validate(self, data):
        accion = data.get('accion')
        items_modificados = data.get('items_modificados', [])
        
        if accion == 'modificar' and not items_modificados:
            raise serializers.ValidationError({
                'items_modificados': 'Debe especificar los items modificados'
            })
        
        return data


class ValidarFinanzasSerializer(serializers.Serializer):
    """Serializer para validación financiera (HU13)"""
    
    class Accion(serializers.ChoiceField):
        def __init__(self, **kwargs):
            kwargs['choices'] = ['aprobar', 'rechazar']
            super().__init__(**kwargs)
    
    accion = Accion()
    comentario = serializers.CharField(required=True)
    
    def validate_accion(self, value):
        # Validar límite de aprobación del usuario
        user = self.context['request'].user
        solicitud = self.context['solicitud']
        
        if value == 'aprobar':
            limite = user.obtener_limite_aprobacion()
            if solicitud.monto_total > limite:
                raise serializers.ValidationError(
                    f'El monto ${solicitud.monto_total} excede tu límite de aprobación ${limite}'
                )
        
        return value


class HistorialValidacionSerializer(serializers.ModelSerializer):
    """Serializer para historial de validaciones"""
    validador_nombre = serializers.CharField(source='validador.nombre_completo', read_only=True)
    tipo_validacion_display = serializers.CharField(source='get_tipo_validacion_display', read_only=True)
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)
    
    class Meta:
        model = HistorialValidacion
        fields = [
            'id', 'tipo_validacion', 'tipo_validacion_display',
            'accion', 'accion_display', 'validador', 'validador_nombre',
            'comentario', 'datos_anteriores', 'created_at'
        ]