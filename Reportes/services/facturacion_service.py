from django.db import transaction
from django.utils import timezone
from django.core.files.base import ContentFile
from Pedidos.models import Pedido
from ..models import Factura, ItemFactura
from .pdf_generator import pdf_generator
from Base.correos import enviar_correo_html
import logging

logger = logging.getLogger(__name__)


class FacturacionService:
    """
    Servicio para facturación automática (HU24)
    """
    
    def generar_factura_desde_pedido(self, pedido, usuario_generador, observaciones="", terminos="", enviar_email=True):
        """
        Genera factura automáticamente desde un pedido pagado
        """
        try:
            with transaction.atomic():
                # Verificar que el pedido esté en estado correcto
                if pedido.estado != Pedido.EstadoPedido.PAGO_CONFIRMADO:
                    raise ValueError(f"El pedido {pedido.numero_pedido} no está en estado 'Pago Confirmado'")
                
                # Verificar que no tenga factura ya
                if hasattr(pedido, 'factura'):
                    raise ValueError(f"El pedido {pedido.numero_pedido} ya tiene una factura generada")
                
                # Crear factura
                factura = Factura.objects.create(
                    pedido=pedido,
                    empresa_cliente=pedido.empresa_cliente,
                    generada_por=usuario_generador,
                    observaciones=observaciones,
                    terminos_condiciones=terminos or self._obtener_terminos_default(),
                    estado=Factura.EstadoFactura.GENERADA
                )
                
                # Crear items de factura desde items del pedido
                self._crear_items_factura(factura, pedido)
                
                # Generar PDF
                self._generar_pdf_factura(factura)
                
                # Actualizar estado del pedido
                pedido.estado = Pedido.EstadoPedido.FACTURADO
                pedido.fecha_facturacion = timezone.now().date()
                pedido.save(update_fields=['estado', 'fecha_facturacion'])
                
                # Enviar por email si se solicita
                if enviar_email:
                    self._enviar_factura_email(factura)
                
                logger.info(f"✅ Factura {factura.numero_factura} generada para pedido {pedido.numero_pedido}")
                
                return factura
                
        except Exception as e:
            logger.error(f"❌ Error generando factura para pedido {pedido.numero_pedido}: {str(e)}")
            raise
    
    def _crear_items_factura(self, factura, pedido):
        """Crea items de factura basados en items del pedido"""
        
        items_factura = []
        
        for item_pedido in pedido.items.all():
            item_factura = ItemFactura(
                factura=factura,
                descripcion=f"{item_pedido.producto.nombre} - {item_pedido.producto.descripcion}",
                cantidad=item_pedido.cantidad_final,
                precio_unitario=item_pedido.precio_unitario_final
            )
            items_factura.append(item_factura)
        
        # Crear todos los items en batch
        ItemFactura.objects.bulk_create(items_factura)
        
        logger.info(f"📋 {len(items_factura)} items creados para factura {factura.numero_factura}")
    
    def _generar_pdf_factura(self, factura):
        """Genera y guarda el PDF de la factura"""
        try:
            # Generar PDF
            pdf_content = pdf_generator.generar_factura_pdf(factura)
            
            # Crear archivo
            pdf_file = ContentFile(
                pdf_content,
                name=f"factura_{factura.numero_factura}.pdf"
            )
            
            # Guardar en el modelo
            factura.archivo_pdf.save(
                f"factura_{factura.numero_factura}.pdf",
                pdf_file,
                save=True
            )
            
            logger.info(f"📄 PDF generado para factura {factura.numero_factura}")
            
        except Exception as e:
            logger.error(f"❌ Error generando PDF para factura {factura.numero_factura}: {str(e)}")
            # No fallar la creación de factura si no se puede generar el PDF
            pass
    
    def _enviar_factura_email(self, factura):
        """Envía la factura por email al cliente"""
        try:
            contexto = {
                'factura': factura,
                'empresa': factura.empresa_cliente,
                'pedido': factura.pedido,
                'fecha_emision': factura.fecha_emision,
                'numero_factura': factura.numero_factura,
                'total': factura.total
            }
            
            # Lista de destinatarios
            destinatarios = [factura.empresa_cliente.correo_contacto]
            
            # Agregar emails adicionales si existen
            if factura.empresa_cliente.correo_facturacion:
                destinatarios.append(factura.empresa_cliente.correo_facturacion)
            
            # Enviar a cada destinatario
            for destinatario in destinatarios:
                resultado = enviar_correo_html(
                    destinatario=destinatario,
                    asunto=f"Factura {factura.numero_factura} - Lambda Commerce",
                    template_path='Reportes/Emails/factura_generada.html',
                    contexto=contexto,
                    archivo_adjunto=factura.archivo_pdf.path if factura.archivo_pdf else None
                )
                
                if resultado:
                    logger.info(f"📧 Factura {factura.numero_factura} enviada a {destinatario}")
                else:
                    logger.error(f"❌ Error enviando factura {factura.numero_factura} a {destinatario}")
            
            # Marcar como enviada
            factura.estado = Factura.EstadoFactura.ENVIADA
            factura.fecha_envio = timezone.now()
            factura.save(update_fields=['estado', 'fecha_envio'])
            
        except Exception as e:
            logger.error(f"❌ Error enviando factura {factura.numero_factura}: {str(e)}")
    
    def _obtener_terminos_default(self):
        """Obtiene términos y condiciones por defecto"""
        return """
TÉRMINOS Y CONDICIONES:

1. ACEPTACIÓN: Esta factura se considera aceptada si no se objeta por escrito dentro de los 8 días siguientes a su recepción.

2. FORMA DE PAGO: El pago debe realizarse según la modalidad acordada en el pedido original.

3. MORA: Los pagos tardíos causarán intereses de mora del 1.5% mensual sobre el valor adeudado.

4. GARANTÍA: Los productos tienen garantía según las especificaciones del fabricante.

5. DEVOLUCIONES: Solo se aceptan devoluciones previa autorización y en perfecto estado.

6. JURISDICCIÓN: Cualquier disputa será resuelta bajo las leyes colombianas en Bogotá D.C.

7. CONTACTO: Para aclaraciones comunicarse a facturacion@lambda.com o al teléfono (1) 234-5678.

Lambda Commerce Solutions - NIT: 900.123.456-7
"""
    
    def procesar_facturacion_automatica(self):
        """
        Procesa facturación automática para pedidos pagados
        Se ejecuta desde comando de gestión
        """
        logger.info("🚀 Iniciando procesamiento de facturación automática...")
        
        # Buscar pedidos pagados sin factura
        pedidos_para_facturar = Pedido.objects.filter(
            estado=Pedido.EstadoPedido.PAGO_CONFIRMADO,
            deleted_at__isnull=True
        ).exclude(
            id__in=Factura.objects.values_list('pedido_id', flat=True)
        ).select_related('empresa_cliente')
        
        total_pedidos = pedidos_para_facturar.count()
        facturas_generadas = 0
        errores = 0
        
        logger.info(f"📊 {total_pedidos} pedidos encontrados para facturar")
        
        for pedido in pedidos_para_facturar:
            try:
                # Generar factura automáticamente
                factura = self.generar_factura_desde_pedido(
                    pedido=pedido,
                    usuario_generador=None,  # Sistema automático
                    observaciones="Factura generada automáticamente",
                    enviar_email=True
                )
                
                facturas_generadas += 1
                logger.info(f"✅ Factura {factura.numero_factura} generada para pedido {pedido.numero_pedido}")
                
            except Exception as e:
                errores += 1
                logger.error(f"❌ Error facturando pedido {pedido.numero_pedido}: {str(e)}")
        
        logger.info(
            f"🎉 Facturación automática completada: "
            f"{facturas_generadas} facturas generadas, {errores} errores"
        )
        
        return {
            'total_pedidos': total_pedidos,
            'facturas_generadas': facturas_generadas,
            'errores': errores
        }


