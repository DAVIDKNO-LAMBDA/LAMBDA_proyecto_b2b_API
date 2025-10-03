from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from Empresas.models import Empresa, Area
from Base.models import BaseModel


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombres, apellidos, cargo, empresa, area=None, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            nombres=nombres,
            apellidos=apellidos,
            cargo=cargo,
            empresa=empresa,
            area=area,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombres, apellidos, cargo, empresa=None, area=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, nombres, apellidos, cargo, empresa, area, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin, BaseModel):
    nombres = models.CharField(max_length=255, verbose_name="Nombres")
    apellidos = models.CharField(max_length=255, verbose_name="Apellidos")
    email = models.EmailField(unique=True, verbose_name="Correo electrónico")
    celular = models.CharField(max_length=10, blank=True, null=True, verbose_name="Número de celular")
    cargo = models.CharField(max_length=255, verbose_name="Cargo")

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="usuarios",
        verbose_name="Empresa"
    )

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="Área"
    )

    is_active = models.BooleanField(default=True, verbose_name="Activo")
    is_staff = models.BooleanField(default=False, verbose_name="Es staff")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombres", "apellidos", "cargo", "empresa", "area"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        db_table = "usuarios"
        permissions = [
            ("es_admin_empresa", "Es Administrador de Empresa"),
            ("es_jefe_area", "Es Jefe de Área"),
            ("valida_financiero", "Validador Financiero"),
            ("solicita_compra", "Empleado solicitante"),
            ("coordina_lambda", "Coordinador Lambda"),
            ("dirige_lambda", "Director Lambda"),
            ("abastece_lambda", "Área de Abastecimiento de Lambda"),
            ("financiero_lambda", "Financiero Lambda"),
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}".title()
    
