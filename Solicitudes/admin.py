from django.contrib import admin
from .models import Solicitud, ItemSolicitud, HistorialValidacion


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = [
        'numero_solicitud', 'empresa', 'solicitante', 'estado',
        'monto_total', 'stock_validado', 'presupuesto_aprobado', 'created_at'
    ]
    list_filter = ['estado', 'stock_validado', 'presupuesto_aprobado', 'created_at']
    search_fields = ['numero_solicitud', 'empresa__nombre', 'solicitante__email']
    readonly_fields = ['numero_solicitud', 'monto_total', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero_solicitud', 'empresa', 'solicitante', 'justificacion', 'estado')
        }),
        ('Validación Abastecimiento', {
            'fields': (
                'validador_abastecimiento', 'fecha_validacion_abastecimiento',
                'comentario_abastecimiento', 'stock_validado'
            )
        }),
        ('Validación Finanzas', {
            'fields': (
                'validador_finanzas', 'fecha_validacion_finanzas',
                'comentario_finanzas', 'presupuesto_aprobado', 'monto_total'
            )
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemSolicitud)
class ItemSolicitudAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'solicitud', 'producto', 'cantidad',
        'cantidad_aprobada', 'precio_unitario'
    ]
    list_filter = ['solicitud__estado', 'created_at']
    search_fields = ['solicitud__numero_solicitud', 'producto__nombre']
    readonly_fields = ['precio_unitario', 'created_at', 'updated_at']


@admin.register(HistorialValidacion)
class HistorialValidacionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'solicitud', 'tipo_validacion', 'accion',
        'validador', 'created_at'
    ]
    list_filter = ['tipo_validacion', 'accion', 'created_at']
    search_fields = ['solicitud__numero_solicitud', 'validador__email']
    readonly_fields = ['created_at']
