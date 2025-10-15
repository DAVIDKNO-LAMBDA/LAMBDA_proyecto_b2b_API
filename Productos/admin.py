from django.contrib import admin
# Importamos el nuevo modelo MovimientoInventario
from .models import Producto, MovimientoInventario

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # Mostramos los nuevos campos de stock
    list_display = ('nombre', 'precio', 'stock_fisico', 'stock_reservado', 'stock_disponible', 'umbral_minimo', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado',)
    ordering = ('nombre',)
    # Hacemos que los campos de stock no se puedan editar directamente
    readonly_fields = ('stock_fisico', 'stock_reservado', 'stock_disponible')

# Registramos el nuevo modelo MovimientoInventario
@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'cantidad', 'fecha_creacion', 'usuario_responsable')
    list_filter = ('tipo', 'producto')
    # Hacemos que los campos no sean editables después de la creación
    readonly_fields = ('producto', 'tipo', 'cantidad', 'descripcion', 'usuario_responsable')
