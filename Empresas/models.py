from django.db import models
from Base.models import BaseModel

class Empresa(BaseModel):
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la empresa")
    sector = models.CharField(max_length=255, verbose_name="Sector")
    nit = models.CharField(max_length=50, unique=True, verbose_name="NIT")
    correo_contacto = models.EmailField(verbose_name="Correo de contacto inicial")
    pagar_despues = models.BooleanField(default=False, verbose_name="¿Puede pagar después?")

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        db_table = "empresas_empresa"

    def __str__(self):
        return self.nombre.title()
