from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # =============================================
    # GESTIÓN BÁSICA DE USUARIOS
    # =============================================
    path('empleados/', views.listar_empleados, name='listar-empleados'),
    path('empleados/crear/', views.crear_empleado, name='crear-empleado'),
    path('activar/<uuid:token>/', views.activar_cuenta, name='activar-cuenta'),
    path('reenviar-activacion/', views.reenviar_activacion, name='reenviar-activacion'),  # 🆕
    
    # =============================================
    # 🆕 GESTIÓN DE ÁREAS (HU08)
    # =============================================
    path('<int:pk>/asignar-area/', views.asignar_area, name='asignar-area'),
    
    # =============================================
    # 🆕 GESTIÓN DE PERMISOS ESPECIALES (HU09)
    # =============================================
    path('<int:pk>/permisos-especiales/', views.asignar_permisos_especiales, name='asignar-permisos-especiales'),
    path('<int:pk>/permisos-especiales/remover/', views.remover_permisos_especiales, name='remover-permisos-especiales'),
    
    # =============================================
    # 🆕 GESTIÓN DE JEFE DE ÁREA
    # =============================================
    path('<int:pk>/jefe-area/', views.asignar_jefe_area, name='asignar-jefe-area'),
    
    # =============================================
    # 🆕 CONSULTA DE PERMISOS Y ROLES
    # =============================================
    path('permisos/disponibles/', views.listar_permisos_disponibles, name='listar-permisos'),
    path('grupos/disponibles/', views.listar_grupos_disponibles, name='listar-grupos'),
    path('<int:pk>/permisos/', views.ver_permisos_usuario, name='ver-permisos-usuario'),
    path('<int:pk>/asignar-rol/', views.asignar_rol, name='asignar-rol'),
    
    # =============================================
    # 🆕 GESTIÓN JERÁRQUICA POR ÁREA  
    # =============================================
    path('mi-area/usuarios/', views.UsuariosAreaJefeView.as_view(), name='usuarios-area-jefe'),
    path('areas/asignables/', views.AreasAsignablesJefeView.as_view(), name='areas-asignables'),
    path('asignar-area/', views.AsignarUsuarioAreaView.as_view(), name='asignar-usuario-area'),
    path('mi-area/estadisticas/', views.EstadisticasAreaJefeView.as_view(), name='estadisticas-area-jefe'),
    
    # =============================================
    # 🆕 VALIDACIÓN DE VALIDADORES (HU10)
    # =============================================
    path('validadores/verificar/', views.verificar_validadores_empresa, name='verificar-validadores'),
]
