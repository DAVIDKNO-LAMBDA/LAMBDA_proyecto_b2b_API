import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.exceptions import ValidationError
from Base.models import BaseModel
from Empresas.models import Empresa, Area


class UsuarioManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario"""
    
    def create_user(self, email, nombres, apellidos, cargo, empresa=None, area=None, password=None, **extra_fields):
        """Crea y guarda un usuario regular"""
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        
        email = self.normalize_email(email)
        
        if empresa and not isinstance(empresa, Empresa):
            try:
                empresa = Empresa.objects.get(id=empresa)
            except Empresa.DoesNotExist:
                raise ValueError("La empresa especificada no existe.")
        
        if area and not isinstance(area, Area):
            try:
                area = Area.objects.get(id=area)
            except Area.DoesNotExist:
                raise ValueError("El área especificada no existe.")
        
        user = self.model(
            email=email,
            nombres=nombres,
            apellidos=apellidos,
            cargo=cargo,
            empresa=empresa,
            area=area,
            **extra_fields
        )
        
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, nombres, apellidos, cargo, empresa=None, area=None, password=None, **extra_fields):
        """Crea y guarda un superusuario"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("estado", "activo")
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        
        return self.create_user(email, nombres, apellidos, cargo, empresa, area, password, **extra_fields)


