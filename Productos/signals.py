from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Producto, MovimientoInventario

@receiver(post_save, sender=MovimientoInventario)
def actualizar_stock_producto(sender, instance, created, **kwargs):
    """
    Actualiza el stock del producto basado en el tipo de movimiento de inventario.
    """
    if created:
        producto = instance.producto
        
        if instance.tipo == MovimientoInventario.TipoMovimiento.ENTRADA:
            producto.stock_fisico += instance.cantidad
        
        elif instance.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
            producto.stock_fisico -= instance.cantidad
        
        elif instance.tipo == MovimientoInventario.TipoMovimiento.RESERVA:
            producto.stock_reservado += instance.cantidad
        
        elif instance.tipo == MovimientoInventario.TipoMovimiento.LIBERACION:
            # Asegurarse de no liberar más de lo reservado
            if producto.stock_reservado >= instance.cantidad:
                producto.stock_reservado -= instance.cantidad
            else:
                producto.stock_reservado = 0 # O manejar como un error
        
        producto.save(update_fields=['stock_fisico', 'stock_reservado'])
        
        if producto.stock_disponible <= producto.umbral_minimo:
            print(f"ALERTA: El stock disponible de '{producto.nombre}' ({producto.stock_disponible}) ha alcanzado o está por debajo del umbral mínimo ({producto.umbral_minimo}).")
