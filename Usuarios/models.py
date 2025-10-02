import uuid
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from Base.models import BaseModel
from Empresas.models import Empresa

class Usuario(AbstractUser, BaseModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(verbose_name="Correo")
    celular = models.CharField(max_length=20, blank=True, null=True)
    cargo = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)

    ROL_CHOICES = [
        ("admin_sistema", "Admin del Sistema"),
        ("admin_empresa", "Admin de Empresa"),
        ("jefe_area", "Jefe de Área"),
        ("validador", "Validador"),
        ("empleado", "Empleado"),
        ("coordinador_lambda", "Coordinador Lambda"),
        ("director_lambda", "Director Lambda"),
        ("financiera_lambda", "Financiera Lambda"),
    ]
    rol = models.CharField(max_length=50, choices=ROL_CHOICES, default="empleado")

    class Meta:
        db_table = "usuarios_usuario"
        constraints = [
            models.UniqueConstraint(fields=["empresa", "email"], name="uq_usuario_empresa_email"),
        ]

class ActivationToken(BaseModel):
    user = models.ForeignKey("Usuario", on_delete=models.CASCADE, related_name="activation_tokens")
    token = models.CharField(max_length=64, unique=True, default=lambda: uuid.uuid4().hex)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "usuarios_activation_token"

    @classmethod
    def create_for_user(cls, user, hours_valid=72):
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=hours_valid),
        )

    @property
    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at

class EmpleadoAudit(BaseModel):
    empleado = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="auditorias")
    modificado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name="modificaciones_realizadas")
    comentario = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "usuarios_empleado_audit"
        verbose_name = "Auditoría de Empleado"
        verbose_name_plural = "Auditorías de Empleados" 