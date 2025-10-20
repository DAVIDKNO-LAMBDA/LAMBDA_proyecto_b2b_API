from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import Pedido, ItemPedido, HistorialValidacionPedido, RecordatorioPago
from Solicitudes.models import Solicitud, ItemSolicitud
from Productos.models import Producto, MovimientoInventario
from Usuarios.models import Usuario
from Empresas.models import Empresa


class ItemPedidoSerializer(serializers.ModelSerializer):
    """Serializer para items de pedido"""
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    subtotal_solicitud = serializers.SerializerMethodField()
    subtotal_final = serializers.SerializerMethodField()
    stock_disponible = serializers.IntegerField(source='producto.stock_disponible', read_only=True)
    
    class Meta:
        model = ItemPedido
        fields = [
            'id', 'producto', 'producto_nombre', 'cantidad_solicitada',
            'cantidad_aprobada_cliente', 'cantidad_final', 
            'precio_unitario_solicitud', 'precio_unitario_final',
            'subtotal_solicitud', 'subtotal_final',
            'stock_disponible', 'observaciones_lambda', 'stock_reservado'
        ]
    
    def get_subtotal_solicitud(self, obj):
        return float(obj.cantidad_solicitada * obj.precio_unitario_solicitud)
    
    def get_subtotal_final(self, obj):
        cantidad = obj.cantidad_final or obj.cantidad_aprobada_cliente
        return float(cantidad * obj.precio_unitario_final)


class PedidoSerializer(serializers.ModelSerializer):
    """Serializer completo para pedidos"""
    items = ItemPedidoSerializer(many=True, read_only=True)
    empresa_cliente_nombre = serializers.CharField(source='empresa_cliente.nombre', read_only=True)
    usuario_solicitante_nombre = serializers.CharField(source='usuario_solicitante.nombre_completo', read_only=True)
    
    # Validadores Lambda
    validador_abastecimiento_lambda_nombre = serializers.CharField(
        source='validador_abastecimiento_lambda.nombre_completo', 
        read_only=True
    )
    validador_finanzas_lambda_nombre = serializers.CharField(
        source='validador_finanzas_lambda.nombre_completo', 
        read_only=True
    )
    
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    modalidad_pago_display = serializers.CharField(source='get_modalidad_pago_display', read_only=True)
    
    # Campos calculados
    dias_vencimiento = serializers.SerializerMethodField()
    esta_vencido = serializers.SerializerMethodField()
    puede_cancelarse = serializers.SerializerMethodField()
    
    class Meta:
        model = Pedido
        fields = [
            'id', 'numero_pedido', 'solicitud_origen', 'empresa_cliente', 'empresa_cliente_nombre',
            'usuario_solicitante', 'usuario_solicitante_nombre', 'estado', 'estado_display',
            'observaciones_cliente', 'items',
            
            # Validación Lambda - Abastecimiento
            'validador_abastecimiento_lambda', 'validador_abastecimiento_lambda_nombre',
            'fecha_validacion_abastecimiento_lambda', 'comentario_abastecimiento_lambda',
            'stock_confirmado_lambda',
            
            # Validación Lambda - Finanzas
            'validador_finanzas_lambda', 'validador_finanzas_lambda_nombre',
            'fecha_validacion_finanzas_lambda', 'comentario_finanzas_lambda',
            'credito_aprobado_lambda',
            
            # Condiciones de Pago
            'modalidad_pago', 'modalidad_pago_display', 'fecha_limite_pago',
            'monto_total', 'descuento_aplicado', 'monto_final',
            'dias_vencimiento', 'esta_vencido', 'puede_cancelarse',
            
            # Gestión de Pago
            'fecha_pago', 'comprobante_pago', 'metodo_pago',
            
            # Despacho
            'fecha_despacho', 'numero_guia', 'transportadora',
            'fecha_entrega_estimada', 'fecha_entrega_real',
            
            # Facturación
            'numero_factura', 'fecha_factura', 'factura_enviada',
            
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'numero_pedido', 'solicitud_origen', 'empresa_cliente', 'usuario_solicitante',
            'monto_total', 'monto_final', 'created_at', 'updated_at'
        ]
    
    def get_dias_vencimiento(self, obj):
        if obj.fecha_limite_pago:
            delta = obj.fecha_limite_pago - timezone.now().date()
            return delta.days
        return None
    
    def get_esta_vencido(self, obj):
        return obj.esta_vencido()
    
    def get_puede_cancelarse(self, obj):
        return obj.puede_cancelarse()


