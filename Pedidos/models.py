from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from Base.models import BaseModel
from Empresas.models import Empresa
from Productos.models import Producto
from Solicitudes.models import Solicitud


class Pedido(BaseModel):
    """
    Modelo principal para pedidos externos hacia Lambda (HU14-HU21)
    Flujo: Solicitud Aprobada → Pedido → Validación Lambda → Pago → Despacho
    """
    
    class EstadoPedido(models.TextChoices):
        # Estados de validación interna Lambda (FLUJO SECUENCIAL)
        PENDIENTE_VALIDACION_LAMBDA = 'pendiente_validacion_lambda', 'Pendiente Validación Lambda'
        PENDIENTE_ABASTECIMIENTO_LAMBDA = 'pendiente_abastecimiento_lambda', 'Pendiente Área Abastecimiento Lambda'
        PENDIENTE_FINANZAS_LAMBDA = 'pendiente_finanzas_lambda', 'Pendiente Área Finanzas Lambda'
        
        # Estados post-validación
        APROBADO_LAMBDA = 'aprobado_lambda', 'Aprobado por Lambda'
        RECHAZADO_ABASTECIMIENTO_LAMBDA = 'rechazado_abastecimiento_lambda', 'Rechazado por Abastecimiento Lambda'
        RECHAZADO_FINANZAS_LAMBDA = 'rechazado_finanzas_lambda', 'Rechazado por Finanzas Lambda'
        
        # Estados de pago (HU15-HU16)
        PENDIENTE_PAGO = 'pendiente_pago', 'Pendiente de Pago'
        PAGO_CONFIRMADO = 'pago_confirmado', 'Pago Confirmado'
        PAGO_VENCIDO = 'pago_vencido', 'Pago Vencido'
        
        # Estados finales
        FACTURADO = 'facturado', 'Facturado'  # Estado final - reemplaza despacho/entrega
        CANCELADO = 'cancelado', 'Cancelado'
    
    class ModalidadPago(models.TextChoices):
        INMEDIATO = 'inmediato', 'Pago Inmediato'
        DIFERIDO = 'diferido', 'Pago Diferido'
    
    # =============================================
    # INFORMACIÓN BÁSICA
    # =============================================
    solicitud_origen = models.OneToOneField(
        Solicitud,
        on_delete=models.CASCADE,
        related_name='pedido',
        verbose_name="Solicitud de Origen"
    )
    
    numero_pedido = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Número de Pedido",
        editable=False
    )
    
    empresa_cliente = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='pedidos',
        verbose_name="Empresa Cliente"
    )
    
    usuario_solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pedidos_solicitados',
        verbose_name="Usuario Solicitante"
    )
    
    estado = models.CharField(
        max_length=40,
        choices=EstadoPedido.choices,
        default=EstadoPedido.PENDIENTE_VALIDACION_LAMBDA,
        verbose_name="Estado del Pedido"
    )
    
    observaciones_cliente = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones del Cliente"
    )
    
    # =============================================
    # VALIDACIÓN LAMBDA - ABASTECIMIENTO
    # =============================================
    validador_abastecimiento_lambda = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_validados_abastecimiento_lambda',
        verbose_name="Validador Abastecimiento Lambda"
    )
    
    fecha_validacion_abastecimiento_lambda = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Validación Abastecimiento Lambda"
    )
    
    comentario_abastecimiento_lambda = models.TextField(
        blank=True,
        null=True,
        verbose_name="Comentario Abastecimiento Lambda"
    )
    
    stock_confirmado_lambda = models.BooleanField(
        default=False,
        verbose_name="Stock Confirmado en Lambda"
    )
    
    # =============================================
    # VALIDACIÓN LAMBDA - FINANZAS
    # =============================================
    validador_finanzas_lambda = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_validados_finanzas_lambda',
        verbose_name="Validador Finanzas Lambda"
    )
    
    fecha_validacion_finanzas_lambda = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Validación Finanzas Lambda"
    )
    
    comentario_finanzas_lambda = models.TextField(
        blank=True,
        null=True,
        verbose_name="Comentario Finanzas Lambda"
    )
    
    credito_aprobado_lambda = models.BooleanField(
        default=False,
        verbose_name="Crédito Aprobado por Lambda"
    )
    
    # =============================================
    # CONDICIONES DE PAGO (HU15)
    # =============================================
    modalidad_pago = models.CharField(
        max_length=20,
        choices=ModalidadPago.choices,
        null=True,
        blank=True,
        verbose_name="Modalidad de Pago"
    )
    
    fecha_limite_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Límite de Pago"
    )
    
    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Monto Total"
    )
    
    descuento_aplicado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Descuento Aplicado (%)"
    )
    
    monto_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Monto Final a Pagar"
    )
    
    # =============================================
    # GESTIÓN DE PAGO (HU16)
    # =============================================
    fecha_pago = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Pago"
    )
    
    fecha_facturacion = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Facturación"
    )
    
    comprobante_pago = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Número de Comprobante de Pago"
    )
    
    metodo_pago = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Método de Pago"
    )
    
    # =============================================
    # DESPACHO Y ENTREGA
    # =============================================
    fecha_despacho = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Despacho"
    )
    
    numero_guia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Número de Guía de Despacho"
    )
    
    transportadora = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Empresa Transportadora"
    )
    
    fecha_entrega_estimada = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Estimada de Entrega"
    )
    
    fecha_entrega_real = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Real de Entrega"
    )
    
    # =============================================
    # FACTURACIÓN (HU25)
    # =============================================
    numero_factura = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Número de Factura"
    )
    
    fecha_factura = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Facturación"
    )
    
    factura_enviada = models.BooleanField(
        default=False,
        verbose_name="Factura Enviada por Correo"
    )
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        db_table = "pedidos"
        ordering = ['-created_at']
        permissions = [
            ("puede_validar_pedido_abastecimiento_lambda", "Puede validar pedidos (Abastecimiento Lambda)"),
            ("puede_validar_pedido_finanzas_lambda", "Puede validar pedidos (Finanzas Lambda)"),
            ("puede_aprobar_pedido_lambda", "Puede aprobar pedidos finales Lambda"),
            ("puede_gestionar_pagos", "Puede gestionar pagos de pedidos"),
            ("puede_gestionar_despachos", "Puede gestionar despachos"),
            ("puede_ver_todos_pedidos", "Puede ver todos los pedidos"),
        ]
    
    def __str__(self):
        return f"{self.numero_pedido} - {self.empresa_cliente.nombre} ({self.get_estado_display()})"
    
    def save(self, *args, **kwargs):
        # Generar número de pedido automático
        if not self.numero_pedido:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.numero_pedido = f"PED-{self.empresa_cliente.id}-{timestamp}"
        
        super().save(*args, **kwargs)
    
    def calcular_monto_total(self):
        """Calcula el monto total del pedido"""
        total = sum(
            item.cantidad_final * item.precio_unitario_final 
            for item in self.items.all()
        )
        self.monto_total = total
        
        # Aplicar descuento
        if self.descuento_aplicado > 0:
            descuento = total * (self.descuento_aplicado / 100)
            self.monto_final = total - descuento
        else:
            self.monto_final = total
        
        self.save(update_fields=['monto_total', 'monto_final'])
        return self.monto_final
    
    def puede_cancelarse(self):
        """Verifica si el pedido puede cancelarse"""
        estados_cancelables = [
            self.EstadoPedido.PENDIENTE_VALIDACION_LAMBDA,
            self.EstadoPedido.PENDIENTE_ABASTECIMIENTO_LAMBDA,
            self.EstadoPedido.PENDIENTE_FINANZAS_LAMBDA,
            self.EstadoPedido.PENDIENTE_PAGO,
        ]
        return self.estado in estados_cancelables
    
    def esta_vencido(self):
        """Verifica si el pago está vencido"""
        if self.fecha_limite_pago and self.modalidad_pago == self.ModalidadPago.DIFERIDO:
            return timezone.now().date() > self.fecha_limite_pago
        return False


