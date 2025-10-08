from django.db import models
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

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        db_table = "areas"
        constraints = [
            models.UniqueConstraint(fields=['nombre', 'empresa'], name='unique_nombre_por_empresa')
        ]
        ordering = ["empresa", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"
