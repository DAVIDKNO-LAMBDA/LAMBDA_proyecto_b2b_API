from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Crea los grupos (roles) iniciales del sistema con sus permisos'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🚀 Iniciando creación de roles y permisos...\n"))
        
        # =============================================
        # DEFINICIÓN DE ROLES Y PERMISOS
        # =============================================
        
        roles_permisos = {
            'Admin Lambda': {
                'descripcion': 'Administrador interno de Lambda - TODOS LOS PERMISOS',
                'permisos': [
                    # Usuarios (CRUD completo)
                    'Usuarios.add_usuario',
                    'Usuarios.change_usuario',
                    'Usuarios.delete_usuario',
                    'Usuarios.view_usuario',
                    'Usuarios.puede_crear_usuarios',
                    'Usuarios.puede_editar_usuarios',
                    'Usuarios.puede_eliminar_usuarios',
                    'Usuarios.puede_activar_usuarios',
                    'Usuarios.puede_asignar_areas',
                    'Usuarios.puede_asignar_roles',
                    'Usuarios.puede_ver_todos_usuarios',
                    
                    # Empresas (CRUD completo)
                    'Empresas.add_empresa',
                    'Empresas.change_empresa',
                    'Empresas.delete_empresa',
                    'Empresas.view_empresa',
                    
                    # Áreas (CRUD completo)
                    'Empresas.add_area',
                    'Empresas.change_area',
                    'Empresas.delete_area',
                    'Empresas.view_area',
                    
                    # Solicitudes y Pedidos (TODOS)
                    'Usuarios.puede_ver_todas_solicitudes',
                    'Usuarios.puede_aprobar_pedidos',
                    'Usuarios.puede_rechazar_pedidos',
                    
                    # Reportes (TODOS)
                    'Usuarios.puede_ver_reportes_avanzados',
                    'Usuarios.puede_exportar_reportes',
                ]
            },
            
            'Admin Empresa': {
                'descripcion': 'Administrador de empresa cliente',
                'permisos': [
                    # Usuarios de SU empresa
                    'Usuarios.view_usuario',
                    'Usuarios.add_usuario',
                    'Usuarios.change_usuario',
                    'Usuarios.puede_crear_usuarios',
                    'Usuarios.puede_editar_usuarios',
                    'Usuarios.puede_activar_usuarios',
                    'Usuarios.puede_asignar_areas',
                    'Usuarios.puede_asignar_roles',
                    'Usuarios.puede_ver_todos_usuarios',
                    
                    # Áreas de SU empresa
                    'Empresas.view_area',
                    'Empresas.add_area',
                    'Empresas.change_area',
                    
                    # Solicitudes de SU empresa
                    'Usuarios.puede_crear_solicitudes',
                    'Usuarios.puede_ver_todas_solicitudes',
                    'Usuarios.puede_aprobar_pedidos',
                    'Usuarios.puede_validar_finanzas',
                    'Usuarios.puede_validar_abastecimiento',
                    
                    # Reportes
                    'Usuarios.puede_ver_reportes_avanzados',
                    'Usuarios.puede_exportar_reportes',
                    
                    # Catálogo
                    'Usuarios.puede_ver_catalogo',
                    'Usuarios.puede_ver_precios',
                ]
            },
            
            'Jefe de Área': {
                'descripcion': 'Jefe de área - Gestiona usuarios y solicitudes de su área',
                'permisos': [
                    # Usuarios de SU área
                    'Usuarios.view_usuario',
                    'Usuarios.add_usuario',
                    'Usuarios.puede_crear_usuarios',
                    'Usuarios.puede_asignar_areas',
                    
                    # Áreas (solo lectura)
                    'Empresas.view_area',
                    
                    # Solicitudes de SU área
                    'Usuarios.puede_crear_solicitudes',
                    'Usuarios.puede_editar_solicitudes',
                    'Usuarios.puede_ver_solicitudes_area',
                    'Usuarios.puede_aprobar_pedidos',
                    
                    # Reportes básicos
                    'Usuarios.puede_ver_reportes_basicos',
                    
                    # Catálogo
                    'Usuarios.puede_ver_catalogo',
                    'Usuarios.puede_ver_precios',
                    'Usuarios.puede_solicitar_productos',
                ]
            },
            
            'Empleado': {
                'descripcion': 'Empleado básico - Solo gestiona sus propias solicitudes',
                'permisos': [
                    # Usuarios (solo lectura de su perfil)
                    'Usuarios.view_usuario',
                    
                    # Solicitudes propias
                    'Usuarios.puede_crear_solicitudes',
                    'Usuarios.puede_editar_solicitudes',
                    'Usuarios.puede_ver_solicitudes_propias',
                    
                    # Catálogo
                    'Usuarios.puede_ver_catalogo',
                    'Usuarios.puede_solicitar_productos',
                ]
            },
        }
        
        # =============================================
        # CREAR GRUPOS Y ASIGNAR PERMISOS
        # =============================================
        
        total_grupos = len(roles_permisos)
        contador = 0
        
        for nombre_rol, config in roles_permisos.items():
            contador += 1
            self.stdout.write(f"\n[{contador}/{total_grupos}] Procesando: {nombre_rol}")
            self.stdout.write(f"    📝 {config['descripcion']}")
            
            # Crear o actualizar grupo
            grupo, created = Group.objects.get_or_create(name=nombre_rol)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"    ✅ Grupo creado"))
            else:
                self.stdout.write(self.style.WARNING(f"    ⚠️  Grupo ya existía, actualizando permisos..."))
            
            # Limpiar permisos anteriores
            grupo.permissions.clear()
            
            # Asignar permisos
            permisos_asignados = 0
            permisos_no_encontrados = []
            
            for permiso_completo in config['permisos']:
                try:
                    # Separar app_label.codename
                    app_label, codename = permiso_completo.split('.')
                    
                    # Buscar permiso
                    permiso = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    grupo.permissions.add(permiso)
                    permisos_asignados += 1
                
                except Permission.DoesNotExist:
                    permisos_no_encontrados.append(permiso_completo)
                except ValueError:
                    self.stdout.write(
                        self.style.ERROR(f"    ❌ Formato inválido: {permiso_completo}")
                    )
            
            # Mostrar resumen
            self.stdout.write(
                self.style.SUCCESS(f"    📋 {permisos_asignados} permisos asignados")
            )
            
            if permisos_no_encontrados:
                self.stdout.write(
                    self.style.WARNING(
                        f"    ⚠️  {len(permisos_no_encontrados)} permisos no encontrados:"
                    )
                )
                for perm in permisos_no_encontrados[:5]:  # Mostrar solo primeros 5
                    self.stdout.write(f"       - {perm}")
                if len(permisos_no_encontrados) > 5:
                    self.stdout.write(f"       ... y {len(permisos_no_encontrados) - 5} más")
        
        self.stdout.write(
            self.style.SUCCESS("\n\n✅ ¡Roles y permisos configurados exitosamente!")
        )
        self.stdout.write(
            self.style.SUCCESS(f"📊 Total de grupos creados/actualizados: {total_grupos}\n")
        )