class ItemPedido(BaseModel):
    """
    Detalle de productos en un pedido (HU14)
    """
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Pedido"
    )
    
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='items_pedido',
        verbose_name="Producto"
    )
    
    cantidad_solicitada = models.PositiveIntegerField(
        verbose_name="Cantidad Solicitada"
    )
    
    cantidad_aprobada_cliente = models.PositiveIntegerField(
        verbose_name="Cantidad Aprobada por Cliente"
    )
    
    cantidad_final = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Cantidad Final Aprobada por Lambda"
    )
    
    precio_unitario_solicitud = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio Unitario en Solicitud"
    )
    
    precio_unitario_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio Unitario Final Lambda"
    )
    
    observaciones_lambda = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones de Lambda"
    )
    
    stock_reservado = models.BooleanField(
        default=False,
        verbose_name="Stock Reservado"
    )
    
    class Meta:
        verbose_name = "Item de Pedido"
        verbose_name_plural = "Items de Pedido"
        db_table = "items_pedido"
        unique_together = ['pedido', 'producto']
    
    def __str__(self):
        return f"{self.producto.nombre} - Cant: {self.cantidad_final or self.cantidad_aprobada_cliente}"
    
    def save(self, *args, **kwargs):
        # Cantidad final por defecto igual a cantidad aprobada por cliente
        if self.cantidad_final is None:
            self.cantidad_final = self.cantidad_aprobada_cliente
        
        # Precio final por defecto igual al de solicitud
        if not self.precio_unitario_final:
            self.precio_unitario_final = self.precio_unitario_solicitud
        
        super().save(*args, **kwargs)
        
        # Recalcular monto total del pedido
        self.pedido.calcular_monto_total()


