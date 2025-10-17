from django.contrib import admin
from .models import Producto, MovimientoInventario

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'precio', 'stock_fisico', 'stock_reservado', 'stock_disponible', 'umbral_minimo', 'estado', 'created_at']
    search_fields = ['nombre', 'descripcion']
    list_filter = ['estado', 'created_at']
    ordering = ['-created_at']
    readonly_fields = ['stock_disponible', 'created_at', 'updated_at']
    
    def stock_disponible(self, obj):
        """Muestra el stock disponible calculado"""
        return obj.stock_disponible
    stock_disponible.short_description = 'Stock Disponible'

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    # ✅ CAMPOS CORRECTOS según tu modelo
    list_display = ['id', 'producto', 'tipo', 'cantidad', 'usuario_responsable', 'created_at']
    list_filter = ['tipo', 'created_at']
    search_fields = ['producto__nombre', 'usuario_responsable__email', 'descripcion']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    # Opcional: Mostrar campos importantes en el formulario
    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('producto', 'tipo', 'cantidad', 'descripcion')
        }),
        ('Usuario Responsable', {
            'fields': ('usuario_responsable',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
