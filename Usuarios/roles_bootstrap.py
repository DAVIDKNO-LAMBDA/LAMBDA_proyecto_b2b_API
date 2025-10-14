from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

GROUPS = {
    "Lambda Abastecimiento": [
        "Productos.view_producto",
        "Productos.add_movimientoinventario",
        "Solicitudes.view_solicitud",
        "Solicitudes.change_solicitud",
        "Pedidos.view_pedido",
    ],
    "Lambda Finanzas": [
        "Productos.view_producto",
        "Solicitudes.view_solicitud",
        "Pedidos.view_pedido",
        "Pedidos.change_pedido",
    ],
    "Lambda Coordinación": [
        "Productos.view_producto",
        "Solicitudes.view_solicitud",
        "Solicitudes.change_solicitud",
        "Pedidos.view_pedido",
    ],
    "Admin Empresa": [
        "Empresas.view_empresa",
        "Empresas.view_area", "Empresas.add_area", "Empresas.change_area",
        "Usuarios.view_usuario", "Usuarios.add_usuario", "Usuarios.change_usuario",
        "Solicitudes.view_solicitud", "Solicitudes.add_solicitud", "Solicitudes.change_solicitud",
        "Pedidos.view_pedido",
    ],
    "Jefe de Área": [
        "Usuarios.view_usuario", "Usuarios.add_usuario", "Usuarios.change_usuario",
        "Solicitudes.view_solicitud", "Solicitudes.add_solicitud", "Solicitudes.change_solicitud",
    ],
    "Empleado": [
        "Solicitudes.view_solicitud", "Solicitudes.add_solicitud",
    ],
}

class Command(BaseCommand):
    help = "Crea/actualiza grupos de roles y asigna permisos por codename"

    def handle(self, *args, **options):
        for group_name, perm_labels in GROUPS.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            desired_perms = []
            for label in perm_labels:
                try:
                    app_label, codename = label.split(".", 1)
                    perm = Permission.objects.select_related("content_type").get(
                        content_type__app_label=app_label.lower(),
                        codename=codename.lower(),
                    )
                    desired_perms.append(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"[roles] Permiso no encontrado: {label}"))
            group.permissions.set(desired_perms)
            self.stdout.write(self.style.SUCCESS(
                f"[roles] Grupo '{group_name}' actualizado ({len(desired_perms)} permisos)."
            ))
        self.stdout.write(self.style.SUCCESS("[roles] OK."))