class ConvertirSolicitudSerializer(serializers.Serializer):
    """Serializer para convertir solicitud aprobada a pedido (HU14)"""
    solicitud_id = serializers.IntegerField()
    observaciones_cliente = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_solicitud_id(self, value):
        """Validar que la solicitud exista y esté aprobada"""
        try:
            solicitud = Solicitud.objects.get(id=value, deleted_at__isnull=True)
        except Solicitud.DoesNotExist:
            raise serializers.ValidationError("La solicitud no existe")
        
        # Verificar que esté aprobada
        if solicitud.estado != Solicitud.EstadoSolicitud.APROBADA:
            raise serializers.ValidationError(
                f"La solicitud debe estar APROBADA. Estado actual: {solicitud.get_estado_display()}"
            )
        
        # Verificar que no tenga pedido ya creado
        if hasattr(solicitud, 'pedido'):
            raise serializers.ValidationError(
                f"La solicitud ya tiene un pedido asociado: {solicitud.pedido.numero_pedido}"
            )
        
        return value
    
    def validate(self, data):
        """Validaciones adicionales"""
        solicitud = Solicitud.objects.get(id=data['solicitud_id'])
        
        # Validar que todos los productos tengan stock en Lambda
        productos_sin_stock = []
        for item in solicitud.items.all():
            if item.producto.stock_disponible < item.cantidad_aprobada:
                productos_sin_stock.append({
                    'producto': item.producto.nombre,
                    'solicitado': item.cantidad_aprobada,
                    'disponible': item.producto.stock_disponible
                })
        
        if productos_sin_stock:
            raise serializers.ValidationError({
                'stock': f"Productos sin stock suficiente en Lambda: {productos_sin_stock}"
            })
        
        return data
    
    def create(self, validated_data):
        """Crear pedido desde solicitud aprobada"""
        solicitud = Solicitud.objects.get(id=validated_data['solicitud_id'])
        
        with transaction.atomic():
            # Crear pedido - ESTADO INICIAL: Pendiente validación Lambda general
            pedido = Pedido.objects.create(
                solicitud_origen=solicitud,
                empresa_cliente=solicitud.empresa,
                usuario_solicitante=solicitud.solicitante,
                observaciones_cliente=validated_data.get('observaciones_cliente', ''),
                estado=Pedido.EstadoPedido.PENDIENTE_VALIDACION_LAMBDA
            )
            
            # Crear items del pedido
            for item_solicitud in solicitud.items.all():
                ItemPedido.objects.create(
                    pedido=pedido,
                    producto=item_solicitud.producto,
                    cantidad_solicitada=item_solicitud.cantidad,
                    cantidad_aprobada_cliente=item_solicitud.cantidad_aprobada,
                    precio_unitario_solicitud=item_solicitud.precio_unitario,
                    precio_unitario_final=item_solicitud.producto.precio  # Precio actual
                )
            
            # Marcar solicitud como convertida
            solicitud.estado = Solicitud.EstadoSolicitud.CONVERTIDA_PEDIDO
            solicitud.save(update_fields=['estado', 'updated_at'])
            
            return pedido


class ValidarAbastecimientoLambdaSerializer(serializers.Serializer):
    """Serializer para validación de abastecimiento en Lambda"""
    
    class Accion(serializers.ChoiceField):
        def __init__(self, **kwargs):
            kwargs['choices'] = ['aprobar', 'rechazar', 'modificar']
            super().__init__(**kwargs)
    
    accion = Accion()
    comentario = serializers.CharField(required=True)
    items_modificados = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Lista de items con cantidades y precios modificados"
    )
    
    def validate(self, data):
        accion = data.get('accion')
        items_modificados = data.get('items_modificados', [])
        
        if accion == 'modificar' and not items_modificados:
            raise serializers.ValidationError({
                'items_modificados': 'Debe especificar los items modificados'
            })
        
        # Validar estructura de items modificados
        if items_modificados:
            for item in items_modificados:
                required_fields = ['id', 'cantidad_final', 'precio_unitario_final']
                for field in required_fields:
                    if field not in item:
                        raise serializers.ValidationError({
                            'items_modificados': f'Cada item debe tener: {required_fields}'
                        })
        
        return data


class ValidarFinanzasLambdaSerializer(serializers.Serializer):
    """Serializer para validación financiera en Lambda"""
    
    class Accion(serializers.ChoiceField):
        def __init__(self, **kwargs):
            kwargs['choices'] = ['aprobar', 'rechazar']
            super().__init__(**kwargs)
    
    accion = Accion()
    comentario = serializers.CharField(required=True)
    modalidad_pago = serializers.ChoiceField(
        choices=Pedido.ModalidadPago.choices,
        required=False
    )
    fecha_limite_pago = serializers.DateField(required=False)
    descuento_aplicado = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        required=False, 
        min_value=0, 
        max_value=100
    )
    
    def validate(self, data):
        accion = data.get('accion')
        modalidad_pago = data.get('modalidad_pago')
        fecha_limite_pago = data.get('fecha_limite_pago')
        
        if accion == 'aprobar':
            # Validar datos requeridos para aprobación
            if not modalidad_pago:
                raise serializers.ValidationError({
                    'modalidad_pago': 'Debe especificar modalidad de pago al aprobar'
                })
            
            # Si es diferido, debe tener fecha límite
            if modalidad_pago == Pedido.ModalidadPago.DIFERIDO:
                if not fecha_limite_pago:
                    raise serializers.ValidationError({
                        'fecha_limite_pago': 'Pago diferido requiere fecha límite'
                    })
                
                # Validar que la fecha no sea pasada
                if fecha_limite_pago <= timezone.now().date():
                    raise serializers.ValidationError({
                        'fecha_limite_pago': 'La fecha límite debe ser futura'
                    })
                
                # Validar límite máximo (2 meses)
                max_fecha = timezone.now().date() + timedelta(days=60)
                if fecha_limite_pago > max_fecha:
                    raise serializers.ValidationError({
                        'fecha_limite_pago': 'Fecha límite no puede ser mayor a 2 meses'
                    })
                
                # Validar que la empresa esté autorizada para pago diferido
                pedido = self.context.get('pedido')
                if pedido and not pedido.empresa_cliente.pagar_despues:
                    raise serializers.ValidationError({
                        'modalidad_pago': 'La empresa no está autorizada para pago diferido'
                    })
        
        return data


