from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Factura, ItemFactura, ReportePeriodico, ConfiguracionReporte


class ItemFacturaInline(admin.TabularInline):
    model = ItemFactura
    extra = 0
    readonly_fields = ['subtotal']
    fields = ['descripcion', 'cantidad', 'precio_unitario', 'subtotal']


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_factura', 
        'empresa_cliente', 
        'tipo', 
        'estado_badge',
        'total', 
        'fecha_emision',
        'acciones'
    ]
    list_filter = [
        'tipo', 
        'estado', 
        'fecha_emision',
        'empresa_cliente'
    ]
    search_fields = [
        'numero_factura', 
        'empresa_cliente__nombre',
        'pedido__numero_pedido'
    ]
    readonly_fields = [
        'numero_factura', 
        'subtotal', 
        'impuestos', 
        'total',
        'fecha_emision'
    ]
    
    fieldsets = [
        ('Información Básica', {
            'fields': ['numero_factura', 'tipo', 'estado', 'pedido', 'empresa_cliente']
        }),
        ('Información Financiera', {
            'fields': ['subtotal', 'descuento', 'impuestos', 'total']
        }),
        ('Fechas', {
            'fields': ['fecha_emision', 'fecha_vencimiento', 'fecha_envio']
        }),
        ('Archivos', {
            'fields': ['archivo_pdf']
        }),
        ('Información Adicional', {
            'fields': ['observaciones', 'terminos_condiciones', 'generada_por'],
            'classes': ['collapse']
        })
    ]
    
    inlines = [ItemFacturaInline]
    
    def estado_badge(self, obj):
        colors = {
            'borrador': 'gray',
            'generada': 'blue',
            'enviada': 'orange',
            'pagada': 'green',
            'anulada': 'red'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def acciones(self, obj):
        if obj.archivo_pdf:
            return format_html(
                '<a href="{}" target="_blank" style="background-color: #28a745; color: white; padding: 2px 8px; text-decoration: none; border-radius: 3px;">📄 Ver PDF</a>',
                obj.archivo_pdf.url
            )
        return format_html(
            '<span style="color: #6c757d;">Sin PDF</span>'
        )
    acciones.short_description = 'Acciones'


@admin.register(ReportePeriodico)
class ReportePeriodicoAdmin(admin.ModelAdmin):
    list_display = [
        'nombre',
        'tipo',
        'formato_badge',
        'periodo',
        'total_registros',
        'monto_total',
        'fecha_generacion',
        'acciones'
    ]
    list_filter = [
        'tipo',
        'formato',
        'fecha_generacion',
        'empresa_filtro'
    ]
    search_fields = [
        'nombre',
        'empresa_filtro__nombre'
    ]
    readonly_fields = [
        'fecha_generacion',
        'total_registros',
        'monto_total'
    ]
    
    fieldsets = [
        ('Información Básica', {
            'fields': ['nombre', 'tipo', 'formato']
        }),
        ('Período y Filtros', {
            'fields': ['fecha_inicio', 'fecha_fin', 'empresa_filtro']
        }),
        ('Resultados', {
            'fields': ['archivo_generado', 'total_registros', 'monto_total', 'resumen_json']
        }),
        ('Metadatos', {
            'fields': ['generado_por', 'fecha_generacion'],
            'classes': ['collapse']
        })
    ]
    
    def formato_badge(self, obj):
        colors = {
            'pdf': 'red',
            'excel': 'green',
            'csv': 'blue'
        }
        color = colors.get(obj.formato, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.formato.upper()
        )
    formato_badge.short_description = 'Formato'
    
    def periodo(self, obj):
        return f"{obj.fecha_inicio} - {obj.fecha_fin}"
    periodo.short_description = 'Período'
    
    def acciones(self, obj):
        if obj.archivo_generado:
            return format_html(
                '<a href="{}" target="_blank" style="background-color: #007bff; color: white; padding: 2px 8px; text-decoration: none; border-radius: 3px;">📊 Descargar</a>',
                obj.archivo_generado.url
            )
        return format_html(
            '<span style="color: #6c757d;">Sin archivo</span>'
        )
    acciones.short_description = 'Acciones'


@admin.register(ConfiguracionReporte)
class ConfiguracionReporteAdmin(admin.ModelAdmin):
    list_display = [
        'nombre',
        'tipo_reporte',
        'frecuencia_badge',
        'activo_badge',
        'proxima_ejecucion',
        'ultima_ejecucion'
    ]
    list_filter = [
        'tipo_reporte',
        'frecuencia',
        'activo'
    ]
    search_fields = ['nombre']
    
    fieldsets = [
        ('Configuración Básica', {
            'fields': ['nombre', 'tipo_reporte', 'frecuencia', 'activo']
        }),
        ('Distribución', {
            'fields': ['emails_destino']
        }),
        ('Programación', {
            'fields': ['proxima_ejecucion', 'ultima_ejecucion']
        })
    ]
    
    def frecuencia_badge(self, obj):
        colors = {
            'diaria': 'green',
            'semanal': 'blue',
            'mensual': 'orange',
            'trimestral': 'purple',
            'anual': 'red'
        }
        color = colors.get(obj.frecuencia, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_frecuencia_display()
        )
    frecuencia_badge.short_description = 'Frecuencia'
    
    def activo_badge(self, obj):
        if obj.activo:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 3px;">✅ Activo</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 3px;">❌ Inactivo</span>'
            )
    activo_badge.short_description = 'Estado'
