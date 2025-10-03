from django.db import models
from Base.models import BaseModel

class Empresa(BaseModel):
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la empresa")
    sector = models.CharField(max_length=255, verbose_name="Sector económico")
    nit = models.CharField(max_length=15, unique=True, verbose_name="NIT")
    nombre_contacto = models.CharField(max_length=255, verbose_name="Nombre del contacto")
    correo_contacto = models.EmailField(verbose_name="Correo del contacto")
    pagar_despues = models.BooleanField(default=False, verbose_name="¿Puede pagar después?")

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        db_table = "empresas"

    def __str__(self):
        return f"{self.nombre} ({self.nit})".title()


class Area(BaseModel):
    nombre = models.CharField(max_length=255, verbose_name="Nombre del área")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del área")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="areas", verbose_name="Empresa")

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        db_table = "areas"
        constraints = [
            models.UniqueConstraint(fields=["nombre", "empresa"], name="unique_nombre_por_empresa")
        ]

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})".title()