class GestionarPagoSerializer(serializers.Serializer):
    """Serializer para gestionar pagos (HU16) - MEJORADO"""
    
    ACCIONES_CHOICES = [
        ('confirmar_pago', 'Confirmar Pago'),
        ('marcar_vencido', 'Marcar como Vencido'),
        ('extender_plazo', 'Extender Plazo'),  # NUEVO
    ]
    
    METODOS_PAGO_CHOICES = [
        ('transferencia', 'Transferencia Bancaria'),
        ('pse', 'PSE'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('efectivo', 'Efectivo'),
        ('cheque', 'Cheque'),
    ]
    
    accion = serializers.ChoiceField(choices=ACCIONES_CHOICES)
    
    # Campos para confirmar pago
    comprobante_pago = serializers.CharField(max_length=255, required=False)
    metodo_pago = serializers.ChoiceField(choices=METODOS_PAGO_CHOICES, required=False)
    monto_pago = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    fecha_pago = serializers.DateTimeField(required=False)
    observaciones = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    # Campos para extender plazo
    nueva_fecha_limite = serializers.DateField(required=False)
    motivo_extension = serializers.CharField(max_length=500, required=False)
    
    def validate(self, data):
        accion = data.get('accion')
        
        if accion == 'confirmar_pago':
            required_fields = ['comprobante_pago', 'metodo_pago', 'monto_pago']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({
                        field: f'Campo requerido para confirmar pago'
                    })
        
        elif accion == 'extender_plazo':
            if not data.get('nueva_fecha_limite'):
                raise serializers.ValidationError({
                    'nueva_fecha_limite': 'Campo requerido para extender plazo'
                })
            if not data.get('motivo_extension'):
                raise serializers.ValidationError({
                    'motivo_extension': 'Debe especificar motivo de la extensión'
                })
            
            # Validar que la nueva fecha sea futura
            if data['nueva_fecha_limite'] <= timezone.now().date():
                raise serializers.ValidationError({
                    'nueva_fecha_limite': 'La nueva fecha límite debe ser futura'
                })
        
        return data


class HistorialValidacionPedidoSerializer(serializers.ModelSerializer):
    """Serializer para historial de validaciones de pedidos"""
    validador_nombre = serializers.CharField(source='validador.nombre_completo', read_only=True)
    tipo_validacion_display = serializers.CharField(source='get_tipo_validacion_display', read_only=True)
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)
    
    class Meta:
        model = HistorialValidacionPedido
        fields = [
            'id', 'tipo_validacion', 'tipo_validacion_display',
            'accion', 'accion_display', 'validador', 'validador_nombre',
            'comentario', 'datos_anteriores', 'monto_pago', 'metodo_pago',
            'created_at'
        ]


class RecordatorioPagoSerializer(serializers.ModelSerializer):
    """Serializer para recordatorios de pago"""
    pedido_numero = serializers.CharField(source='pedido.numero_pedido', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    dias_restantes = serializers.SerializerMethodField()
    
    class Meta:
        model = RecordatorioPago
        fields = [
            'id', 'pedido', 'pedido_numero', 'tipo', 'tipo_display',
            'fecha_programada', 'fecha_enviado', 'enviado', 'exitoso',
            'email_destinatario', 'asunto', 'error_envio',
            'dias_restantes', 'created_at'
        ]
        read_only_fields = ['fecha_enviado', 'enviado', 'exitoso', 'error_envio']
    
    def get_dias_restantes(self, obj):
        if obj.fecha_programada:
            delta = obj.fecha_programada.date() - timezone.now().date()
            return delta.days
        return None


class PedidoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados de pedidos"""
    empresa_cliente_nombre = serializers.CharField(source='empresa_cliente.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    modalidad_pago_display = serializers.CharField(source='get_modalidad_pago_display', read_only=True)
    dias_vencimiento = serializers.SerializerMethodField()
    cantidad_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Pedido
        fields = [
            'id', 'numero_pedido', 'empresa_cliente_nombre', 'estado', 'estado_display',
            'modalidad_pago', 'modalidad_pago_display', 'monto_final',
            'fecha_limite_pago', 'dias_vencimiento', 'cantidad_items',
            'created_at'
        ]
    
    def get_dias_vencimiento(self, obj):
        if obj.fecha_limite_pago:
            delta = obj.fecha_limite_pago - timezone.now().date()
            return delta.days
        return None
    
    def get_cantidad_items(self, obj):
        return obj.items.count()