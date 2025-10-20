from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from Base.models import BaseModel
from Empresas.models import Empresa
from Productos.models import Producto


class Solicitud(BaseModel):
    """
    Modelo para solicitudes internas de productos (HU10)
    Flujo: Solicitante → Abastecimiento → Finanzas → Pedido
    """
    
    class EstadoSolicitud(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        PENDIENTE_JEFE_AREA = 'pendiente_jefe_area', 'Pendiente Aprobación Jefe de Área'
        RECHAZADA_JEFE_AREA = 'rechazada_jefe_area', 'Rechazada por Jefe de Área'
        PENDIENTE_ABASTECIMIENTO = 'pendiente_abastecimiento', 'Pendiente Abastecimiento'
        RECHAZADA_ABASTECIMIENTO = 'rechazada_abastecimiento', 'Rechazada por Abastecimiento'
        PENDIENTE_FINANZAS = 'pendiente_finanzas', 'Pendiente Finanzas'
        RECHAZADA_FINANZAS = 'rechazada_finanzas', 'Rechazada por Finanzas'
        APROBADA = 'aprobada', 'Aprobada - Lista para Conversión'
        CONVERTIDA_PEDIDO = 'convertida_pedido', 'Convertida a Pedido'
        CANCELADA = 'cancelada', 'Cancelada'
    
    # Información básica
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='solicitudes',
        verbose_name="Empresa"
    )
    
    numero_solicitud = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Número de Solicitud",
        editable=False
    )
    
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='solicitudes_creadas',
        verbose_name="Usuario Solicitante"
    )
    
    justificacion = models.TextField(verbose_name="Justificación de la solicitud")
    
    estado = models.CharField(
        max_length=30,
        choices=EstadoSolicitud.choices,
        default=EstadoSolicitud.PENDIENTE_JEFE_AREA,
        verbose_name="Estado"
    )
    
    # Validación del Jefe de Área (NUEVO PASO)
    jefe_area = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_aprobadas_jefe',
        verbose_name="Jefe de Área que Aprueba"
    )
    
    fecha_aprobacion_jefe = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Aprobación Jefe"
    )
    
    comentario_jefe = models.TextField(
        blank=True,
        null=True,
        verbose_name="Comentario del Jefe de Área"
    )
    
    # Validación de Abastecimiento (HU12)
    validador_abastecimiento = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_validadas_abastecimiento',
        verbose_name="Validador de Abastecimiento"
    )
    
    fecha_validacion_abastecimiento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Validación Abastecimiento"
    )
    
    comentario_abastecimiento = models.TextField(
        blank=True,
        null=True,
        verbose_name="Comentario de Abastecimiento"
    )
    
    stock_validado = models.BooleanField(
        default=False,
        verbose_name="Stock Validado"
    )
    
    # Validación Financiera (HU13)
    validador_finanzas = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_validadas_finanzas',
        verbose_name="Validador Financiero"
    )
    
    fecha_validacion_finanzas = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Validación Finanzas"
    )
    
    comentario_finanzas = models.TextField(
        blank=True,
        null=True,
        verbose_name="Comentario Financiero"
    )
    
    # 🆕 ACTUALIZADO: Monto de presupuesto aprobado (HU13)
    presupuesto_aprobado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Presupuesto Aprobado"
    )
    
    # 🆕 NUEVO: Forma de pago preferida por empresa (HU15)
    FORMA_PAGO_CHOICES = [
        ('inmediato', 'Pago Inmediato'),
        ('credito', 'Pago a Crédito'),
        ('diferido', 'Pago Diferido'),
    ]
    
    forma_pago_preferida = models.CharField(
        max_length=20,
        choices=FORMA_PAGO_CHOICES,
        default='inmediato',
        verbose_name="Forma de Pago Preferida"
    )
    
    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Monto Total"
    )
    
    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        db_table = "solicitudes"
        ordering = ['-created_at']
        permissions = [
            ("puede_validar_solicitud_abastecimiento", "Puede validar solicitudes (Abastecimiento)"),
            ("puede_validar_solicitud_finanzas", "Puede validar solicitudes (Finanzas)"),
            ("puede_aprobar_solicitud", "Puede aprobar solicitudes finales"),
            ("puede_rechazar_solicitud", "Puede rechazar solicitudes"),
        ]
    
    def __str__(self):
        return f"{self.numero_solicitud} - {self.empresa.nombre} ({self.get_estado_display()})"
    
    def save(self, *args, **kwargs):
        # Generar número de solicitud automático
        if not self.numero_solicitud:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.numero_solicitud = f"SOL-{self.empresa.id}-{timestamp}"
        
        super().save(*args, **kwargs)
    
    def calcular_monto_total(self):
        """Calcula el monto total de la solicitud"""
        total = sum(
            item.cantidad * item.precio_unitario 
            for item in self.items.all()
        )
        self.monto_total = total
        self.save(update_fields=['monto_total'])
        return total
    
    def aprobar_por_jefe(self, jefe_usuario, comentario=""):
        """Aprueba la solicitud por el jefe de área"""
        self.jefe_area = jefe_usuario
        self.fecha_aprobacion_jefe = timezone.now()
        self.comentario_jefe = comentario
        self.estado = self.EstadoSolicitud.PENDIENTE_ABASTECIMIENTO
        self.save()
    
    def rechazar_por_jefe(self, jefe_usuario, comentario=""):
        """Rechaza la solicitud por el jefe de área"""
        self.jefe_area = jefe_usuario
        self.fecha_aprobacion_jefe = timezone.now()
        self.comentario_jefe = comentario
        self.estado = self.EstadoSolicitud.RECHAZADA_JEFE_AREA
        self.save()
    
    def aprobar_abastecimiento(self, validador_usuario, comentario=""):
        """Aprueba por validador de abastecimiento"""
        self.validador_abastecimiento = validador_usuario
        self.fecha_validacion_abastecimiento = timezone.now()
        self.comentario_abastecimiento = comentario
        self.stock_validado = True
        self.estado = self.EstadoSolicitud.PENDIENTE_FINANZAS
        self.save()
    
    def rechazar_abastecimiento(self, validador_usuario, comentario=""):
        """Rechaza por validador de abastecimiento"""
        self.validador_abastecimiento = validador_usuario
        self.fecha_validacion_abastecimiento = timezone.now()
        self.comentario_abastecimiento = comentario
        self.stock_validado = False
        self.estado = self.EstadoSolicitud.RECHAZADA_ABASTECIMIENTO
        self.save()
    
    def aprobar_finanzas(self, validador_usuario, comentario=""):
        """Aprueba por validador financiero"""
        self.validador_finanzas = validador_usuario
        self.fecha_validacion_finanzas = timezone.now()
        self.comentario_finanzas = comentario
        self.presupuesto_aprobado = True
        self.estado = self.EstadoSolicitud.APROBADA
        self.save()
    
    def rechazar_finanzas(self, validador_usuario, comentario=""):
        """Rechaza por validador financiero"""
        self.validador_finanzas = validador_usuario
        self.fecha_validacion_finanzas = timezone.now()
        self.comentario_finanzas = comentario
        self.presupuesto_aprobado = False
        self.estado = self.EstadoSolicitud.RECHAZADA_FINANZAS
        self.save()


