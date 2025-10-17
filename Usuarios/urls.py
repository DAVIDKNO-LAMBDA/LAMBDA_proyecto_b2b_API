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
    # 🆕 CONSULTA DE PERMISOS Y ROLES
    # =============================================
    path('permisos/disponibles/', views.listar_permisos_disponibles, name='listar-permisos'),
    path('grupos/disponibles/', views.listar_grupos_disponibles, name='listar-grupos'),
    path('<int:pk>/permisos/', views.ver_permisos_usuario, name='ver-permisos-usuario'),
    path('<int:pk>/asignar-rol/', views.asignar_rol, name='asignar-rol'),
    
    # =============================================
    # 🆕 VALIDACIÓN DE VALIDADORES (HU10)
    # =============================================
    path('validadores/verificar/', views.verificar_validadores_empresa, name='verificar-validadores'),
]
