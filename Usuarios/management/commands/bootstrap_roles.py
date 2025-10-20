from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


class Command(BaseCommand):
    help = 'Crea los grupos (roles) iniciales del sistema con sus permisos'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🚀 Iniciando creación de roles y permisos...\n"))
        
        # =============================================
        # 🆕 VERIFICAR Y CREAR CONTENT TYPES
        # =============================================
        self.verificar_content_types()
        
        # =============================================
        # DEFINICIÓN DE ROLES Y PERMISOS
        # =============================================
        
        roles_permisos = {
            # =============================================
            # ROLES LAMBDA (HU01-03, HU15)
            # =============================================
            'Admin Lambda': {
                'descripcion': 'Administrador interno de Lambda - TODOS LOS PERMISOS (HU01-03)',
                'permisos': [
                    # Gestión de Empresas Cliente (HU01-03)
                    'Empresas.add_empresa',
                    'Empresas.change_empresa', 
                    'Empresas.delete_empresa',
                    'Empresas.view_empresa',
                    
                    # Gestión completa de usuarios
                    'Usuarios.add_usuario',
                    'Usuarios.change_usuario',
                    'Usuarios.delete_usuario', 
                    'Usuarios.view_usuario',
                    'Usuarios.puede_crear_usuarios',
                    'Usuarios.puede_editar_usuarios',
                    'Usuarios.puede_activar_usuarios',
                    'Usuarios.puede_asignar_roles',
                    'Usuarios.puede_asignar_jefe_area',
                    'Usuarios.puede_ver_todos_usuarios',
                    
                    # Áreas
                    'Empresas.add_area',
                    'Empresas.change_area',
                    'Empresas.view_area',
                    
                    # Catálogo Lambda (HU23)
                    'Productos.add_producto',
                    'Productos.change_producto',
                    'Productos.view_producto',
                    
                    # Condiciones de Pago (HU15)
                    'Usuarios.puede_aprobar_credito',
                    'Usuarios.puede_definir_condiciones_pago',
                    
                    # Solicitudes y Pedidos (todos)
                    'Usuarios.puede_ver_todas_solicitudes',
                    'Usuarios.puede_aprobar_pedidos',
                    'Usuarios.puede_rechazar_pedidos',
                    'Usuarios.puede_gestionar_pagos',
                    'Usuarios.puede_facturar',
                    
                    # Validaciones Lambda
                    'Usuarios.puede_validar_abastecimiento',
                    'Usuarios.puede_validar_finanzas',
                    
                    # Reportes avanzados (HU24-26)
                    'Usuarios.puede_ver_reportes_avanzados',
                    'Usuarios.puede_exportar_reportes',
                ]
            },
            
            'Validador Abastecimiento Lambda': {
                'descripcion': 'Validador de stock Lambda - Valida disponibilidad en inventario Lambda',
                'permisos': [
                    # Validación específica de stock Lambda
                    'Usuarios.puede_validar_abastecimiento',
                    'Usuarios.puede_ver_todas_solicitudes',
                    
                    # Gestión de inventario
                    'Productos.view_producto',
                    'Productos.change_producto',
                    
                    # Su perfil
                    'Usuarios.view_usuario',
                ]
            },
            
            'Validador Financiero Lambda': {
                'descripcion': 'Validador financiero Lambda - Aprueba créditos y condiciones de pago',
                'permisos': [
                    # Validación específica financiera Lambda
                    'Usuarios.puede_validar_finanzas',
                    'Usuarios.puede_aprobar_credito',
                    'Usuarios.puede_definir_condiciones_pago',
                    'Usuarios.puede_ver_todas_solicitudes',
                    
                    # Gestión de pagos
                    'Usuarios.puede_gestionar_pagos',
                    'Usuarios.puede_facturar',
                    
                    # Su perfil
                    'Usuarios.view_usuario',
                ]
            },
            
            # =============================================
            # ROLES EMPRESA CLIENTE
            # =============================================
            'Admin Empresa': {
                'descripcion': 'Admin inicial de empresa cliente (HU04) - Gestiona empresa, empleados, áreas y asigna jefes',
                'permisos': [
                    # Gestión completa de empleados de SU empresa (HU05-07)
                    'Usuarios.view_usuario',
                    'Usuarios.add_usuario',
                    'Usuarios.change_usuario',
                    'Usuarios.puede_crear_usuarios',
                    'Usuarios.puede_editar_usuarios',
                    'Usuarios.puede_activar_usuarios',
                    'Usuarios.puede_asignar_roles',
                    'Usuarios.puede_asignar_jefe_area',
                    
                    # Gestión completa de áreas de SU empresa (HU08)
                    'Empresas.view_area',
                    'Empresas.add_area',
                    'Empresas.change_area',
                    'Empresas.delete_area',
                    
                    # Asignación de validadores especiales (HU09)
                    'Usuarios.puede_asignar_validadores',
                    
                    # Solicitudes de SU empresa (puede ver todas)
                    'Usuarios.puede_crear_solicitudes',
                    'Usuarios.puede_ver_todas_solicitudes',
                    
                    # Catálogo (solo lectura)
                    'Productos.view_producto',
                    
                    # Reportes básicos
                    'Usuarios.puede_ver_reportes_basicos',
                ]
            },
            
            'Jefe de Área': {
                'descripcion': 'Jefe de área - Aprueba solicitudes de su área (PRIMER PASO)',
                'permisos': [
                    # Aprobación de solicitudes de su área (PRIMER PASO DEL FLUJO)
                    'Usuarios.puede_aprobar_solicitudes_jefe',
                    'Usuarios.puede_crear_solicitudes',
                    'Usuarios.puede_editar_solicitudes',
                    'Usuarios.puede_ver_solicitudes_area',
                    
                    # Catálogo
                    'Productos.view_producto',
                    
                    # Su perfil
                    'Usuarios.view_usuario',
                ]
            },
            
            'Validador Abastecimiento': {
                'descripcion': 'Validador de abastecimiento (HU12) - Valida stock interno',
                'permisos': [
                    # Validación específica de abastecimiento (HU12)
                    'Solicitudes.puede_validar_solicitud_abastecimiento',
                    'Usuarios.puede_ver_solicitudes_area',
                    'Usuarios.puede_validar_abastecimiento',
                    
                    # Catálogo (para verificar productos)
                    'Productos.view_producto',
                    
                    # Su perfil
                    'Usuarios.view_usuario',
                ]
            },
            
            'Validador Financiero': {
                'descripcion': 'Validador financiero (HU13) - Valida presupuesto',
                'permisos': [
                    # Validación específica financiera (HU13) 
                    'Solicitudes.puede_validar_solicitud_finanzas',
                    'Usuarios.puede_ver_solicitudes_area',
                    'Usuarios.puede_validar_finanzas',
                    
                    # Catálogo (para verificar precios)
                    'Productos.view_producto',
                    
                    # Su perfil
                    'Usuarios.view_usuario',
                ]
            },
            
            'Empleado': {
                'descripcion': 'Empleado básico - Solo puede crear solicitudes y ver catálogo',
                'permisos': [
                    # Solicitudes propias únicamente
                    'Usuarios.puede_crear_solicitudes',
                    'Usuarios.puede_ver_solicitudes_propias',
                    
                    # Catálogo (solo lectura)
                    'Productos.view_producto',
                    
                    # Su perfil
                    'Usuarios.view_usuario',
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
        
        # =============================================
        # CREAR USUARIO LAMBDA SUPERADMIN (OPCIONAL)
        # =============================================
        self.crear_usuario_lambda_admin()
    
    def crear_usuario_lambda_admin(self):
        """Crea usuario administrador de Lambda si no existe"""
        from Usuarios.models import Usuario
        
        email_admin = "admin@lambda.com"
        
        # Verificar si ya existe
        if Usuario.objects.filter(email=email_admin).exists():
            self.stdout.write(
                self.style.WARNING(f"ℹ️ Usuario Lambda '{email_admin}' ya existe")
            )
            return
        
        try:
            # Crear usuario Lambda
            admin_lambda = Usuario.objects.create_user(
                email=email_admin,
                password="Lambda123!",  # Cambiar en producción
                nombres="Administrador",
                apellidos="Lambda",
                cargo="Super Admin",
                empresa=None,  # Sin empresa = Usuario Lambda
                is_staff=True,
                is_active=True,
                estado='activo'
            )
            
            # El signal automáticamente asignará permisos completos
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Usuario Lambda admin creado: {email_admin} / Lambda123!"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error creando usuario Lambda: {str(e)}")
            )

    def verificar_content_types(self):
        """Verifica que existan los ContentTypes necesarios"""
        self.stdout.write("🔍 Verificando Content Types...")
        
        apps_required = ['Usuarios', 'Empresas', 'Productos', 'Solicitudes', 'Pedidos', 'Reportes']
        missing_apps = []
        
        for app_label in apps_required:
            try:
                # Intentar obtener al menos un content type de la app
                ContentType.objects.filter(app_label=app_label.lower()).first()
                if not ContentType.objects.filter(app_label=app_label.lower()).exists():
                    missing_apps.append(app_label)
            except:
                missing_apps.append(app_label)
        
        if missing_apps:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️ Apps faltantes o sin modelos: {', '.join(missing_apps)}"
                )
            )
            self.stdout.write(
                self.style.WARNING("💡 Ejecuta 'python manage.py migrate' primero")
            )
        else:
            self.stdout.write(self.style.SUCCESS("✅ Content Types verificados"))
        
        return len(missing_apps) == 0
