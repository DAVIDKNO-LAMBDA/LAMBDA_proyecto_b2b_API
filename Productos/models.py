from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

from Base.models import BaseModel


class Producto(BaseModel):
    nombre = models.CharField(max_length=255, unique=True, verbose_name="Nombre del producto")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    precio = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    umbral_minimo = models.PositiveIntegerField(default=0, verbose_name="Umbral mínimo de stock")
    # estado/banderas y timestamps vienen de BaseModel

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        db_table = "productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def stock_disponible(self) -> int:
        """
        Stock disponible = entradas - salidas - reservas activas
        (reservas las manejaremos desde Pedidos; aquí solo se descuentan si existen)
        """
        entradas = self.movimientos.filter(tipo=MovimientoInventario.TIPO_ENTRADA).aggregate(
            total=models.Sum("cantidad")
        )["total"] or 0
        salidas = self.movimientos.filter(tipo=MovimientoInventario.TIPO_SALIDA).aggregate(
            total=models.Sum("cantidad")
        )["total"] or 0
        reservas = self.movimientos.filter(
            tipo=MovimientoInventario.TIPO_RESERVA, reserva_activa=True
        ).aggregate(total=models.Sum("cantidad"))["total"] or 0
        return int(entradas) - int(salidas) - int(reservas)


class MovimientoInventario(BaseModel):
    TIPO_ENTRADA = "entrada"
    TIPO_SALIDA = "salida"
    TIPO_RESERVA = "reserva"
    TIPOS = [
        (TIPO_ENTRADA, "Entrada"),
        (TIPO_SALIDA, "Salida"),
        (TIPO_RESERVA, "Reserva"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=TIPOS)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimientos_inventario")
    nota = models.TextField(blank=True, null=True)

    # Para reservas (se usará desde Pedidos)
    reserva_activa = models.BooleanField(default=False)
    referencia = models.CharField(max_length=50, blank=True, null=True, help_text="ID/Referencia externa (Pedido, etc.)")

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        db_table = "movimientos_inventario"
        ordering = ["-creado"]

    def __str__(self):
        return f"[{self.tipo}] {self.producto.nombre} x {self.cantidad}"
