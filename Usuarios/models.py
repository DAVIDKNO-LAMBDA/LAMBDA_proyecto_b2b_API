import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.exceptions import ValidationError
from Base.models import BaseModel
from Empresas.models import Empresa, Area

class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombres, apellidos, cargo, empresa, area, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(
            email=email, nombres=nombres, apellidos=apellidos, cargo=cargo,
            empresa=empresa, area=area, **extra_fields
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean(exclude=None)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombres, apellidos, cargo, empresa, area, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, nombres, apellidos, cargo, empresa, area, password, **extra_fields)

class Usuario(BaseModel, AbstractBaseUser, PermissionsMixin):
    nombres = models.CharField(max_length=255, verbose_name="Nombres")
    apellidos = models.CharField(max_length=255, verbose_name="Apellidos")
    email = models.EmailField(unique=True, verbose_name="Correo electrónico")
    celular = models.CharField(max_length=10, blank=True, null=True, verbose_name="Número de celular")
    cargo = models.CharField(max_length=255, verbose_name="Cargo")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="usuarios", verbose_name="Empresa")
    area = models.ForeignKey(Area, on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios", verbose_name="Área")
    is_active = models.BooleanField(default=False, verbose_name="Activo")
    is_staff = models.BooleanField(default=False, verbose_name="Es staff")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombres", "apellidos", "cargo", "empresa", "area"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        db_table = "usuarios"
        ordering = ["empresa", "nombres"]

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.empresa.nombre})"

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip()

    def clean(self):
        super().clean()
        if self.area and self.empresa and self.area.empresa_id != self.empresa_id:
            raise ValidationError({"area": "El área debe pertenecer a la misma empresa del usuario."})

    def save(self, *args, **kwargs):
        self.full_clean(exclude=None)
        return super().save(*args, **kwargs)

def fecha_expiracion_default():
    return timezone.now() + timedelta(days=2)

class ActivacionUsuario(BaseModel):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name="activacion")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    usado = models.BooleanField(default=False)
    fecha_expiracion = models.DateTimeField(default=fecha_expiracion_default)

    class Meta:
        verbose_name = "Activación de usuario"
        verbose_name_plural = "Activaciones de usuarios"
        db_table = "activaciones_usuarios"

    def __str__(self):
        return f"Token {self.token} - {self.usuario.email}"

    def expirado(self) -> bool:
        return timezone.now() > self.fecha_expiracion

    def esta_vigente(self) -> bool:
        return (not self.usado) and (timezone.now() <= self.fecha_expiracion)
