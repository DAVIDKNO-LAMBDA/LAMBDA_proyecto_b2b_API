from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from Base.models import BaseModel
from Empresas.models import Empresa
from Pedidos.models import Pedido

Usuario = get_user_model()


class Factura(BaseModel):
    """
    Modelo para facturas generadas automáticamente (HU24)
    """
    class TipoFactura(models.TextChoices):
        VENTA = 'venta', 'Factura de Venta'
        NOTA_CREDITO = 'nota_credito', 'Nota de Crédito'
        NOTA_DEBITO = 'nota_debito', 'Nota de Débito'
    
    class EstadoFactura(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        GENERADA = 'generada', 'Generada'
        ENVIADA = 'enviada', 'Enviada al Cliente'
        PAGADA = 'pagada', 'Pagada'
        ANULADA = 'anulada', 'Anulada'
    
    # =============================================
    # INFORMACIÓN BÁSICA
    # =============================================
    numero_factura = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Número de Factura",
        help_text="Generado automáticamente: FACT-YYYY-NNNNNN"
    )
    
    tipo = models.CharField(
        max_length=20,
        choices=TipoFactura.choices,
        default=TipoFactura.VENTA,
        verbose_name="Tipo de Factura"
    )
    
    estado = models.CharField(
        max_length=20,
        choices=EstadoFactura.choices,
        default=EstadoFactura.BORRADOR,
        verbose_name="Estado"
    )
    
    # =============================================
    # RELACIONES
    # =============================================
    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name='factura',
        verbose_name="Pedido Asociado"
    )
    
    empresa_cliente = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='facturas',
        verbose_name="Empresa Cliente"
    )
    
    generada_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='facturas_generadas',
        verbose_name="Generada por"
    )
    
    # =============================================
    # INFORMACIÓN FINANCIERA
    # =============================================
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Subtotal"
    )
    
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Descuento Aplicado"
    )
    
    impuestos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Impuestos (IVA)"
    )
    
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total Factura"
    )
    
    # =============================================
    # FECHAS
    # =============================================
    fecha_emision = models.DateField(
        default=timezone.now,
        verbose_name="Fecha de Emisión"
    )
    
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Vencimiento"
    )
    
    fecha_envio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Envío"
    )
    
    # =============================================
    # ARCHIVOS
    # =============================================
    archivo_pdf = models.FileField(
        upload_to='facturas/pdf/',
        null=True,
        blank=True,
        verbose_name="Archivo PDF"
    )
    
    # =============================================
    # INFORMACIÓN ADICIONAL
    # =============================================
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones"
    )
    
    terminos_condiciones = models.TextField(
        blank=True,
        verbose_name="Términos y Condiciones"
    )
    
    class Meta:
        db_table = 'reportes_factura'
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ['-fecha_emision', '-numero_factura']
    
    def __str__(self):
        return f"{self.numero_factura} - {self.empresa_cliente.nombre}"
    
    def save(self, *args, **kwargs):
        # Generar número de factura automáticamente
        if not self.numero_factura:
            self.numero_factura = self.generar_numero_factura()
        
        # Calcular totales
        if self.pedido:
            self.subtotal = self.pedido.monto_total
            self.descuento = self.pedido.descuento_aplicado or 0
            self.impuestos = self.calcular_impuestos()
            self.total = self.subtotal - self.descuento + self.impuestos
        
        super().save(*args, **kwargs)
    
    def generar_numero_factura(self):
        """Genera número de factura único"""
        año = timezone.now().year
        
        # Obtener último número del año
        ultima_factura = Factura.objects.filter(
            numero_factura__startswith=f"FACT-{año}"
        ).order_by('-numero_factura').first()
        
        if ultima_factura:
            ultimo_numero = int(ultima_factura.numero_factura.split('-')[-1])
            nuevo_numero = ultimo_numero + 1
        else:
            nuevo_numero = 1
        
        return f"FACT-{año}-{nuevo_numero:06d}"
    
    def calcular_impuestos(self):
        """Calcula IVA (19% en Colombia)"""
        base_gravable = self.subtotal - self.descuento
        return base_gravable * 0.19


