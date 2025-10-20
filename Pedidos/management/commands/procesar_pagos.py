from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from Pedidos.models import Pedido, RecordatorioPago
from Base.correos import enviar_correo_html
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa recordatorios de pago y gestiona vencimientos automáticamente (HU19)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta sin realizar cambios reales (solo muestra lo que haría)',
        )
        parser.add_argument(
            '--enviar-emails',
            action='store_true',
            help='Envía emails de recordatorio (por defecto solo muestra)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.enviar_emails = options['enviar_emails']
        
        self.stdout.write(
            self.style.SUCCESS("🚀 Iniciando procesamiento de pagos automático...\n")
        )
        
        # =============================================
        # 1. PROCESAR RECORDATORIOS PENDIENTES
        # =============================================
        self.procesar_recordatorios_pendientes()
        
        # =============================================
        # 2. MARCAR PEDIDOS VENCIDOS
        # =============================================
        self.marcar_pedidos_vencidos()
        
        # =============================================
        # 3. ESTADÍSTICAS FINALES
        # =============================================
        self.mostrar_estadisticas()
        
        self.stdout.write(
            self.style.SUCCESS("\n✅ Procesamiento completado exitosamente!")
        )

    def procesar_recordatorios_pendientes(self):
        """Procesa recordatorios de pago que deben enviarse hoy"""
        self.stdout.write(
            self.style.WARNING("📧 Procesando recordatorios de pago...")
        )
        
        hoy = timezone.now().date()
        
        # Obtener recordatorios que deben enviarse hoy
        recordatorios_pendientes = RecordatorioPago.objects.filter(
            fecha_programada__date=hoy,
            enviado=False,
            pedido__deleted_at__isnull=True,
            pedido__estado__in=[
                Pedido.EstadoPedido.PENDIENTE_PAGO,
                Pedido.EstadoPedido.PAGO_VENCIDO
            ]
        ).select_related('pedido', 'pedido__empresa_cliente')
        
        total_recordatorios = recordatorios_pendientes.count()
        enviados_exitosos = 0
        errores = 0
        
        self.stdout.write(f"   📊 {total_recordatorios} recordatorios programados para hoy")
        
        for recordatorio in recordatorios_pendientes:
            try:
                if self.dry_run:
                    self.stdout.write(
                        f"   🔍 [DRY-RUN] Enviaría recordatorio {recordatorio.tipo} "
                        f"para pedido {recordatorio.pedido.numero_pedido}"
                    )
                    continue
                
                # Generar contenido del email
                contexto = self.generar_contexto_recordatorio(recordatorio)
                
                if self.enviar_emails:
                    # Enviar email de recordatorio
                    resultado = enviar_correo_html(
                        destinatario=recordatorio.email_destinatario,
                        asunto=recordatorio.asunto,
                        template_path='Pedidos/Emails/recordatorio_pago.html',
                        contexto=contexto
                    )
                    
                    if resultado:
                        # Marcar como enviado
                        recordatorio.enviado = True
                        recordatorio.fecha_envio = timezone.now()
                        recordatorio.save(update_fields=['enviado', 'fecha_envio'])
                        
                        enviados_exitosos += 1
                        self.stdout.write(
                            f"   ✅ Recordatorio {recordatorio.tipo} enviado "
                            f"para pedido {recordatorio.pedido.numero_pedido}"
                        )
                    else:
                        errores += 1
                        self.stdout.write(
                            f"   ❌ Error enviando recordatorio para pedido "
                            f"{recordatorio.pedido.numero_pedido}"
                        )
                else:
                    # Solo marcar como procesado sin enviar
                    recordatorio.enviado = True
                    recordatorio.fecha_envio = timezone.now()
                    recordatorio.save(update_fields=['enviado', 'fecha_envio'])
                    
                    enviados_exitosos += 1
                    self.stdout.write(
                        f"   📝 Recordatorio marcado como procesado "
                        f"para pedido {recordatorio.pedido.numero_pedido}"
                    )
            
            except Exception as e:
                errores += 1
                logger.error(f"Error procesando recordatorio {recordatorio.id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(
                        f"   ❌ Error procesando recordatorio {recordatorio.id}: {str(e)}"
                    )
                )
        
        # Resumen de recordatorios
        self.stdout.write(
            f"   📊 Resumen: {enviados_exitosos} enviados, {errores} errores\n"
        )

    def marcar_pedidos_vencidos(self):
        """Marca pedidos como vencidos si pasó la fecha límite"""
        self.stdout.write(
            self.style.WARNING("⏰ Verificando pedidos vencidos...")
        )
        
        hoy = timezone.now().date()
        
        # Buscar pedidos pendientes de pago que ya vencieron
        pedidos_vencidos = Pedido.objects.filter(
            estado=Pedido.EstadoPedido.PENDIENTE_PAGO,
            modalidad_pago=Pedido.ModalidadPago.DIFERIDO,
            fecha_limite_pago__lt=hoy,
            deleted_at__isnull=True
        )
        
        total_vencidos = pedidos_vencidos.count()
        marcados = 0
        
        self.stdout.write(f"   📊 {total_vencidos} pedidos vencidos encontrados")
        
        for pedido in pedidos_vencidos:
            try:
                if self.dry_run:
                    self.stdout.write(
                        f"   🔍 [DRY-RUN] Marcaría como vencido: {pedido.numero_pedido} "
                        f"(vencía: {pedido.fecha_limite_pago})"
                    )
                    continue
                
                with transaction.atomic():
                    # Cambiar estado a vencido
                    pedido.estado = Pedido.EstadoPedido.PAGO_VENCIDO
                    pedido.save(update_fields=['estado'])
                    
                    # Crear registro en historial
                    from Pedidos.models import HistorialValidacionPedido
                    HistorialValidacionPedido.objects.create(
                        pedido=pedido,
                        tipo_validacion=HistorialValidacionPedido.TipoValidacion.PAGO,
                        accion=HistorialValidacionPedido.AccionValidacion.MODIFICAR,
                        comentario=f"Pago vencido automáticamente - Límite: {pedido.fecha_limite_pago}",
                        datos_anteriores={'estado_anterior': Pedido.EstadoPedido.PENDIENTE_PAGO}
                    )
                    
                    marcados += 1
                    self.stdout.write(
                        f"   ⏰ Pedido {pedido.numero_pedido} marcado como vencido "
                        f"(vencía: {pedido.fecha_limite_pago})"
                    )
            
            except Exception as e:
                logger.error(f"Error marcando pedido vencido {pedido.id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(
                        f"   ❌ Error marcando pedido {pedido.numero_pedido}: {str(e)}"
                    )
                )
        
        self.stdout.write(f"   📊 {marcados} pedidos marcados como vencidos\n")

    def mostrar_estadisticas(self):
        """Muestra estadísticas generales del sistema de pagos"""
        self.stdout.write(
            self.style.WARNING("📊 Estadísticas del sistema de pagos:")
        )
        
        # Contar por estado
        estados_pedidos = {
            'pendiente_pago': Pedido.objects.filter(
                estado=Pedido.EstadoPedido.PENDIENTE_PAGO
            ).count(),
            'pago_vencido': Pedido.objects.filter(
                estado=Pedido.EstadoPedido.PAGO_VENCIDO
            ).count(),
            'pago_confirmado': Pedido.objects.filter(
                estado=Pedido.EstadoPedido.PAGO_CONFIRMADO
            ).count(),
        }
        
        # Recordatorios pendientes próximos 7 días
        hoy = timezone.now().date()
        proximos_recordatorios = RecordatorioPago.objects.filter(
            fecha_programada__date__range=[hoy, hoy + timedelta(days=7)],
            enviado=False
        ).count()
        
        self.stdout.write(f"   💰 Pedidos pendientes de pago: {estados_pedidos['pendiente_pago']}")
        self.stdout.write(f"   ⏰ Pedidos con pago vencido: {estados_pedidos['pago_vencido']}")
        self.stdout.write(f"   ✅ Pedidos con pago confirmado: {estados_pedidos['pago_confirmado']}")
        self.stdout.write(f"   📧 Recordatorios programados (próximos 7 días): {proximos_recordatorios}")

    def generar_contexto_recordatorio(self, recordatorio):
        """Genera el contexto para el template de email de recordatorio"""
        pedido = recordatorio.pedido
        
        # Calcular días para vencimiento o mora
        if pedido.fecha_limite_pago:
            hoy = timezone.now().date()
            dias_diferencia = (pedido.fecha_limite_pago - hoy).days
            
            if dias_diferencia > 0:
                mensaje_vencimiento = f"Su pago vence en {dias_diferencia} días"
            elif dias_diferencia == 0:
                mensaje_vencimiento = "Su pago vence HOY"
            else:
                mensaje_vencimiento = f"Su pago está vencido hace {abs(dias_diferencia)} días"
        else:
            mensaje_vencimiento = "Fecha de vencimiento no definida"
        
        return {
            'pedido': pedido,
            'recordatorio': recordatorio,
            'empresa': pedido.empresa_cliente,
            'mensaje_vencimiento': mensaje_vencimiento,
            'es_preventivo': recordatorio.tipo == RecordatorioPago.TipoRecordatorio.PREVENTIVO,
            'es_vencimiento': recordatorio.tipo == RecordatorioPago.TipoRecordatorio.VENCIMIENTO,
            'es_mora': recordatorio.tipo.startswith('MORA'),
            'es_legal': recordatorio.tipo == RecordatorioPago.TipoRecordatorio.LEGAL,
            'url_pago': f"https://lambda.com/pedidos/{pedido.id}/pago",  # URL de tu frontend
            'telefono_contacto': "+57 123 456 7890",  # Teléfono de Lambda
            'email_contacto': "facturacion@lambda.com"
        }