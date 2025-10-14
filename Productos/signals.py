from django.db.models.signals import post_save
from django.dispatch import receiver
from Productos.models import Producto, MovimientoInventario
from Base.correos import enviar_correo
from django.conf import settings

def _destinatarios():
    arr = []
    for attr in ("PRODUCTS_ALERT_EMAILS","NOTIF_EMAILS_LAMBDA"):
        val = getattr(settings, attr, None)
        if isinstance(val, (list, tuple)):
            arr.extend([x for x in val if isinstance(x, str)])
    # únicos
    return list(dict.fromkeys(arr))

def _mail_alerta(producto: Producto):
    stock = producto.stock_disponible()
    if stock < (producto.umbral_minimo or 0):
        enviar_correo(
            asunto=f"Alerta de umbral - {producto.nombre}",
            plantilla="Productos/emails/alerta_umbral.html",
            contexto={"producto": producto, "stock": stock, "umbral": producto.umbral_minimo},
            destinatarios=_destinatarios(),
        )

@receiver(post_save, sender=Producto)
def alerta_por_producto(sender, instance: Producto, **kwargs):
    _mail_alerta(instance)

@receiver(post_save, sender=MovimientoInventario)
def alerta_por_movimiento(sender, instance: MovimientoInventario, created, **kwargs):
    if created:
        _mail_alerta(instance.producto)