class HistorialValidacionPedido(BaseModel):
    """
    Modelo para auditoría de validaciones en Lambda (Similar a HU12-HU13)
    """
    class TipoValidacion(models.TextChoices):
        ABASTECIMIENTO_LAMBDA = 'abastecimiento_lambda', 'Abastecimiento Lambda'
        FINANZAS_LAMBDA = 'finanzas_lambda', 'Finanzas Lambda'
        PAGO = 'pago', 'Validación de Pago'
        FACTURACION = 'facturacion', 'Facturación'
    
    class AccionValidacion(models.TextChoices):
        APROBAR = 'aprobar', 'Aprobado'
        RECHAZAR = 'rechazar', 'Rechazado'
        MODIFICAR = 'modificar', 'Modificado'
        PAGO_CONFIRMADO = 'pago_confirmado', 'Pago Confirmado'
        DESPACHADO = 'despachado', 'Despachado'
        ENTREGADO = 'entregado', 'Entregado'
        ASIGNAR_AREA = 'asignar_area', 'Asignado a Área'
        ASIGNACION_AREA = 'asignacion_area', 'Asignación de Área Lambda'
    
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='historial_validaciones',
        verbose_name="Pedido"
    )
    
    tipo_validacion = models.CharField(
        max_length=30,
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
        related_name='validaciones_pedidos_realizadas',
        verbose_name="Validador"
    )
    
    comentario = models.TextField(verbose_name="Comentario")
    
    datos_anteriores = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos Anteriores",
        help_text="Snapshot del estado anterior"
    )
    
    # Campos específicos para seguimiento de pagos
    monto_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto del Pago"
    )
    
    metodo_pago = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Método de Pago"
    )
    
    # Campo para asignación de áreas Lambda
    area_asignada = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Área Asignada",
        help_text="Área Lambda a la que se asignó el pedido"
    )
    
    class Meta:
        verbose_name = "Historial de Validación de Pedido"
        verbose_name_plural = "Historial de Validaciones de Pedidos"
        db_table = "historial_validaciones_pedido"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_tipo_validacion_display()} - {self.get_accion_display()} por {self.validador.nombre_completo}"


class RecordatorioPago(BaseModel):
    """
    Modelo para gestionar recordatorios de pago (HU19)
    """
    class TipoRecordatorio(models.TextChoices):
        PREVENTIVO = 'preventivo', 'Recordatorio Preventivo (3 días antes)'
        VENCIMIENTO = 'vencimiento', 'Recordatorio de Vencimiento'
        MORA_1 = 'mora_1', 'Primer Recordatorio de Mora (15 días)'
        MORA_2 = 'mora_2', 'Segundo Recordatorio de Mora (30 días)'
        MORA_3 = 'mora_3', 'Tercer Recordatorio de Mora (45 días)'
        MORA_4 = 'mora_4', 'Cuarto Recordatorio de Mora (60 días)'
        LEGAL = 'legal', 'Notificación Legal (75 días)'
    
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='recordatorios',
        verbose_name="Pedido"
    )
    
    tipo = models.CharField(
        max_length=20,
        choices=TipoRecordatorio.choices,
        verbose_name="Tipo de Recordatorio"
    )
    
    fecha_programada = models.DateTimeField(verbose_name="Fecha Programada de Envío")
    
    fecha_enviado = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Envío"
    )
    
    enviado = models.BooleanField(default=False, verbose_name="Enviado")
    
    email_destinatario = models.EmailField(verbose_name="Email Destinatario")
    
    asunto = models.CharField(max_length=255, verbose_name="Asunto del Correo")
    
    exitoso = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Envío Exitoso"
    )
    
    error_envio = models.TextField(
        blank=True,
        null=True,
        verbose_name="Error de Envío"
    )
    
    class Meta:
        verbose_name = "Recordatorio de Pago"
        verbose_name_plural = "Recordatorios de Pago"
        db_table = "recordatorios_pago"
        ordering = ['fecha_programada']
        unique_together = ['pedido', 'tipo']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.pedido.numero_pedido}"
