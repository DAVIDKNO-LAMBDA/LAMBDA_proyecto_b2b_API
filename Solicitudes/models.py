from django.db import models
from django.db import models
from Base.models import BaseModel
from Empresas.models import Empresa
from Usuarios.models import Usuario


class Solicitud(BaseModel):
    ESTADOS = [
        ("pendiente_abastecimiento", "Pendiente Abastecimiento"),
        ("pendiente_finanzas", "Pendiente Finanzas"),
        ("rechazada", "Rechazada"),
        ("aprobada", "Aprobada"),  # lista para generar Pedido a Lambda (HU14)
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="solicitudes")
    solicitante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="solicitudes")
    justificacion = models.TextField(verbose_name="Justificación de la solicitud")
    estado = models.CharField(max_length=50, choices=ESTADOS, default="pendiente_abastecimiento")

    class Meta:
        db_table = "solicitudes"
        ordering = ["-creado"]
        verbose_name = "Solicitud interna"
        verbose_name_plural = "Solicitudes internas"

    def __str__(self):
        return f"Solicitud #{self.id} - {self.empresa.nombre} ({self.estado})"


class ProductoSolicitud(BaseModel):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name="productos")
    nombre = models.CharField(max_length=255)
    cantidad = models.PositiveIntegerField()
    unidad = models.CharField(max_length=50)

    class Meta:
        db_table = "productos_solicitud"
        verbose_name = "Producto solicitado"
        verbose_name_plural = "Productos solicitados"

    def __str__(self):
        return f"{self.nombre} x{self.cantidad}"


class HistorialAprobacion(BaseModel):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name="historial")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    comentario = models.TextField(blank=True, null=True)
    estado_aprobacion = models.CharField(max_length=50)  # p.ej. aprobado_abastecimiento, rechazado_finanzas

    class Meta:
        db_table = "historial_aprobaciones"
        ordering = ["-creado"]
        verbose_name = "Evento de aprobación"
        verbose_name_plural = "Historial de aprobaciones"

    def __str__(self):
        return f"{self.estado_aprobacion} por {self.usuario.email if self.usuario else 'N/A'}"


# Create your models here.
