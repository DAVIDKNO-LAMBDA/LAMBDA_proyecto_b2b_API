from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.contrib.auth import get_user_model
from Empresas.models import Empresa, Area
from Usuarios.models import Usuario, ActivacionUsuario
from Base.correos import enviar_correo
from django.conf import settings

def _ctx(usuario: Usuario, token):
    base = getattr(settings, "ACTIVATION_BASE_URL", "http://localhost:8000/api")
    return {
        "nombre": usuario.nombres or "Usuario",
        "cargo": usuario.cargo or "Usuario",
        "token": str(token),
        "url_activacion": f"{base}/usuarios/activar/{token}/",
    }

@receiver(post_save, sender=Usuario)
def enviar_mail_activacion_empleado(sender, instance: Usuario, created, **kwargs):
    if not created or instance.is_active:
        return
    def _mail():
        act, _ = ActivacionUsuario.objects.get_or_create(usuario=instance)
        enviar_correo(
            asunto="Activa tu cuenta",
            plantilla="Usuarios/emails/activacion.html",
            contexto=_ctx(instance, act.token),
            destinatarios=[instance.email],
        )
    transaction.on_commit(_mail)
