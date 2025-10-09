from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from Productos.models import Producto, MovimientoInventario
from Base.correos import enviar_correo
from Usuarios.models import Usuario


def _destinatarios_alerta_lambda():
    """
    Destinatarios para alerta de umbral:
      1) settings.PRODUCTS_ALERT_EMAILS (lista), si existe.
      2) Usuarios staff de empresa Lambda (is_staff y empresa.es_lambda=True).
    """
    emails = []
    for attr in ("PRODUCTS_ALERT_EMAILS", "NOTIF_EMAILS_LAMBDA"):
        val = getattr(settings, attr, None)
        if isinstance(val, (list, tuple)) and val:
            emails.extend([e for e in val if isinstance(e, str)])
    if emails:
        # Quitar duplicados manteniendo orden
        return list(dict.fromkeys(emails))

    qs = Usuario.objects.filter(is_staff=True, empresa__es_lambda=True, is_active=True).values_list("email", flat=True)
    return list(qs)


def _mail_alerta(producto: Producto):
    stock = producto.stock_disponible()
    if stock < (producto.umbral_minimo or 0):
        enviar_correo(
            asunto=f"Alerta de umbral - {producto.nombre}",
            plantilla="Productos/emails/alerta_umbral.html",
            contexto={"producto": producto, "stock": stock, "umbral": producto.umbral_minimo},
            destinatarios=_destinatarios_alerta_lambda() or [],
        )


@receiver(post_save, sender=Producto)
def alerta_umbral_por_producto(sender, instance: Producto, **kwargs):
    _mail_alerta(instance)


@receiver(post_save, sender=MovimientoInventario)
def alerta_umbral_por_movimiento(sender, instance: MovimientoInventario, created, **kwargs):
    # Disparar solo si el movimiento fue creado (afecta stock)
    if created:
        _mail_alerta(instance.producto)