class NotificacionesFacturacion:
    """
    Servicio para notificaciones relacionadas con facturación
    """
    
    def notificar_facturas_vencidas(self):
        """Notifica facturas vencidas para cobro"""
        
        hoy = timezone.now().date()
        
        # Buscar facturas vencidas no pagadas
        facturas_vencidas = Factura.objects.filter(
            fecha_vencimiento__lt=hoy,
            estado__in=[Factura.EstadoFactura.ENVIADA, Factura.EstadoFactura.GENERADA],
            deleted_at__isnull=True
        ).select_related('empresa_cliente', 'pedido')
        
        for factura in facturas_vencidas:
            try:
                self._enviar_notificacion_vencimiento(factura)
            except Exception as e:
                logger.error(f"Error notificando vencimiento de factura {factura.numero_factura}: {str(e)}")
    
    def _enviar_notificacion_vencimiento(self, factura):
        """Envía notificación de factura vencida"""
        
        dias_vencida = (timezone.now().date() - factura.fecha_vencimiento).days
        
        contexto = {
            'factura': factura,
            'empresa': factura.empresa_cliente,
            'dias_vencida': dias_vencida,
            'urgencia': 'alta' if dias_vencida > 30 else 'media'
        }
        
        # Enviar notificación
        resultado = enviar_correo_html(
            destinatario=factura.empresa_cliente.correo_contacto,
            asunto=f"FACTURA VENCIDA {factura.numero_factura} - Acción Requerida",
            template_path='Reportes/Emails/factura_vencida.html',
            contexto=contexto
        )
        
        if resultado:
            logger.info(f"📧 Notificación de vencimiento enviada para factura {factura.numero_factura}")


# Instancias globales de los servicios
facturacion_service = FacturacionService()
notificaciones_service = NotificacionesFacturacion()