class Usuario(BaseModel, AbstractBaseUser, PermissionsMixin):
    """
    Modelo de Usuario extendido con soporte para empresas, áreas y roles
    Hereda de BaseModel para timestamps y soft-delete
    """
    # =============================================
    # INFORMACIÓN PERSONAL
    # =============================================
    nombres = models.CharField(max_length=255, verbose_name="Nombres")
    apellidos = models.CharField(max_length=255, verbose_name="Apellidos")
    email = models.EmailField(unique=True, verbose_name="Correo electrónico")
    celular = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número de celular")
    cargo = models.CharField(max_length=255, verbose_name="Cargo")
    
    # =============================================
    # RELACIONES
    # =============================================
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="usuarios",
        verbose_name="Empresa",
        null=True,
        blank=True,
        help_text="Empresa a la que pertenece (null para usuarios de Lambda)"
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="Área",
        help_text="Área funcional dentro de la empresa"
    )
    
    # =============================================
    # ESTADO Y ACTIVACIÓN
    # =============================================
    ESTADO_CHOICES = [
        ('pendiente_activacion', 'Pendiente de Activación'),
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    ]
    estado = models.CharField(
        max_length=30,
        choices=ESTADO_CHOICES,
        default='pendiente_activacion',
        verbose_name="Estado"
    )
    
    token_activacion = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Token de activación"
    )
    
    fecha_activacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de activación"
    )
    
    # =============================================
    # FLAGS DE DJANGO
    # =============================================
    is_active = models.BooleanField(default=False, verbose_name="Usuario activo")
    is_staff = models.BooleanField(default=False, verbose_name="Es staff")
    
    # =============================================
    # INDICADORES Y PERMISOS ESPECIALES (NUEVO)
    # =============================================
    es_primer_usuario = models.BooleanField(
        default=False,
        verbose_name="Es primer usuario",
        help_text="True si es el primer usuario creado para la empresa"
    )
    
    # 🆕 CAMPO NUEVO - Permisos personalizados dinámicos
    permisos_personalizados = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Permisos especiales",
        help_text="Permisos dinámicos: validadores, límites, etc."
    )
    
    # =============================================
    # TRAZABILIDAD
    # =============================================
    creado_por = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_creados',
        verbose_name="Creado por"
    )
    
    # =============================================
    # CONFIGURACIÓN DE AUTENTICACIÓN
    # =============================================
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombres", "apellidos", "cargo"]
    
    objects = UsuarioManager()
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        db_table = "usuarios"
        ordering = ["-created_at"]
        
        # =============================================
        # PERMISOS PERSONALIZADOS DE DJANGO
        # =============================================
        permissions = [
            # GESTIÓN DE USUARIOS
            ("puede_crear_usuarios", "Puede crear usuarios"),
            ("puede_editar_usuarios", "Puede editar usuarios"),
            ("puede_eliminar_usuarios", "Puede eliminar usuarios"),
            ("puede_activar_usuarios", "Puede activar/desactivar usuarios"),
            
            # GESTIÓN DE ÁREAS Y ROLES
            ("puede_asignar_areas", "Puede asignar áreas a usuarios"),
            ("puede_asignar_roles", "Puede asignar roles a usuarios"),
            ("puede_ver_todos_usuarios", "Puede ver todos los usuarios"),
            
            # GESTIÓN DE PEDIDOS (Para futuras HU)
            ("puede_crear_solicitudes", "Puede crear solicitudes internas"),
            ("puede_editar_solicitudes", "Puede editar solicitudes propias"),
            ("puede_ver_solicitudes_propias", "Puede ver sus propias solicitudes"),
            ("puede_ver_solicitudes_area", "Puede ver solicitudes de su área"),
            ("puede_ver_todas_solicitudes", "Puede ver todas las solicitudes"),
            
            # VALIDACIONES (HU12, HU13)
            ("puede_validar_abastecimiento", "Puede validar solicitudes (Abastecimiento)"),
            ("puede_validar_finanzas", "Puede validar solicitudes (Finanzas)"),
            ("puede_aprobar_pedidos", "Puede aprobar pedidos finales"),
            ("puede_rechazar_pedidos", "Puede rechazar pedidos"),
            
            # PRODUCTOS Y CATÁLOGO
            ("puede_ver_catalogo", "Puede ver catálogo de productos"),
            ("puede_ver_precios", "Puede ver precios de productos"),
            ("puede_solicitar_productos", "Puede solicitar productos"),
            
            # REPORTES
            ("puede_ver_reportes_basicos", "Puede ver reportes básicos"),
            ("puede_ver_reportes_avanzados", "Puede ver reportes avanzados"),
            ("puede_exportar_reportes", "Puede exportar reportes"),
        ]
    
    def __str__(self):
        return f"{self.nombre_completo} - {self.empresa.nombre if self.empresa else 'Lambda'}"
    
    @property
    def nombre_completo(self) -> str:
        """Retorna nombre completo del usuario"""
        return f"{self.nombres} {self.apellidos}".strip()
    
    def clean(self):
        """Validaciones de negocio"""
        super().clean()
        
        if self.area and not self.empresa:
            raise ValidationError({
                "area": "Un usuario con área debe pertenecer a una empresa."
            })
        
        if self.area and self.empresa and self.area.empresa_id != self.empresa_id:
            raise ValidationError({
                "area": "El área debe pertenecer a la misma empresa del usuario."
            })
    
    def save(self, *args, **kwargs):
        """Override save para validaciones y lógica de activación"""
        if not self.pk and self.empresa and not self.token_activacion:
            self.token_activacion = uuid.uuid4()
            self.estado = 'pendiente_activacion'
        
        if not self.empresa and self.estado == 'pendiente_activacion':
            self.estado = 'activo'
            self.is_active = True
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    # =============================================
    # MÉTODOS DE VERIFICACIÓN DE ROLES (GRUPOS)
    # =============================================
    
    def es_usuario_lambda(self) -> bool:
        """Verifica si es usuario interno de Lambda"""
        return self.empresa is None
    
    def es_admin_empresa(self) -> bool:
        """Verifica si el usuario es Admin de Empresa"""
        return self.groups.filter(name='Admin Empresa').exists()
    
    def es_jefe_area(self) -> bool:
        """Verifica si el usuario es Jefe de Área"""
        return self.groups.filter(name='Jefe de Área').exists()
    
    def es_empleado(self) -> bool:
        """Verifica si el usuario es Empleado básico"""
        return self.groups.filter(name='Empleado').exists()
    
    def obtener_roles(self) -> list:
        """Retorna lista de nombres de roles (grupos) del usuario"""
        return [grupo.name for grupo in self.groups.all()]
    
    # =============================================
    # 🆕 MÉTODOS PARA PERMISOS PERSONALIZADOS (HU09)
    # =============================================
    
    def es_validador_finanzas(self) -> bool:
        """Verifica si puede validar solicitudes financieras (HU13)"""
        return self.permisos_personalizados.get('validador_finanzas', False)
    
    def es_validador_abastecimiento(self) -> bool:
        """Verifica si puede validar solicitudes de abastecimiento (HU12)"""
        return self.permisos_personalizados.get('validador_abastecimiento', False)
    
    def puede_crear_solicitudes(self) -> bool:
        """Verifica si puede crear solicitudes internas (HU10)"""
        return (
            self.permisos_personalizados.get('puede_crear_solicitudes', False) or
            self.es_jefe_area() or
            self.es_admin_empresa()
        )
    
    def obtener_limite_aprobacion(self) -> int:
        """Retorna límite de aprobación financiera (para HU13)"""
        return self.permisos_personalizados.get('limite_aprobacion', 0)
    
    def obtener_permisos_detalle(self) -> dict:
        """
        Retorna diccionario completo con permisos de grupos + personalizados
        Útil para frontend
        """
        permisos_grupos = []
        for grupo in self.groups.all():
            for p in grupo.permissions.all():
                permisos_grupos.append(f"{p.content_type.app_label}.{p.codename}")
        
        permisos_usuario = [
            f"{p.content_type.app_label}.{p.codename}" 
            for p in self.user_permissions.all()
        ]
        
        return {
            'roles': self.obtener_roles(),
            'permisos_grupos': permisos_grupos,
            'permisos_individuales': permisos_usuario,
            'permisos_personalizados': self.permisos_personalizados,
            'validadores': {
                'finanzas': self.es_validador_finanzas(),
                'abastecimiento': self.es_validador_abastecimiento(),
            }
        }


def fecha_expiracion_default():
    """Retorna fecha de expiración por defecto (48 horas)"""
    return timezone.now() + timedelta(days=2)


class ActivacionUsuario(BaseModel):
    """
    Modelo para gestionar tokens de activación de usuarios
    """
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="activacion"
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    usado = models.BooleanField(default=False)
    fecha_expiracion = models.DateTimeField(default=fecha_expiracion_default)
    
    class Meta:
        verbose_name = "Activación de usuario"
        verbose_name_plural = "Activaciones de usuarios"
        db_table = "activaciones_usuarios"
    
    def __str__(self):
        return f"Token {self.token} - {self.usuario.email}"
    
    def expirado(self) -> bool:
        """Verifica si el token está expirado"""
        return timezone.now() > self.fecha_expiracion
    
    def esta_vigente(self) -> bool:
        """Verifica si el token está vigente (no usado y no expirado)"""
        return (not self.usado) and (timezone.now() <= self.fecha_expiracion)
