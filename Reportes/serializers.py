from rest_framework import serializers
from django.utils import timezone
from .models import Factura, ItemFactura, ReportePeriodico, ConfiguracionReporte


class ItemFacturaSerializer(serializers.ModelSerializer):
    """Serializer para items de factura"""
    
    class Meta:
        model = ItemFactura
        fields = [
            'id', 'descripcion', 'cantidad', 
            'precio_unitario', 'subtotal'
        ]
        read_only_fields = ['subtotal']


class FacturaSerializer(serializers.ModelSerializer):
    """Serializer completo para facturas"""
    
    items = ItemFacturaSerializer(many=True, read_only=True)
    empresa_cliente_nombre = serializers.CharField(source='empresa_cliente.nombre', read_only=True)
    pedido_numero = serializers.CharField(source='pedido.numero_pedido', read_only=True)
    generada_por_nombre = serializers.CharField(source='generada_por.nombre_completo', read_only=True)
    
    class Meta:
        model = Factura
        fields = [
            'id', 'numero_factura', 'tipo', 'estado',
            'pedido', 'pedido_numero', 
            'empresa_cliente', 'empresa_cliente_nombre',
            'subtotal', 'descuento', 'impuestos', 'total',
            'fecha_emision', 'fecha_vencimiento', 'fecha_envio',
            'archivo_pdf', 'observaciones', 'terminos_condiciones',
            'generada_por', 'generada_por_nombre', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'numero_factura', 'subtotal', 'impuestos', 'total',
            'generada_por', 'created_at', 'updated_at'
        ]


class FacturaListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listas de facturas"""
    
    empresa_cliente_nombre = serializers.CharField(source='empresa_cliente.nombre', read_only=True)
    pedido_numero = serializers.CharField(source='pedido.numero_pedido', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    
    class Meta:
        model = Factura
        fields = [
            'id', 'numero_factura', 'tipo', 'tipo_display',
            'estado', 'estado_display', 'empresa_cliente_nombre',
            'pedido_numero', 'total', 'fecha_emision',
            'fecha_vencimiento', 'archivo_pdf'
        ]


class GenerarFacturaSerializer(serializers.Serializer):
    """Serializer para generar factura desde pedido"""
    
    pedido_id = serializers.IntegerField(help_text="ID del pedido para facturar")
    observaciones = serializers.CharField(
        max_length=500, 
        required=False, 
        allow_blank=True,
        help_text="Observaciones adicionales para la factura"
    )
    terminos_condiciones = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Términos y condiciones específicos"
    )
    enviar_email = serializers.BooleanField(
        default=True,
        help_text="Enviar factura por email al cliente"
    )
    
    def validate_pedido_id(self, value):
        from Pedidos.models import Pedido
        
        try:
            pedido = Pedido.objects.get(
                id=value, 
                deleted_at__isnull=True,
                estado=Pedido.EstadoPedido.PAGO_CONFIRMADO
            )
        except Pedido.DoesNotExist:
            raise serializers.ValidationError(
                "Pedido no encontrado o no está en estado 'Pago Confirmado'"
            )
        
        # Verificar que no tenga factura ya
        if hasattr(pedido, 'factura'):
            raise serializers.ValidationError(
                f"El pedido {pedido.numero_pedido} ya tiene una factura generada"
            )
        
        return value


class ReportePeriodicoSerializer(serializers.ModelSerializer):
    """Serializer para reportes periódicos"""
    
    empresa_filtro_nombre = serializers.CharField(source='empresa_filtro.nombre', read_only=True)
    generado_por_nombre = serializers.CharField(source='generado_por.nombre_completo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    formato_display = serializers.CharField(source='get_formato_display', read_only=True)
    
    class Meta:
        model = ReportePeriodico
        fields = [
            'id', 'nombre', 'tipo', 'tipo_display',
            'formato', 'formato_display', 'fecha_inicio', 'fecha_fin',
            'empresa_filtro', 'empresa_filtro_nombre',
            'archivo_generado', 'generado_por', 'generado_por_nombre',
            'fecha_generacion', 'total_registros', 'monto_total',
            'resumen_json'
        ]
        read_only_fields = [
            'generado_por', 'fecha_generacion', 'total_registros',
            'monto_total', 'resumen_json'
        ]


class GenerarReporteSerializer(serializers.Serializer):
    """Serializer para generar reportes personalizados"""
    
    TIPOS_REPORTE = [
        ('ventas_periodo', 'Ventas por Período'),
        ('empresas_ranking', 'Ranking de Empresas'),
        ('productos_mas_vendidos', 'Productos Más Vendidos'),
        ('pagos_pendientes', 'Pagos Pendientes'),
        ('mora_detallada', 'Análisis de Mora'),
        ('resumen_financiero', 'Resumen Financiero'),
    ]
    
    FORMATOS = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
    ]
    
    nombre = serializers.CharField(
        max_length=255,
        help_text="Nombre descriptivo del reporte"
    )
    
    tipo = serializers.ChoiceField(
        choices=TIPOS_REPORTE,
        help_text="Tipo de reporte a generar"
    )
    
    formato = serializers.ChoiceField(
        choices=FORMATOS,
        default='pdf',
        help_text="Formato de salida del reporte"
    )
    
    fecha_inicio = serializers.DateField(
        help_text="Fecha de inicio del período"
    )
    
    fecha_fin = serializers.DateField(
        help_text="Fecha de fin del período"
    )
    
    empresa_filtro = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID de empresa para filtrar (opcional)"
    )
    
    incluir_graficos = serializers.BooleanField(
        default=True,
        help_text="Incluir gráficos en el reporte PDF"
    )
    
    enviar_email = serializers.BooleanField(
        default=False,
        help_text="Enviar reporte por email"
    )
    
    emails_destino = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True,
        help_text="Lista de emails para envío (si enviar_email=True)"
    )
    
    def validate(self, data):
        # Validar fechas
        if data['fecha_inicio'] > data['fecha_fin']:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha fin debe ser posterior a la fecha inicio'
            })
        
        # Validar que no sea muy antiguo (máximo 2 años)
        if data['fecha_inicio'] < timezone.now().date().replace(year=timezone.now().year - 2):
            raise serializers.ValidationError({
                'fecha_inicio': 'No se pueden generar reportes de más de 2 años de antigüedad'
            })
        
        # Validar empresa si se especifica
        if data.get('empresa_filtro'):
            from Empresas.models import Empresa
            try:
                Empresa.objects.get(id=data['empresa_filtro'], deleted_at__isnull=True)
            except Empresa.DoesNotExist:
                raise serializers.ValidationError({
                    'empresa_filtro': 'Empresa no encontrada'
                })
        
        # Validar emails si se va a enviar
        if data.get('enviar_email') and not data.get('emails_destino'):
            raise serializers.ValidationError({
                'emails_destino': 'Debe especificar emails de destino si enviar_email=True'
            })
        
        return data


class ConfiguracionReporteSerializer(serializers.ModelSerializer):
    """Serializer para configuración de reportes automáticos"""
    
    tipo_reporte_display = serializers.CharField(source='get_tipo_reporte_display', read_only=True)
    frecuencia_display = serializers.CharField(source='get_frecuencia_display', read_only=True)
    
    class Meta:
        model = ConfiguracionReporte
        fields = [
            'id', 'nombre', 'tipo_reporte', 'tipo_reporte_display',
            'frecuencia', 'frecuencia_display', 'activo',
            'emails_destino', 'proxima_ejecucion', 'ultima_ejecucion'
        ]
        read_only_fields = ['ultima_ejecucion']
    
    def validate_emails_destino(self, value):
        """Validar que todos sean emails válidos"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Debe ser una lista de emails")
        
        for email in value:
            if not isinstance(email, str) or '@' not in email:
                raise serializers.ValidationError(f"'{email}' no es un email válido")
        
        return value


class DashboardSerializer(serializers.Serializer):
    """Serializer para datos del dashboard"""
    
    # Estadísticas generales
    total_facturas_mes = serializers.IntegerField()
    total_facturado_mes = serializers.DecimalField(max_digits=15, decimal_places=2)
    facturas_pendientes = serializers.IntegerField()
    
    # Gráficos
    ventas_ultimos_meses = serializers.JSONField()
    empresas_top = serializers.JSONField()
    productos_mas_vendidos = serializers.JSONField()
    
    # Estado del sistema
    reportes_programados = serializers.IntegerField()
    ultima_actualizacion = serializers.DateTimeField()