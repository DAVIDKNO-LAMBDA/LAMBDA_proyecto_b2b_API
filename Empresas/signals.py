from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from Empresas.models import Empresa, Area
from Usuarios.models import ActivacionUsuario
from Base.correos import enviar_correo
from django.conf import settings

@receiver(post_save, sender=Empresa)
def configurar_areas_y_admin_inicial(sender, instance: Empresa, created, **kwargs):
    if not created:
        return

    # Áreas base
    if instance.es_lambda:
        base = [("Coordinación","coordinacion"), ("Financiera","financiera"), ("Abastecimiento","abastecimiento")]
    else:
        base = [("Financiera","financiera"), ("Abastecimiento","abastecimiento")]
    for nombre, tipo in base:
        Area.objects.get_or_create(
            empresa=instance, nombre=nombre,
            defaults={"descripcion": f"Área {nombre}", "tipo": tipo},
        )

    # Crear admin inicial para empresa externa y enviar activación
    if not instance.es_lambda and instance.correo_contacto:
        User = get_user_model()
        if not User.objects.filter(email=instance.correo_contacto).exists():
            area_fin = Area.objects.filter(empresa=instance, nombre__iexact="Financiera").first()
            admin = User.objects.create_user(
                email=instance.correo_contacto,
                nombres=instance.nombre_contacto or "Admin",
                apellidos="",
                cargo="Administrador de Empresa",
                empresa=instance,
                area=area_fin,
                password=None,
            )
            admin.is_active = False
            admin.set_unusable_password()
            admin.save(update_fields=["is_active", "password"])

            # Asignar grupo "Admin Empresa"
            try:
                grp = Group.objects.get(name="Admin Empresa")
                admin.groups.add(grp)
            except Group.DoesNotExist:
                pass

            act = ActivacionUsuario.objects.create(usuario=admin)

            base_url = getattr(settings, "ACTIVATION_BASE_URL", "http://localhost:8000/api")
            enviar_correo(
                asunto="Activa tu cuenta de Administrador de Empresa",
                plantilla="Usuarios/emails/activacion.html",
                contexto={
                    "nombre": admin.nombres or "Usuario",
                    "cargo": admin.cargo or "Usuario",
                    "token": str(act.token),
                    "url_activacion": f"{base_url}/usuarios/activar/{act.token}/",
                },
                destinatarios=[admin.email],
            )