class ItemFactura(BaseModel):
    """
    Detalle de items en factura
    """
    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Factura"
    )
    
    descripcion = models.CharField(
        max_length=255,
        verbose_name="Descripción"
    )
    
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Cantidad"
    )
    
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio Unitario"
    )
    
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Subtotal"
    )
    
    class Meta:
        db_table = 'reportes_item_factura'
        verbose_name = "Item de Factura"
        verbose_name_plural = "Items de Factura"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)


class ReportePeriodico(BaseModel):
    """
    Reportes periódicos generados automáticamente (HU25)
    """
    class TipoReporte(models.TextChoices):
        VENTAS_MENSUAL = 'ventas_mensual', 'Ventas Mensual'
        VENTAS_ANUAL = 'ventas_anual', 'Ventas Anual'
        EMPRESAS_MENSUAL = 'empresas_mensual', 'Por Empresa Mensual'
        PRODUCTOS_MENSUAL = 'productos_mensual', 'Por Productos Mensual'
        PAGOS_PENDIENTES = 'pagos_pendientes', 'Pagos Pendientes'
        MORA_EMPRESAS = 'mora_empresas', 'Empresas en Mora'
    
    class FormatoReporte(models.TextChoices):
        PDF = 'pdf', 'PDF'
        EXCEL = 'excel', 'Excel'
        CSV = 'csv', 'CSV'
    
    # =============================================
    # INFORMACIÓN BÁSICA
    # =============================================
    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del Reporte"
    )
    
    tipo = models.CharField(
        max_length=50,
        choices=TipoReporte.choices,
        verbose_name="Tipo de Reporte"
    )
    
    formato = models.CharField(
        max_length=20,
        choices=FormatoReporte.choices,
        default=FormatoReporte.PDF,
        verbose_name="Formato"
    )
    
    # =============================================
    # PERÍODO
    # =============================================
    fecha_inicio = models.DateField(
        verbose_name="Fecha Inicio"
    )
    
    fecha_fin = models.DateField(
        verbose_name="Fecha Fin"
    )
    
    # =============================================
    # FILTROS
    # =============================================
    empresa_filtro = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Filtrar por Empresa"
    )
    
    # =============================================
    # ARCHIVOS Y RESULTADOS
    # =============================================
    archivo_generado = models.FileField(
        upload_to='reportes/',
        null=True,
        blank=True,
        verbose_name="Archivo Generado"
    )
    
    generado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Generado por"
    )
    
    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Generación"
    )
    
    # =============================================
    # ESTADÍSTICAS DEL REPORTE
    # =============================================
    total_registros = models.IntegerField(
        default=0,
        verbose_name="Total de Registros"
    )
    
    monto_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Monto Total"
    )
    
    resumen_json = models.JSONField(
        default=dict,
        verbose_name="Resumen en JSON"
    )
    
    class Meta:
        db_table = 'reportes_periodico'
        verbose_name = "Reporte Periódico"
        verbose_name_plural = "Reportes Periódicos"
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"{self.nombre} ({self.fecha_inicio} - {self.fecha_fin})"


class ConfiguracionReporte(BaseModel):
    """
    Configuración para reportes automáticos
    """
    class Frecuencia(models.TextChoices):
        DIARIA = 'diaria', 'Diaria'
        SEMANAL = 'semanal', 'Semanal'
        MENSUAL = 'mensual', 'Mensual'
        TRIMESTRAL = 'trimestral', 'Trimestral'
        ANUAL = 'anual', 'Anual'
    
    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre de la Configuración"
    )
    
    tipo_reporte = models.CharField(
        max_length=50,
        choices=ReportePeriodico.TipoReporte.choices,
        verbose_name="Tipo de Reporte"
    )
    
    frecuencia = models.CharField(
        max_length=20,
        choices=Frecuencia.choices,
        verbose_name="Frecuencia"
    )
    
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    
    emails_destino = models.JSONField(
        default=list,
        verbose_name="Emails de Destino",
        help_text="Lista de emails que recibirán el reporte"
    )
    
    proxima_ejecucion = models.DateTimeField(
        verbose_name="Próxima Ejecución"
    )
    
    ultima_ejecucion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Ejecución"
    )
    
    class Meta:
        db_table = 'reportes_configuracion'
        verbose_name = "Configuración de Reporte"
        verbose_name_plural = "Configuraciones de Reportes"
    
    def __str__(self):
        return f"{self.nombre} ({self.frecuencia})"
