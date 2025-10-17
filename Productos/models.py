from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from Base.models import BaseModel


class Producto(BaseModel):
    nombre = models.CharField(max_length=255, unique=True, verbose_name="Nombre del Producto")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Precio Unitario"
    )
    stock_fisico = models.IntegerField(default=0, verbose_name="Stock Físico")
    stock_reservado = models.IntegerField(default=0, verbose_name="Stock Reservado")
    umbral_minimo = models.IntegerField(default=10, verbose_name="Umbral Mínimo")
    estado = models.BooleanField(default=True, verbose_name="Estado Activo")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        db_table = "productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def stock_disponible(self):
        """Calcula el stock disponible (físico - reservado)"""
        return self.stock_fisico - self.stock_reservado


class MovimientoInventario(BaseModel):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada de stock'
        SALIDA = 'SALIDA', 'Salida por despacho'
        RESERVA = 'RESERVA', 'Reserva de stock'
        LIBERACION = 'LIBERACION', 'Liberación de reserva'
        AJUSTE = 'AJUSTE', 'Ajuste de inventario'

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="movimientos",
        verbose_name="Producto"
    )
    
    tipo = models.CharField(
        max_length=20,
        choices=TipoMovimiento.choices,
        verbose_name="Tipo de Movimiento"
    )
    
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    
    # ✅ RELACIONES AGREGADAS
    solicitud = models.ForeignKey(
        'Solicitudes.Solicitud',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
        verbose_name="Solicitud Origen"
    )
    
    pedido = models.ForeignKey(
        'Solicitudes.Pedido',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
        verbose_name="Pedido Origen"
    )
    
    descripcion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Descripción/Comprobante"
    )
    
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_creados",
        verbose_name="Usuario Responsable"
    )

    class Meta:
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        db_table = "movimientos_inventario"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.cantidad} para {self.producto.nombre}"
