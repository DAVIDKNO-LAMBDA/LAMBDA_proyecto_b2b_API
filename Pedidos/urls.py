from django.urls import path
from . import views

urlpatterns = [
    # ========== CONVERSIÓN DE SOLICITUDES ==========
    path('convertir-solicitud/', views.convertir_solicitud_a_pedido, name='convertir-solicitud-a-pedido'),
    
    # ========== LISTAR Y VER PEDIDOS ==========
    path('', views.listar_pedidos, name='listar-pedidos'),
    path('<int:pk>/', views.detalle_pedido, name='detalle-pedido'),
    
    # ========== ASIGNACIÓN A ÁREAS LAMBDA ==========
    path('<int:pk>/asignar-abastecimiento/', views.asignar_a_area_abastecimiento, name='asignar-abastecimiento'),
    path('<int:pk>/asignar-area-lambda/', views.asignar_area_lambda, name='asignar-area-lambda'),
    
    # ========== VALIDACIONES LAMBDA ==========
    path('<int:pk>/validar-abastecimiento/', views.validar_abastecimiento_lambda, name='validar-abastecimiento-lambda'),
    path('<int:pk>/validar-finanzas/', views.validar_finanzas_lambda, name='validar-finanzas-lambda'),
    
    # ========== GESTIÓN DE PAGOS ==========
    path('<int:pk>/gestionar-pago/', views.gestionar_pago, name='gestionar-pago'),
    path('<int:pk>/marcar-facturado/', views.marcar_como_facturado, name='marcar-facturado'),
    
    # ========== ENDPOINTS PARA LAMBDA ==========
    path('pendientes-validacion/', views.pedidos_pendientes_validacion_lambda, name='pendientes-validacion'),
    path('pendientes-abastecimiento/', views.pedidos_pendientes_abastecimiento_lambda, name='pendientes-abastecimiento'),
    path('pendientes-finanzas/', views.pedidos_pendientes_finanzas_lambda, name='pendientes-finanzas'),
    path('dashboard/', views.dashboard_lambda, name='dashboard-lambda'),
    path('estadisticas-pagos/', views.estadisticas_pagos, name='estadisticas-pagos'),
    path('ejecutar-procesamiento-pagos/', views.ejecutar_procesamiento_pagos, name='ejecutar-procesamiento-pagos'),
]