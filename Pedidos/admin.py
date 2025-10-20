from django.contrib import admin
from .models import Pedido, ItemPedido, HistorialValidacionPedido, RecordatorioPago


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_pedido', 'empresa_cliente', 'usuario_solicitante', 'estado',
        'modalidad_pago', 'monto_final', 'fecha_limite_pago', 'created_at'
    ]
    list_filter = [
        'estado', 'modalidad_pago', 'stock_confirmado_lambda', 
        'credito_aprobado_lambda', 'factura_enviada', 'created_at'
    ]
    search_fields = [
        'numero_pedido', 'empresa_cliente__nombre', 'usuario_solicitante__email',
        'numero_factura', 'comprobante_pago'
    ]
    readonly_fields = [
        'numero_pedido', 'monto_total', 'monto_final', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'numero_pedido', 'solicitud_origen', 'empresa_cliente', 
                'usuario_solicitante', 'estado', 'observaciones_cliente'
            )
        }),
        ('Validación Lambda - Abastecimiento', {
            'fields': (
                'validador_abastecimiento_lambda', 'fecha_validacion_abastecimiento_lambda',
                'comentario_abastecimiento_lambda', 'stock_confirmado_lambda'
            )
        }),
        ('Validación Lambda - Finanzas', {
            'fields': (
                'validador_finanzas_lambda', 'fecha_validacion_finanzas_lambda',
                'comentario_finanzas_lambda', 'credito_aprobado_lambda'
            )
        }),
        ('Condiciones de Pago', {
            'fields': (
                'modalidad_pago', 'fecha_limite_pago', 'monto_total', 
                'descuento_aplicado', 'monto_final'
            )
        }),
        ('Gestión de Pago', {
            'fields': (
                'fecha_pago', 'comprobante_pago', 'metodo_pago'
            )
        }),
        ('Despacho y Entrega', {
            'fields': (
                'fecha_despacho', 'numero_guia', 'transportadora',
                'fecha_entrega_estimada', 'fecha_entrega_real'
            )
        }),
        ('Facturación', {
            'fields': (
                'numero_factura', 'fecha_factura', 'factura_enviada'
            )
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'pedido', 'producto', 'cantidad_solicitada',
        'cantidad_aprobada_cliente', 'cantidad_final', 'precio_unitario_final',
        'stock_reservado'
    ]
    list_filter = ['stock_reservado', 'created_at']
    search_fields = ['pedido__numero_pedido', 'producto__nombre']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(HistorialValidacionPedido)
class HistorialValidacionPedidoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'pedido', 'tipo_validacion', 'accion',
        'validador', 'monto_pago', 'created_at'
    ]
    list_filter = ['tipo_validacion', 'accion', 'created_at']
    search_fields = ['pedido__numero_pedido', 'validador__email']
    readonly_fields = ['created_at']


@admin.register(RecordatorioPago)
class RecordatorioPagoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'pedido', 'tipo', 'fecha_programada',
        'enviado', 'exitoso', 'fecha_enviado'
    ]
    list_filter = ['tipo', 'enviado', 'exitoso', 'fecha_programada']
    search_fields = ['pedido__numero_pedido', 'email_destinatario']
    readonly_fields = ['fecha_enviado']
    
    actions = ['marcar_como_enviado', 'reenviar_recordatorio']
    
    def marcar_como_enviado(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            enviado=True, 
            fecha_enviado=timezone.now(),
            exitoso=True
        )
        self.message_user(request, f'{updated} recordatorios marcados como enviados.')
    marcar_como_enviado.short_description = "Marcar como enviados"
    
    def reenviar_recordatorio(self, request, queryset):
        # Aquí se podría implementar el reenvío automático
        self.message_user(request, f'Funcionalidad de reenvío pendiente de implementación.')
    reenviar_recordatorio.short_description = "Reenviar recordatorios"
