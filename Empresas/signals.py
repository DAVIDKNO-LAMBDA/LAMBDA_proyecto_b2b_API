from django.db.models.signals import post_save
from django.dispatch import receiver
from Empresas.models import Empresa, Area

@receiver(post_save, sender=Empresa)
def configurar_areas_post_empresa(sender, instance: Empresa, created, **kwargs):
    """
    Esta señal SOLO crea/asegura áreas.
    NO crea usuarios (eso vive en Usuarios.signals).
    """
    if not created:
        return

    if instance.es_lambda:
        base = [
            ("Coordinación", "coordinacion"),
            ("Financiera", "financiera"),
            ("Abastecimiento", "abastecimiento"),
        ]
        for nombre, tipo in base:
            Area.objects.get_or_create(
                empresa=instance,
                nombre=nombre,
                defaults={"descripcion": f"Área {nombre}", "tipo": tipo, "activa": True},
            )
    else:
        # Empresa externa: asegurar área de finanzas
        Area.objects.get_or_create(
            empresa=instance,
            nombre="Finanzas",
            defaults={"descripcion": "Área financiera", "tipo": "financiera", "activa": True},
        )
