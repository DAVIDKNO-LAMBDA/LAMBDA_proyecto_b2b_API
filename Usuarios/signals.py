from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from Usuarios.models import Usuario, ActivacionUsuario


@receiver(post_save, sender=Usuario)
def enviar_correo_activacion(sender, instance, created, **kwargs):
    if created and not instance.is_active:
        activacion, _ = ActivacionUsuario.objects.get_or_create(usuario=instance)
        enlace = f"http://127.0.0.1:8000/api/usuarios/activar/{activacion.token}/"

        asunto = "Activa tu cuenta en Lambda B2B"
        mensaje = (
            f"Hola {instance.nombres},\n\n"
            "Tu cuenta ha sido creada en el sistema Lambda B2B.\n"
            "Por favor, activa tu cuenta usando el siguiente enlace (válido por 48 horas):\n\n"
            f"{enlace}\n\n"
            "Gracias,\nEquipo Lambda B2B"
        )

        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=False,
        )
        print(f"📨 Correo de activación enviado a {instance.email}")
