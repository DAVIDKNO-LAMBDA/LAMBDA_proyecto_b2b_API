from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from Empresas.models import Empresa, Area
from Usuarios.models import Usuario, ActivacionUsuario

@receiver(post_save, sender=Empresa)
def configurar_areas_y_admin_inicial(sender, instance, created, **kwargs):
    if created:
        # --- PASO 1: Crear áreas por defecto ---
        # Esto es útil para todas las empresas, incluida Lambda.
        area_gerencia, _ = Area.objects.get_or_create(
            empresa=instance,
            nombre="Gerencia",
            defaults={"descripcion": "Área de Gerencia General"}
        )
        Area.objects.get_or_create(
            empresa=instance,
            nombre="Abastecimiento",
            defaults={"descripcion": "Área de compras y abastecimiento"}
        )
        Area.objects.get_or_create(
            empresa=instance,
            nombre="Finanzas",
            defaults={"descripcion": "Área de contabilidad y finanzas"}
        )

        # --- PASO 2: Crear usuario admin inicial SÓLO para empresas CLIENTE ---
        # Verificamos que la empresa que se está creando NO sea la principal.
        if instance.nombre != "Lambda Commerce Solutions":
            # Si no es Lambda, entonces sí creamos el admin y su token.
            admin = Usuario.objects.create_user(
                email=instance.correo_contacto,
                nombres=instance.nombre,
                apellidos="(Admin)",      # Placeholder para el apellido
                cargo="Administrador",    # Cargo por defecto
                empresa=instance,
                area=area_gerencia,       # Asignamos al área de Gerencia
                password=None,            # Sin contraseña inicial
            )
            
            # Asignar rol de admin de empresa
            try:
                rol_admin_empresa = Group.objects.get(name="admin_empresa")
                admin.groups.add(rol_admin_empresa)
            except Group.DoesNotExist:
                # Manejar el caso en que el grupo aún no exista
                print("ADVERTENCIA: El grupo 'admin_empresa' no existe. No se pudo asignar el rol.")

            # Crear token de activación para que el admin establezca su contraseña
            ActivacionUsuario.objects.create(usuario=admin)
            print(f"Usuario admin y token de activación creados para la empresa cliente: {instance.nombre}")
