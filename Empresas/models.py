from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from Base.models import BaseModel

class Empresa(BaseModel):
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la empresa")
    sector = models.CharField(max_length=255, verbose_name="Sector económico")
    nit = models.CharField(max_length=15, unique=True, verbose_name="NIT")
    nombre_contacto = models.CharField(max_length=255, verbose_name="Nombre del contacto")
    correo_contacto = models.EmailField(verbose_name="Correo del contacto")
    pagar_despues = models.BooleanField(default=False, verbose_name="Habilidad para pagar después")
    es_lambda = models.BooleanField(default=False, verbose_name="¿Es la empresa Lambda?")

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        db_table = "empresas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.nit})"


class Area(BaseModel):
    TIPOS = [
        ("operativa", "Área Operativa"),
        ("financiera", "Área Financiera"),
        ("direccion", "Área de Dirección"),
        ("abastecimiento", "Área de Abastecimiento"),
        ("coordinacion", "Área de Coordinación"),
    ]

    nombre = models.CharField(max_length=255, verbose_name="Nombre del área")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del área")
    tipo = models.CharField(max_length=50, choices=TIPOS, default="operativa", verbose_name="Tipo de área")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="areas", verbose_name="Empresa")

    jefe = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="areas_a_cargo",
        verbose_name="Jefe de área",
        help_text="Usuario jefe de esta área (debe pertenecer a la misma empresa)."
    )

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        db_table = "areas"
        constraints = [
            models.UniqueConstraint(fields=["nombre", "empresa"], name="unique_nombre_por_empresa")
        ]
        ordering = ["empresa", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

    def clean(self):
        super().clean()
        if self.jefe and getattr(self.jefe, "empresa_id", None) != self.empresa_id:
            raise ValidationError({"jefe": "El jefe de área debe pertenecer a la misma empresa."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