class ItemSolicitud(BaseModel):
    """
    Detalle de productos en una solicitud (HU10)
    """
    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Solicitud"
    )
    
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='items_solicitud',
        verbose_name="Producto"
    )
    
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    
    cantidad_aprobada = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Cantidad Aprobada",
        help_text="Cantidad final aprobada por Abastecimiento"
    )
    
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio Unitario"
    )
    
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )
    
    class Meta:
        verbose_name = "Item de Solicitud"
        verbose_name_plural = "Items de Solicitud"
        db_table = "items_solicitud"
        unique_together = ['solicitud', 'producto']
    
    def __str__(self):
        return f"{self.producto.nombre} - Cant: {self.cantidad}"
    
    def clean(self):
        """Validaciones de negocio"""
        super().clean()
        
        # Validar que haya stock disponible
        if self.producto.stock_disponible < self.cantidad:
            raise ValidationError({
                'cantidad': f'Stock insuficiente. Disponible: {self.producto.stock_disponible}'
            })
    
    def save(self, *args, **kwargs):
        # Capturar precio actual del producto
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio
        
        # Cantidad aprobada por defecto igual a cantidad solicitada
        if self.cantidad_aprobada is None:
            self.cantidad_aprobada = self.cantidad
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalcular monto total de la solicitud
        self.solicitud.calcular_monto_total()


class HistorialValidacion(BaseModel):
    """
    Modelo para auditoría de validaciones (HU12, HU13)
    """
    class TipoValidacion(models.TextChoices):
        ABASTECIMIENTO = 'abastecimiento', 'Abastecimiento'
        FINANZAS = 'finanzas', 'Finanzas'
    
    class AccionValidacion(models.TextChoices):
        APROBAR = 'aprobar', 'Aprobado'
        RECHAZAR = 'rechazar', 'Rechazado'
        MODIFICAR = 'modificar', 'Modificado'
    
    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name='historial_validaciones',
        verbose_name="Solicitud"
    )
    
    tipo_validacion = models.CharField(
        max_length=20,
        choices=TipoValidacion.choices,
        verbose_name="Tipo de Validación"
    )
    
    accion = models.CharField(
        max_length=20,
        choices=AccionValidacion.choices,
        verbose_name="Acción"
    )
    
    validador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='validaciones_realizadas',
        verbose_name="Validador"
    )
    
    comentario = models.TextField(verbose_name="Comentario")
    
    datos_anteriores = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos Anteriores",
        help_text="Snapshot del estado anterior"
    )
    
    class Meta:
        verbose_name = "Historial de Validación"
        verbose_name_plural = "Historial de Validaciones"
        db_table = "historial_validaciones"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_tipo_validacion_display()} - {self.get_accion_display()} por {self.validador.nombre_completo}"
