# Empresas/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from Empresas.models import Empresa, Area

@receiver(post_save, sender=Empresa)
def configurar_areas_post_empresa(sender, instance: Empresa, created, **kwargs):
    """
    Crea/asegura áreas base al crear una Empresa.
    - Lambda: Coordinación, Financiera, Abastecimiento.
    - Externa: Financiera, Abastecimiento.
    """
    if not created:
        return

    if instance.es_lambda:
        Area.objects.get_or_create(
            empresa=instance,
            nombre="Coordinación",
            defaults={"descripcion": "Área Coordinación", "tipo": "coordinacion"},
        )
        Area.objects.get_or_create(
            empresa=instance,
            nombre="Financiera",
            defaults={"descripcion": "Área Financiera", "tipo": "financiera"},
        )
        Area.objects.get_or_create(
            empresa=instance,
            nombre="Abastecimiento",
            defaults={"descripcion": "Área Abastecimiento", "tipo": "abastecimiento"},
        )
    else:
        Area.objects.get_or_create(
            empresa=instance,
            nombre="Financiera",
            defaults={"descripcion": "Área Financiera", "tipo": "financiera"},
        )
        Area.objects.get_or_create(
            empresa=instance,
            nombre="Abastecimiento",
            defaults={"descripcion": "Área Abastecimiento", "tipo": "abastecimiento"},
        )
