from django.urls import path
from . import views

app_name = 'solicitudes'

urlpatterns = [
    # =============================================
    # HU10 - CREAR SOLICITUD
    # =============================================
    path('crear/', views.crear_solicitud, name='crear-solicitud'),
    
    # =============================================
    # HU11 - LISTAR Y VER SOLICITUDES
    # =============================================
    path('', views.listar_solicitudes, name='listar-solicitudes'),
    path('<int:pk>/', views.detalle_solicitud, name='detalle-solicitud'),
    
    # =============================================
    # 🆕 APROBACIÓN POR JEFE DE ÁREA (PRIMER PASO)
    # =============================================
    path('<int:pk>/aprobar-jefe/', views.aprobar_por_jefe, name='aprobar-por-jefe'),
    path('<int:pk>/rechazar-jefe/', views.rechazar_por_jefe, name='rechazar-por-jefe'),
    
    # =============================================
    # HU12 - VALIDACIÓN ABASTECIMIENTO EMPRESA
    # =============================================
    path('<int:pk>/validar-abastecimiento/', views.validar_abastecimiento, name='validar-abastecimiento'),
    path('pendientes-abastecimiento/', views.solicitudes_pendientes_abastecimiento, name='pendientes-abastecimiento'),
    
    # =============================================
    # HU13 - VALIDACIÓN FINANZAS EMPRESA  
    # =============================================
    path('<int:pk>/validar-finanzas/', views.validar_finanzas, name='validar-finanzas'),
    path('pendientes-finanzas/', views.solicitudes_pendientes_finanzas, name='pendientes-finanzas'),
    
    # =============================================
    # AUXILIARES
    # =============================================
    path('<int:pk>/cancelar/', views.cancelar_solicitud, name='cancelar-solicitud'),
]