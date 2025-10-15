from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from Base.models import BaseModel

class Producto(BaseModel):
    nombre = models.CharField(max_length=255, verbose_name="Nombre del producto")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    
    # --- CAMPOS DE STOCK MEJORADOS ---
    stock_fisico = models.PositiveIntegerField(default=0, verbose_name="Stock Físico Total")
    stock_reservado = models.PositiveIntegerField(default=0, verbose_name="Stock Reservado")
    
    umbral_minimo = models.PositiveIntegerField(default=5, verbose_name="Umbral mínimo de stock")
    estado = models.BooleanField(default=True, verbose_name="Estado")

    @property
    def stock_disponible(self):
        """
        Calcula el stock real disponible para la venta.
        """
        return self.stock_fisico - self.stock_reservado

    def __str__(self):
        return self.nombre
    
    # Eliminamos el campo 'stock' anterior.
    # El 'stock_fisico' solo se modificará mediante movimientos.

class MovimientoInventario(BaseModel):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada de stock'
        SALIDA = 'SALIDA', 'Salida por despacho'
        RESERVA = 'RESERVA', 'Reserva de stock'
        LIBERACION = 'LIBERACION', 'Liberación de reserva'
        AJUSTE = 'AJUSTE', 'Ajuste de inventario'

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=TipoMovimiento.choices, verbose_name="Tipo de Movimiento")
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    # Referencia a la solicitud o pedido que origina el movimiento
    # solicitud = models.ForeignKey('Solicitudes.Solicitud', on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Descripción/Comprobante")
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="movimientos_creados"
    )

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.cantidad} para {self.producto.nombre}"
