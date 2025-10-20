from django.urls import path
from . import views

urlpatterns = [
    # ========== GESTIÓN DE FACTURAS ==========
    path('facturas/', views.listar_facturas, name='listar-facturas'),
    path('facturas/<int:pk>/', views.detalle_factura, name='detalle-factura'),
    path('facturas/<int:pk>/pdf/', views.descargar_factura_pdf, name='descargar-factura-pdf'),
    path('generar-factura/', views.generar_factura, name='generar-factura'),
    
    # ========== REPORTES ==========
    path('generar-reporte/', views.generar_reporte, name='generar-reporte'),
    path('dashboard/', views.dashboard_reportes, name='dashboard-reportes'),
]