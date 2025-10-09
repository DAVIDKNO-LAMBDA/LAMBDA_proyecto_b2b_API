from decimal import Decimal
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from Base.models import BaseModel
from Empresas.models import Empresa
from Productos.models import Producto


def _generar_numero_orden():
    """
    PO-YYYY-XXXXX (secuencial simple por año)
    """
    year = timezone.now().year
    prefix = f"PO-{year}-"
    last = Pedido.objects.filter(numero__startswith=prefix).order_by("-numero").first()
    if not last:
        return f"{prefix}00001"
    try:
        seq = int(last.numero.split("-")[-1]) + 1
    except Exception:
        seq = 1
    return f"{prefix}{seq:05d}"


class Pedido(BaseModel):
    EST_PENDIENTE_PAGO = "pendiente_pago"
    EST_FACTURADO = "facturado"
    EST_FINALIZADO = "finalizado"
    EST_CANCELADO = "cancelado"

    ESTADOS = [
        (EST_PENDIENTE_PAGO, "Pendiente de pago"),
        (EST_FACTURADO, "Facturado"),
        (EST_FINALIZADO, "Finalizado"),
        (EST_CANCELADO, "Cancelado"),
    ]

    PAGO_INMEDIATO = "inmediato"
    PAGO_DIFERIDO = "diferido"
    MODALIDADES = [
        (PAGO_INMEDIATO, "Inmediato"),
        (PAGO_DIFERIDO, "Diferido"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="pedidos")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos_creados")

    numero = models.CharField(max_length=20, unique=True, blank=True)  # se autogenera
    estado = models.CharField(max_length=20, choices=ESTADOS, default=EST_PENDIENTE_PAGO)

    modalidad_pago = models.CharField(max_length=20, choices=MODALIDADES, default=PAGO_INMEDIATO)
    fecha_vencimiento = models.DateField(null=True, blank=True, help_text="Solo para pago diferido (≤ 60 días).")
    aprobado_pago_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="pedidos_aprobados_pago"
    )

    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        db_table = "pedidos"
        ordering = ["-creado"]

    def __str__(self):
        return self.numero or "(sin número)"

    # --------- Reglas HU15 ----------
    def clean(self):
        super().clean()
        if self.modalidad_pago == self.PAGO_DIFERIDO:
            if not self.empresa.pagar_despues:
                raise ValidationError({"modalidad_pago": "La empresa no está autorizada para pago diferido."})
            if not self.fecha_vencimiento:
                raise ValidationError({"fecha_vencimiento": "Debes definir una fecha de vencimiento para pago diferido."})
            if self.fecha_vencimiento > (timezone.localdate() + timedelta(days=60)):
                raise ValidationError({"fecha_vencimiento": "La fecha de vencimiento no puede exceder 60 días."})

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = _generar_numero_orden()
        super().save(*args, **kwargs)

    def recalcular_total(self):
        agg = self.items.aggregate(s=models.Sum("subtotal"))
        self.total = agg["s"] or Decimal("0.00")
        self.save(update_fields=["total"])


class PedidoItem(BaseModel):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = "Item de pedido"
        verbose_name_plural = "Items de pedido"
        db_table = "pedidos_items"

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"

    def clean(self):
        super().clean()
        # HU14: validar existencia actual en Lambda (no reservamos todavía)
        if self.producto and self.cantidad:
            if self.producto.stock_disponible() < self.cantidad:
                raise ValidationError({"cantidad": f"Stock insuficiente para {self.producto.nombre}."})

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio
        self.subtotal = (self.precio_unitario or Decimal("0.00")) * Decimal(self.cantidad or 0)
        super().save(*args, **kwargs)
        # actualizar total del pedido
        if self.pedido_id:
            self.pedido.recalcular_total()
