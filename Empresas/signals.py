from django.db.models.signals import post_save
from django.dispatch import receiver
from Empresas.models import Empresa, Area
from Usuarios.models import Usuario

@receiver(post_save, sender=Empresa)
def crear_estructura_empresa(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.es_lambda:
        areas_lambda = [
            ("Coordinación", "Supervisa procesos del sistema", "coordinacion"),
            ("Dirección", "Aprueba compras grandes o de alto valor", "direccion"),
            ("Abastecimiento", "Gestiona inventario y productos", "abastecimiento"),
            ("Financiera", "Valida pagos y genera facturas", "financiera"),
        ]
        for nombre, desc, tipo in areas_lambda:
            Area.objects.get_or_create(
                nombre=nombre,
                empresa=instance,
                defaults={"descripcion": desc, "tipo": tipo}
            )
        print("✅ Estructura interna de Lambda creada correctamente.")
    else:
        area_financiera, _ = Area.objects.get_or_create(
            nombre="Financiera",
            empresa=instance,
            defaults={"descripcion": "Área encargada de la validación y gestión de pagos.", "tipo": "financiera"}
        )

        admin_email = f"admin@{instance.nombre.lower().replace(' ', '')}.com"
        if not Usuario.objects.filter(email=admin_email).exists():
            admin_empresa = Usuario.objects.create_user(
                email=admin_email,
                nombres="Admin",
                apellidos=instance.nombre,
                cargo="Administrador de Empresa",
                empresa=instance,
                area=area_financiera,
                password="Temporal123*",
                is_active=False
            )
            admin_empresa.user_permissions.add("Usuarios.es_admin_empresa")
            print(f"✅ Creado admin empresa {admin_email}")
