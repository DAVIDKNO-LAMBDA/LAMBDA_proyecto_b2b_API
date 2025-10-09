from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.contrib.auth import get_user_model
from django.conf import settings

from Empresas.models import Empresa, Area
from Usuarios.models import Usuario, ActivacionUsuario
from Base.correos import enviar_correo


def _contexto_activacion(usuario: Usuario, token):
    base = getattr(settings, "ACTIVATION_BASE_URL", "http://localhost:8000/api")
    url = f"{base}/usuarios/activar/{token}/"
    return {
        "nombre": usuario.nombres or "Usuario",
        "cargo": usuario.cargo or "Usuario",
        "token": str(token),
        "url_activacion": url,
    }


@receiver(post_save, sender=Empresa)
def crear_admin_empresa_y_enviar_mail(sender, instance: Empresa, created, **kwargs):
    """
    Al crear una empresa EXTERNA:
    - crea Admin Empresa inactivo (sin contraseña)
    - crea token de activación
    - envía correo de activación al correo de contacto
    """
    if not created or instance.es_lambda:
        return

    def _create_and_mail():
        User = get_user_model()
        email_admin = instance.correo_contacto
        if not email_admin:
            return
        if User.objects.filter(email=email_admin).exists():
            return  # idempotente

        # Buscar área 'Financiera' (fallback: crearla si no existe)
        area_fin = Area.objects.filter(empresa=instance, nombre__iexact="Financiera").first()
        if area_fin is None:
            area_fin = Area.objects.create(
                empresa=instance,
                nombre="Financiera",
                descripcion="Área encargada de la validación y gestión de pagos.",
                tipo="financiera",
            )

        user = User.objects.create_user(
            email=email_admin,
            nombres=instance.nombre_contacto or "Admin",
            apellidos="",
            cargo="Administrador de Empresa",
            empresa=instance,
            area=area_fin,
            password=None,  # sin contraseña
        )
        user.es_admin_empresa = True
        user.is_active = False
        user.set_unusable_password()  # jamás guardar pass en claro
        user.save(update_fields=["es_admin_empresa", "is_active", "password"])

        act = ActivacionUsuario.objects.create(usuario=user)

        enviar_correo(
            asunto="Activa tu cuenta de Administrador de Empresa",
            plantilla="Usuarios/emails/activacion.html",  # ← plantilla por app
            contexto=_contexto_activacion(user, act.token),
            destinatarios=[user.email],
        )

    transaction.on_commit(_create_and_mail)


@receiver(post_save, sender=Usuario)
def enviar_mail_activacion_empleado(sender, instance: Usuario, created, **kwargs):
    """
    Para empleados creados por el Admin Empresa:
    - si nacen inactivos, generar/obtener token de activación
    - enviar correo de activación al email del empleado
    """
    if not created or instance.is_active:
        return

    def _mail():
        act, _ = ActivacionUsuario.objects.get_or_create(usuario=instance)
        enviar_correo(
            asunto="Activa tu cuenta",
            plantilla="Usuarios/emails/activacion.html",  # ← plantilla por app
            contexto=_contexto_activacion(instance, act.token),
            destinatarios=[instance.email],
        )

    transaction.on_commit(_mail)
